from fastapi import APIRouter, Header, Request, HTTPException, Depends
import logging
import asyncio

# 引入 line-bot-sdk v3 的類別
from linebot.v3.webhook import WebhookParser
from linebot.v3.messaging import MessagingApi
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
)

from config import settings
from services.line_message_handler import handle_message
# 使用正確的 LINE API 客戶端
from utils.line_api_client import get_messaging_api

router = APIRouter()
logger = logging.getLogger("linebot_logger")

# 在模組層級初始化 v3 的事件解析器
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)

@router.post("/callback")
async def line_webhook_callback(
    request: Request,
    x_line_signature: str = Header(None),
    messaging_api: MessagingApi = Depends(get_messaging_api)
):
    """
    LINE Webhook 回調處理器
    處理來自 LINE 平台的 webhook 請求
    """
    try:
        body = await request.body()
        body_str = body.decode("utf-8")
        
        # 驗證請求簽名
        if not x_line_signature:
            logger.error("Missing X-Line-Signature header")
            raise HTTPException(status_code=400, detail="Missing signature header")
        
        # 解析 webhook 事件
        try:
            events = parser.parse(body_str, x_line_signature)
        except InvalidSignatureError as e:
            logger.error(f"Invalid signature: {e}")
            raise HTTPException(status_code=400, detail="Invalid signature")
        except Exception as e:
            logger.error(f"Failed to parse webhook events: {e}")
            raise HTTPException(status_code=400, detail="Failed to parse events")
        
        # 記錄收到的事件數量
        logger.info(f"Received {len(events)} webhook events")
        
        # 並行處理所有訊息事件
        tasks = []
        for event in events:
            if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
                logger.debug(f"Processing message event from user: {event.source.user_id}")
                # 注意：這裡只傳遞兩個參數，已修正原本的錯誤
                tasks.append(handle_message(event, messaging_api))
            else:
                logger.debug(f"Skipping non-text message event: {type(event)}")
        
        # 等待所有任務完成
        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
                logger.info(f"Successfully processed {len(tasks)} message events")
            except Exception as e:
                logger.error(f"Error in batch processing events: {e}")
                # 不拋出異常，因為部分事件可能已成功處理
        
        return {"status": "ok", "processed_events": len(tasks)}
        
    except HTTPException:
        # 重新拋出 HTTP 異常
        raise
    except Exception as e:
        logger.error(f"Unexpected error in webhook callback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")