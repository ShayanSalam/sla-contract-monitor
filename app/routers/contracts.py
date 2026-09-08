from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.security import get_current_user
from app.models.models import Contract, Obligation, Party, User
from app.schemas.schemas import ContractCreate, ContractOut, ObligationOut
from app.services.extraction import extract_obligations_from_text
from app.services.pdf_parser import extract_text_from_upload

router = APIRouter(prefix="/contracts", tags=["contracts"])

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB - generous for a text-based contract PDF


@router.post("/upload", response_model=ContractOut, status_code=201)
async def upload_contract(
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a PDF or .txt contract file and save it as a Contract record.

    The raw text is extracted immediately and stored in the DB.
    To run AI obligation extraction, call POST /contracts/{id}/extract next.

    Accepted file types: application/pdf, text/plain
    """
    file_bytes = await file.read()
    content_type = file.content_type or ""

    if len(file_bytes) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB.",
        )

    try:
        raw_text = extract_text_from_upload(file_bytes, content_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    contract = Contract(
        owner_id=current_user.id,
        title=title,
        raw_text=raw_text,
        original_filename=file.filename,
        status="uploaded",
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


@router.post("/", response_model=ContractOut, status_code=201)
def create_contract(
    payload: ContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a contract record with raw text provided directly in the request body.
    Useful for testing without a real file. Use POST /contracts/upload for real PDFs.
    """
    contract = Contract(
        owner_id=current_user.id,
        title=payload.title,
        raw_text=payload.raw_text,
        status="uploaded",
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


@router.get("/", response_model=List[ContractOut])
def list_contracts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Contract).filter(Contract.owner_id == current_user.id).all()


@router.get("/{contract_id}", response_model=ContractOut)
def get_contract(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract = (
        db.query(Contract)
        .filter(Contract.id == contract_id, Contract.owner_id == current_user.id)
        .first()
    )
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


def _run_extraction_in_background(contract_id: str):
    """
    Does the actual Gemini extraction + obligation creation. Runs after the
    request has already returned, in its own DB session (the request-scoped
    session from `get_db` is closed by the time this runs, so it can't be
    reused here).

    This is what makes extraction non-blocking: the person who clicked
    "extract" gets their response back immediately and can keep using the
    app while this runs. The contract's `status` field is the only signal
    the frontend needs - it polls GET /contracts/{id} and updates the UI
    whenever status flips from "processing" to "processed" or "failed".
    """
    db = SessionLocal()
    try:
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if not contract:
            return

        try:
            result = extract_obligations_from_text(contract.raw_text)
        except Exception:
            contract.status = "failed"
            db.commit()
            return

        for item in result.obligations:
            party_id = None
            if item.party_name:
                party = db.query(Party).filter(Party.name == item.party_name).first()
                if not party:
                    party = Party(name=item.party_name)
                    db.add(party)
                    db.commit()
                    db.refresh(party)
                party_id = party.id

            obligation = Obligation(
                contract_id=contract.id,
                party_id=party_id,
                description=item.description,
                deadline=item.deadline,
                penalty_amount=item.penalty_amount,
                penalty_currency=item.penalty_currency or "USD",
                is_ai_extracted=True,
            )
            db.add(obligation)

        contract.status = "processed"
        db.commit()
    finally:
        db.close()


@router.post("/{contract_id}/extract", response_model=ContractOut, status_code=202)
def extract_obligations(
    contract_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Kicks off AI obligation extraction for this contract and returns
    immediately (202 Accepted) with the contract now marked "processing" -
    it does NOT wait for Gemini to finish.

    The actual extraction (chunking, calling Gemini, saving obligations)
    runs in the background via `_run_extraction_in_background`. The client
    should poll GET /contracts/{id} to see status move to "processed" or
    "failed", then fetch GET /obligations/contract/{id} for the results.

    This is idempotent-unsafe by design for now (running it twice creates
    duplicate obligations) — Week 2's scope is proving the extraction works
    correctly, not building re-run protection yet.
    """
    contract = (
        db.query(Contract)
        .filter(Contract.id == contract_id, Contract.owner_id == current_user.id)
        .first()
    )
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if not contract.raw_text or not contract.raw_text.strip():
        raise HTTPException(status_code=400, detail="Contract has no text to extract from")

    contract.status = "processing"
    db.commit()
    db.refresh(contract)

    background_tasks.add_task(_run_extraction_in_background, contract.id)

    return contract


@router.delete("/{contract_id}", status_code=204)
def delete_contract(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a contract and all its obligations/alerts (cascade).

    Primarily needed to clean up orphaned rows from failed extraction
    attempts - upload and extract are two separate calls, so a failed
    extraction otherwise leaves a permanent contract row with zero
    obligations and no way to remove it.
    """
    contract = (
        db.query(Contract)
        .filter(Contract.id == contract_id, Contract.owner_id == current_user.id)
        .first()
    )
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    db.delete(contract)
    db.commit()
    return None
