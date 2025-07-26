import asyncio
import logging
from functools import wraps
import datetime
from linebot.v3.messaging import (
    MessagingApi,
    ReplyMessageRequest,
    TextMessage as V3TextMessage,
)
from linebot.v3.webhooks import MessageEvent
from utils.gsheet_connector import GSheetConnector
from services.email_sender import send_notification_email
from config import settings

logger = logging.getLogger("linebot_logger")
# 初始化 Google Sheet 連接器
gsheet_connector = GSheetConnector()

def command_with_argument(usage_message: str):
    """
    A decorator to handle boilerplate for commands that require one argument.
    It handles argument parsing, validation, and centralized error handling.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(event: MessageEvent, messaging_api: MessagingApi):
            command_name = func.__name__
            argument = None
            try:
                parts = event.message.text.split(maxsplit=1)
                if len(parts) < 2:
                    await messaging_api.reply_message(ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[V3TextMessage(text=usage_message)]
                    ))
                    return
                
                argument = parts[1]
                await func(argument, event, messaging_api) # Pass the argument to the actual command
            except Exception as e:
                logger.error(f"Error in command '{command_name}' with argument '{argument}': {e}", exc_info=True)
                await messaging_api.reply_message(ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[V3TextMessage(text="指令執行失敗，請稍後再試。")]
                ))
        return wrapper
    return decorator

async def handle_message(event: MessageEvent, messaging_api: MessagingApi):
    text = event.message.text # 確保事件是 TextMessageContent

    # 檢查是否來自群組或聊天室，如果是，則拒絕服務並回覆
    if event.source.type != "user":
        await messaging_api.reply_message(ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[V3TextMessage(text="抱歉，本機器人僅支援一對一聊天。")]
        ))
        return

    # 使用字典進行指令分派
    command_handlers = {
        "/登記": register_command,
        "/查詢": query_command,
        "/取消": cancel_command, # 使用 startswith 進行模糊匹配
    }

    # 找到對應的處理函式
    handler = command_handlers.get(text.split()[0]) # 取第一個詞作為指令
    if handler:
        await handler(event, messaging_api)
    else:
        # 處理一般訊息
        await default_message_handler(event, messaging_api)

async def register_command(event: MessageEvent, messaging_api: MessagingApi):
    # 處理登記邏輯
    try:
        # 執行阻塞 I/O 操作於獨立線程
        new_serial = await asyncio.to_thread(gsheet_connector.get_new_serial)
        
        # 使用更精確的伺服器時間，並格式化
        timestamp_dt = datetime.datetime.fromtimestamp(event.timestamp / 1000)
        timestamp_str = timestamp_dt.strftime('%Y-%m-%d %H:%M:%S')

        # 因為只處理一對一聊天，直接獲取用戶個人資料即可
        profile = await messaging_api.get_profile(event.source.user_id)
        user_name = profile.display_name

        row_data = [
            str(new_serial),
            timestamp_str,
            user_name,
            event.source.user_id,
            "待處理"
        ]
        # 執行阻塞 I/O 操作於獨立線程
        await asyncio.to_thread(gsheet_connector.append_row, row_data)

        reply_message = f"登記成功！您的序號是：{new_serial}"
        await messaging_api.reply_message(ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[V3TextMessage(text=reply_message)]
        ))

        # 發送郵件通知 (執行阻塞 I/O 操作於獨立線程)
        await asyncio.to_thread(
            send_notification_email,
            f"新的登記訊息 - 序號 {new_serial}",
            f"用戶 {user_name} (ID: {event.source.user_id}) 於 {timestamp_str} 登記，序號為 {new_serial}。\n詳細資料請參考 Google Sheet。"
        )
    except Exception as e:
        logger.error(f"Registration failed for user {event.source.user_id}: {e}", exc_info=True)
        await messaging_api.reply_message(ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[V3TextMessage(text=f"登記失敗，請稍後再試。")]
        ))

@command_with_argument(usage_message="請輸入要查詢的序號，例如：/查詢 123")
async def query_command(serial_to_query: str, event: MessageEvent, messaging_api: MessagingApi):
    # The core logic for querying, now much cleaner.
    record = await asyncio.to_thread(gsheet_connector.find_row_by_serial, serial_to_query)

    if record:
        # 假設回傳的 record 是包含標題的字典
        # 例如: {'序號': '123', '登記時間': '...', '處理狀態': '待處理'}
        reply_text = f"查詢結果 - 序號 {serial_to_query}:\n"
        reply_text += f"登記時間: {record.get('登記時間', 'N/A')}\n"
        reply_text += f"登記用戶: {record.get('登記用戶', 'N/A')}\n"
        reply_text += f"處理狀態: {record.get('處理狀態', 'N/A')}"
    else:
        reply_text = f"找不到序號 {serial_to_query} 的登記紀錄。"

    await messaging_api.reply_message(ReplyMessageRequest(
        reply_token=event.reply_token,
        messages=[V3TextMessage(text=reply_text)]
    ))

@command_with_argument(usage_message="請輸入要取消的序號，例如：/取消 123")
async def cancel_command(serial_to_cancel: str, event: MessageEvent, messaging_api: MessagingApi):
    # The core logic for cancellation.
    success = await asyncio.to_thread(gsheet_connector.update_status_by_serial, serial_to_cancel, "已取消")

    if success:
        reply_text = f"序號 {serial_to_cancel} 已成功標記為「已取消」。"
    else:
        reply_text = f"找不到序號 {serial_to_cancel} 或無法更新狀態。"

    await messaging_api.reply_message(ReplyMessageRequest(
        reply_token=event.reply_token,
        messages=[V3TextMessage(text=reply_text)]
    ))

async def default_message_handler(event: MessageEvent, messaging_api: MessagingApi):
    # 處理不屬於任何指令的普通訊息
    await messaging_api.reply_message(ReplyMessageRequest(
        reply_token=event.reply_token,
        messages=[V3TextMessage(text="我收到你的訊息了！你可以嘗試輸入 /登記 或 /查詢。")]
    ))