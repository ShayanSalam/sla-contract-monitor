from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import AlertLog, Obligation, Contract, User
from app.schemas.schemas import AlertLogOut
from app.services.scheduler import run_deadline_check_with_db

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.post("/run-check")
def run_manual_deadline_check(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually trigger an immediate deadline monitoring check.

    Evaluates all obligations:
    - If deadline has passed → flags as 'breached', logs to alerts_log, sends breach notification.
    - If deadline is within 7 days → flags as 'upcoming', logs to alerts_log, sends reminder.

    Returns the number of obligations checked and newly flagged.
    """
    stats = run_deadline_check_with_db(db)
    return {
        "status": "success",
        "message": "Deadline check completed successfully",
        "details": stats,
    }


@router.get("/alerts", response_model=List[AlertLogOut])
def list_alert_logs(
    alert_type: Optional[str] = Query(None, description="Filter by 'upcoming_reminder' or 'breach_notice'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve audit trail of all alerts sent for the current user's contracts.

    This audit log proves legal compliance and SLA traceability.
    """
    query = (
        db.query(AlertLog)
        .join(Obligation)
        .join(Contract)
        .filter(Contract.owner_id == current_user.id)
    )

    if alert_type:
        query = query.filter(AlertLog.alert_type == alert_type)

    return query.order_by(AlertLog.sent_at.desc()).all()
