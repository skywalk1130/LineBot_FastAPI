import asyncio
from fastapi import APIRouter, Depends, HTTPException
from linebot.v3.messaging import (
    MessagingApi,
    PushMessageRequest,
    TextMessage as V3TextMessage,
)
from utils.line_api_client import get_messaging_api
from services.email_sender import send_notification_email
from config import settings

router = APIRouter()

@router.post("/send-test-email")
async def send_test_email_command(messaging_api: MessagingApi = Depends(get_messaging_api)):
    try:
        # 在獨立線程中執行同步的郵件發送，避免阻塞
        await asyncio.to_thread(send_notification_email, "測試主旨", "這是一封來自 Line Bot 的測試郵件。")
        # 發送 Line 訊息通知管理員郵件已發送
        if settings.LINE_ADMIN_USER_ID:
            await messaging_api.push_message(PushMessageRequest(
                to=settings.LINE_ADMIN_USER_ID,
                messages=[V3TextMessage(text="測試郵件已發送。")]
            ))
        return {"message": "Test email sent successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send test email: {e}")