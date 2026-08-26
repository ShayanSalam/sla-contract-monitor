"""
Deadline Monitoring Scheduler.

Runs periodic background checks across all obligations stored in PostgreSQL.

Logic Rules:
------------
1. BREACHED: If (deadline < current_time) AND (status != 'completed')
   -> Set status = ObligationStatus.breached
   -> Log audit record in alerts_log
   -> Trigger breach notification email

2. UPCOMING: If (current_time <= deadline <= current_time + 7_days) AND (status == 'pending')
   -> Set status = ObligationStatus.upcoming
   -> Log audit record in alerts_log
   -> Trigger upcoming reminder email
"""
import logging
from datetime import datetime, timedelta
from typing import Dict

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.models import Obligation, ObligationStatus
from app.services.alerting import log_and_send_alert

logger = logging.getLogger("sla_monitor.scheduler")

# Number of days before deadline to flag obligation as 'upcoming'
UPCOMING_DAYS_THRESHOLD = 7

# Global scheduler instance
scheduler = BackgroundScheduler()


def run_deadline_check_with_db(db: Session) -> Dict[str, int]:
    """
    Core monitoring function. Inspects every obligation in PostgreSQL,
    updates statuses, sends alerts, and writes to `alerts_log`.
    """
    now = datetime.utcnow()
    upcoming_threshold = now + timedelta(days=UPCOMING_DAYS_THRESHOLD)

    # Query all active obligations (not completed)
    active_obligations = (
        db.query(Obligation)
        .filter(Obligation.status != ObligationStatus.completed)
        .all()
    )

    breached_count = 0
    upcoming_count = 0
    checked_count = len(active_obligations)

    for ob in active_obligations:
        # Check 1: Has the deadline passed?
        if ob.deadline < now:
            if ob.status != ObligationStatus.breached:
                ob.status = ObligationStatus.breached
                db.commit()
                log_and_send_alert(db, ob, alert_type="breach_notice")
                breached_count += 1
                logger.info(f"Obligation {ob.id} flagged as BREACHED")

        # Check 2: Is the deadline approaching within the upcoming window?
        elif now <= ob.deadline <= upcoming_threshold:
            if ob.status == ObligationStatus.pending:
                ob.status = ObligationStatus.upcoming
                db.commit()
                log_and_send_alert(db, ob, alert_type="upcoming_reminder")
                upcoming_count += 1
                logger.info(f"Obligation {ob.id} flagged as UPCOMING")

    return {
        "checked": checked_count,
        "flagged_upcoming": upcoming_count,
        "flagged_breached": breached_count,
        "executed_at": now.isoformat(),
    }


def scheduled_job():
    """Wrapper function for APScheduler to open a clean DB session."""
    db = SessionLocal()
    try:
        logger.info("Starting scheduled deadline check...")
        stats = run_deadline_check_with_db(db)
        logger.info(f"Scheduled deadline check completed: {stats}")
    except Exception as e:
        logger.error(f"Error in scheduled deadline check: {str(e)}")
    finally:
        db.close()


def start_scheduler():
    """Start the background scheduler to run check daily (or hourly in dev)."""
    if not scheduler.running:
        # Run daily check job
        scheduler.add_job(
            scheduled_job,
            "interval",
            hours=24,
            id="daily_deadline_check",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("Background deadline monitoring scheduler started.")


def stop_scheduler():
    """Stop the background scheduler cleanly."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background deadline monitoring scheduler stopped.")
