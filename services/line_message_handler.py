import logging
from datetime import datetime, timezone, timedelta

from linebot.v3.exceptions import LineBotApiError
from linebot.v3.messaging import (
    MessageEvent,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    TextMessageContent,
)

from services.async_email_sender import send_notification_email
from utils.async_gsheet_connector import get_gsheet_connector, GSheetApiClientError

logger = logging.getLogger(__name__)
TAIWAN_TZ = timezone(timedelta(hours=+8))

async def _reply_with_error(messaging_api: MessagingApi, event: MessageEvent, text: str):
    """發送錯誤回覆的輔助函數"""
    try:
        await messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=text)]
            )
        )
    except LineBotApiError as e:
        logger.error(f"Failed to send error message to user {event.source.user_id}: {e}")

async def handle_register_command(event: MessageEvent, messaging_api: MessagingApi):
    """處理登記命令"""
    user_id = event.source.user_id
    if not user_id:
        logger.warning("Received event without user_id")
        return

    try:
        # 獲取使用者資料
        user_name = "使用者"
        try:
            profile = await messaging_api.get_profile(user_id)
            user_name = profile.display_name
        except LineBotApiError as e:
            logger.warning(f"Failed to get profile for {user_id}: {e}")

        # 獲取 Google Sheets 連接器
        gsheet_connector = await get_gsheet_connector()
        
        # 執行登記流程
        logger.info(f"Starting registration for: {user_name} ({user_id})")
        new_serial = await gsheet_connector.get_new_serial()
        timestamp_str = datetime.now(TAIWAN_TZ).strftime("%Y-%m-%d %H:%M:%S")
        row_data = [new_serial, user_id, user_name, timestamp_str]
        
        await gsheet_connector.append_row(row_data)
        logger.info(f"Data written to GSheet with serial: {new_serial}")

        # 回覆使用者
        reply_text = f"您好 {user_name}，您的登記已完成。\n序號：{new_serial}\n時間：{timestamp_str}"
        await messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

        # 發送通知郵件（非阻塞）
        try:
            await send_notification_email(
                subject=f"新的登記訊息 - 序號 {new_serial}",
                body=f"用戶 {user_name} (ID: {user_id}) 於 {timestamp_str} 登記，序號為 {new_serial}。"
            )
            logger.info(f"Notification email sent for serial: {new_serial}")
        except Exception as email_error:
            logger.error(f"Failed to send notification email: {email_error}")

    except GSheetApiClientError as e:
        logger.error(f"GSheet API error for user {user_id}: {e}")
        await _reply_with_error(messaging_api, event, "抱歉，系統暫時無法連接到資料庫，請稍後再試。")
    except LineBotApiError as e:
        logger.error(f"LINE API error when replying to {user_id}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error for user {user_id}: {e}", exc_info=True)
        await _reply_with_error(messaging_api, event, "抱歉，系統發生未預期的錯誤，請聯繫管理員。")

async def handle_message(event: MessageEvent, messaging_api: MessagingApi):
    """
    主要訊息處理函數 - 已修正參數問題
    """
    if not isinstance(event.message, TextMessageContent):
        return

    text = event.message.text.strip().lower()

    if text == "登記":
        await handle_register_command(event, messaging_api)
    else:
        # 預設回覆
        reply_text = f"您說了「{event.message.text}」。\n若要登記，請輸入「登記」。"
        try:
            await messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token, 
                    messages=[TextMessage(text=reply_text)]
                )
            )
        except LineBotApiError as e:
            logger.error(f"Failed to send default reply: {e}")