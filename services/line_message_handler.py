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

# 假設這些自訂模組存在於您的專案結構中
from services.async_email_sender import send_notification_email
from utils.async_gsheet_connector import AsyncGSheetConnector, GSheetApiClientError

# --- 設定 ---
logger = logging.getLogger(__name__)
gsheet_connector = AsyncGSheetConnector()
TAIWAN_TZ = timezone(timedelta(hours=+8))  # 設定時區為台灣時間


async def _reply_with_error(messaging_api: MessagingApi, event: MessageEvent, text: str):
    """一個輔助函式，用於發送錯誤回覆並記錄失敗。"""
    try:
        await messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=text)]
            )
        )
    except LineBotApiError as e:
        # 如果連回覆錯誤訊息都失敗，只能記錄下來
        logger.error(
            f"無法發送錯誤訊息給使用者 {event.source.user_id}: {e.status_code} {e.error.message}"
        )

async def handle_register_command(event: MessageEvent, messaging_api: MessagingApi):
    """處理使用者的登記邏輯。"""
    user_id = event.source.user_id
    if not user_id:
        logger.warning("收到一個沒有 user_id 的訊息事件。")
        return

    try:
        user_name = "使用者"  # 設定預設名稱
        # 1. 取得使用者個人資料以獲取顯示名稱
        try:
            profile = await messaging_api.get_profile(user_id)
            user_name = profile.display_name
        except LineBotApiError as e:
            # 如果個人資料獲取失敗，僅記錄錯誤但繼續執行，使用預設名稱
            logger.warning(f"無法取得使用者 {user_id} 的個人資料: {e.status_code} {e.error.message}. 將使用預設名稱。")

        # 2. 核心邏輯：非同步與 Google Sheets 互動
        logger.info(f"開始為使用者進行登記: {user_name} ({user_id})")
        new_serial = await gsheet_connector.get_new_serial()
        timestamp_str = datetime.now(TAIWAN_TZ).strftime("%Y-%m-%d %H:%M:%S")
        row_data = [new_serial, user_id, user_name, timestamp_str]
        await gsheet_connector.append_row(row_data)
        logger.info(f"已成功將資料寫入 GSheet，序號為 {new_serial}")

        # 3. 關鍵步驟：回覆使用者確認訊息
        reply_text = f"您好 {user_name}，您的登記已完成。\n序號：{new_serial}\n時間：{timestamp_str}"
        await messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

        # 4. 非關鍵步驟：發送通知郵件。此操作的失敗不應影響給使用者的回覆。
        try:
            await send_notification_email(
                subject=f"新的登記訊息 - 序號 {new_serial}",
                body=f"用戶 {user_name} (ID: {user_id}) 於 {timestamp_str} 登記，序號為 {new_serial}。"
            )
            logger.info(f"已為序號 {new_serial} 發送通知郵件")
        except Exception as email_error:
            # 如果郵件發送失敗，只需記錄，因為主要流程已成功
            logger.error(f"為序號 {new_serial} 發送通知郵件失敗: {email_error}", exc_info=True)

    except GSheetApiClientError as e:
        logger.error(f"為使用者 {user_id} 登記時發生 GSheet API 錯誤: {e}", exc_info=True)
        await _reply_with_error(messaging_api, event, "抱歉，系統暫時無法連接到資料庫，請稍後再試。")
    except LineBotApiError as e:
        # 處理回覆訊息時的 API 錯誤
        logger.error(f"回覆訊息給使用者 {user_id} 時發生 LINE API 錯誤: {e.status_code} {e.error.message}", exc_info=True)
        # 此時已無法回覆，只能記錄
    except Exception as e:
        logger.error(f"為使用者 {user_id} 登記時發生未預期的錯誤: {e}", exc_info=True)
        await _reply_with_error(messaging_api, event, "抱歉，系統發生未預期的錯誤，我們將盡快處理，請聯繫管理員。")

# --- 主訊息路由器 ---

async def handle_message(event: MessageEvent, messaging_api: MessagingApi):
    """
    將收到的文字訊息路由到對應的命令處理函式。
    """
    if not isinstance(event.message, TextMessageContent):
        return  # 只處理文字訊息

    text = event.message.text.strip().lower()

    # 根據訊息文字進行簡單的路由
    if text == "登記":
        await handle_register_command(event, messaging_api)
    else:
        # 對於其他訊息的預設回覆
        reply_text = f"您說了「{event.message.text}」。\n若要登記，請輸入「登記」。"
        await messaging_api.reply_message(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply_text)])
        )