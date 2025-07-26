import smtplib
from email.mime.text import MIMEText
from email.header import Header
from config import settings

def send_notification_email(subject: str, body: str):
    sender = settings.EMAIL_SENDER
    receivers = settings.EMAIL_RECEIVER # settings.EMAIL_RECEIVER 現在是一個列表

    message = MIMEText(body, 'plain', 'utf-8')
    message['From'] = Header(sender, 'utf-8')
    message['To'] = Header(",".join(receivers), 'utf-8')
    message['Subject'] = Header(subject, 'utf-8')

    try:
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as smtpObj:
            smtpObj.starttls() # 啟用 TLS
            smtpObj.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtpObj.sendmail(sender, receivers, message.as_string())
        print("郵件成功發送！")
    except smtplib.SMTPException as e:
        print(f"無法發送郵件: {e}")
        raise # 重新拋出異常以便上層捕獲
    except Exception as e:
        print(f"發送郵件時發生未知錯誤: {e}")
        raise