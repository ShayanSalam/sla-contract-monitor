from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Contract, Obligation, Party, User
from app.schemas.schemas import ContractCreate, ContractOut, ObligationOut
from app.services.extraction import extract_obligations_from_text
from app.services.pdf_parser import extract_text_from_upload

router = APIRouter(prefix="/contracts", tags=["contracts"])


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


@router.post("/{contract_id}/extract", response_model=List[ObligationOut], status_code=201)
def extract_obligations(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Sends the contract's raw text to Gemini, extracts every obligation/deadline
    it finds, and saves them as real Obligation rows linked to this contract.

    Long contracts are automatically chunked before extraction and results are
    merged and deduplicated before being written to the DB.

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

    if not contract.raw_text or not contract.raw_text.strip():\
        raise HTTPException(status_code=400, detail="Contract has no text to extract from")

    contract.status = "processing"
    db.commit()

    try:
        result = extract_obligations_from_text(contract.raw_text)
    except Exception as e:
        contract.status = "failed"
        db.commit()
        raise HTTPException(status_code=502, detail=f"Extraction failed: {str(e)}")

    created_obligations = []
    for item in result.obligations:
        party_id = None
        if item.party_name:
            # Reuse an existing party with this name if one exists, otherwise create it
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
        created_obligations.append(obligation)

    contract.status = "processed"
    db.commit()
    for ob in created_obligations:
        db.refresh(ob)

    return created_obligations
