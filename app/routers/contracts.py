from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Contract, User
from app.schemas.schemas import ContractCreate, ContractOut

router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.post("/", response_model=ContractOut, status_code=201)
def create_contract(
    payload: ContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a contract record with raw text already provided.
    Week 2 will replace this with real PDF upload + text extraction."""
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
    from fastapi import HTTPException
    contract = (
        db.query(Contract)
        .filter(Contract.id == contract_id, Contract.owner_id == current_user.id)
        .first()
    )
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract
