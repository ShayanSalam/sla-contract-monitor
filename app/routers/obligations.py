from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Obligation, Contract, User, ObligationStatus
from app.schemas.schemas import ObligationCreate, ObligationOut, ObligationStatusUpdate

router = APIRouter(prefix="/obligations", tags=["obligations"])


@router.post("/", response_model=ObligationOut, status_code=201)
def create_obligation(
    payload: ObligationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Make sure the contract belongs to this user before attaching an obligation to it
    contract = (
        db.query(Contract)
        .filter(Contract.id == payload.contract_id, Contract.owner_id == current_user.id)
        .first()
    )
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    obligation = Obligation(
        contract_id=payload.contract_id,
        party_id=payload.party_id,
        description=payload.description,
        deadline=payload.deadline,
        penalty_amount=payload.penalty_amount,
        penalty_currency=payload.penalty_currency,
        is_ai_extracted=False,
    )
    db.add(obligation)
    db.commit()
    db.refresh(obligation)
    return obligation


@router.get("/", response_model=List[ObligationOut])
def list_obligations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Obligation)
        .join(Contract)
        .filter(Contract.owner_id == current_user.id)
        .all()
    )


@router.get("/contract/{contract_id}", response_model=List[ObligationOut])
def list_obligations_for_contract(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Obligation)
        .join(Contract)
        .filter(Contract.id == contract_id, Contract.owner_id == current_user.id)
        .all()
    )


@router.patch("/{obligation_id}/status", response_model=ObligationOut)
def update_obligation_status(
    obligation_id: str,
    payload: ObligationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update an obligation's status (e.g. mark as 'completed' once fulfilled, or reset).
    """
    obligation = (
        db.query(Obligation)
        .join(Contract)
        .filter(Obligation.id == obligation_id, Contract.owner_id == current_user.id)
        .first()
    )
    if not obligation:
        raise HTTPException(status_code=404, detail="Obligation not found")

    valid_statuses = [status.value for status in ObligationStatus]
    if payload.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{payload.status}'. Must be one of {valid_statuses}",
        )

    obligation.status = ObligationStatus(payload.status)
    db.commit()
    db.refresh(obligation)
    return obligation
