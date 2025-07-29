import logging
import aiosmtplib
from email.mime.text import MIMEText
from email.header import Header
from config import settings

logger = logging.getLogger(__name__)

async def send_notification_email(subject: str, body: str):
    """
    使用 aiosmtplib 非同步地發送通知郵件。
    """
    message = MIMEText(body, 'plain', 'utf-8')
    message['From'] = Header(settings.EMAIL_SENDER, 'utf-8')
    message['To'] = Header(", ".join(settings.EMAIL_RECEIVER), 'utf-8')
    message['Subject'] = Header(subject, 'utf-8')

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_SERVER,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            use_tls=True
        )
        logger.info(f"Email notification sent successfully. Subject: '{subject}'")
    except Exception as e:
        logger.error(f"Failed to send email notification: {e}", exc_info=True)