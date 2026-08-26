"""
Alerting Service.

Handles sending email notifications (via SMTP/SendGrid if configured) and
creating audit log entries in the `alerts_log` PostgreSQL table whenever an
obligation becomes upcoming or breached.

Traceability & Compliance
--------------------------
Every alert triggered MUST generate an AlertLog record. This audit trail is what
proves compliance and non-repudiation in legal & corporate audits.
"""
import logging
import smtplib
from email.message import EmailMessage
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import AlertLog, Obligation

logger = logging.getLogger("sla_monitor.alerting")


def send_email_notification(to_email: str, subject: str, body: str) -> bool:
    """
    Sends an email using standard SMTP.
    If SMTP settings are missing from .env, it logs the alert to console
    so local development and testing never fail.
    """
    smtp_host = getattr(settings, "SMTP_HOST", None)
    smtp_port = getattr(settings, "SMTP_PORT", 587)
    smtp_user = getattr(settings, "SMTP_USER", None)
    smtp_password = getattr(settings, "SMTP_PASSWORD", None)

    if not (smtp_host and smtp_user and smtp_password):
        logger.info(
            f"[SIMULATED EMAIL ALERT] To: {to_email} | Subject: {subject}\nBody: {body}"
        )
        # Safe ASCII printing for Windows console compatibility
        safe_subject = subject.encode("ascii", "replace").decode("ascii")
        safe_body = body.encode("ascii", "replace").decode("ascii")
        print(f"\n[ALERT EMAIL SENT TO {to_email}]\nSubject: {safe_subject}\n{safe_body}\n")
        return True

    try:
        msg = EmailMessage()
        msg["From"] = settings.EMAILS_FROM if hasattr(settings, "EMAILS_FROM") else smtp_user
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        logger.info(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False


def log_and_send_alert(
    db: Session,
    obligation: Obligation,
    alert_type: str,  # "upcoming_reminder" | "breach_notice"
    custom_message: Optional[str] = None,
) -> AlertLog:
    """
    1. Formats the alert message.
    2. Writes a permanent audit record to PostgreSQL `alerts_log`.
    3. Triggers email notification.
    """
    contract_title = obligation.contract.title if obligation.contract else "Unknown Contract"
    deadline_str = obligation.deadline.strftime("%Y-%m-%d %H:%M UTC")
    penalty_info = (
        f" Penalty amount: {obligation.penalty_amount} {obligation.penalty_currency}."
        if obligation.penalty_amount
        else ""
    )

    if not custom_message:
        if alert_type == "breach_notice":
            message = (
                f"[SLA BREACH WARNING] Obligation '{obligation.description}' "
                f"under contract '{contract_title}' passed its deadline on {deadline_str}.{penalty_info}"
            )
        else:  # upcoming_reminder
            message = (
                f"[UPCOMING DEADLINE] Obligation '{obligation.description}' "
                f"under contract '{contract_title}' is due on {deadline_str}.{penalty_info}"
            )
    else:
        message = custom_message

    # Create audit log record in PostgreSQL
    alert_log = AlertLog(
        obligation_id=obligation.id,
        alert_type=alert_type,
        message=message,
        sent_at=datetime.utcnow(),
    )
    db.add(alert_log)
    db.commit()
    db.refresh(alert_log)

    # Determine email recipient (contract owner email or default admin)
    recipient_email = "admin@slamonitor.com"
    if obligation.contract and obligation.contract.owner:
        recipient_email = obligation.contract.owner.email

    subject_prefix = "[BREACH NOTICE]" if alert_type == "breach_notice" else "[UPCOMING SLA REMINDER]"
    subject = f"{subject_prefix} {contract_title} - {obligation.description[:40]}"

    send_email_notification(
        to_email=recipient_email,
        subject=subject,
        body=message,
    )

    return alert_log
