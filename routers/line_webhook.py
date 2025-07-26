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
# 使用新的非同步 API 客戶端
from utils.line_api_client import get_messaging_api

router = APIRouter()
logger = logging.getLogger("linebot_logger")

# 在模組層級初始化 v3 的事件解析器，這是正確的做法
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)

@router.post("/callback")
async def line_webhook_callback(
    request: Request,
    x_line_signature: str = Header(None),
    messaging_api: MessagingApi = Depends(get_messaging_api)
):
    body = await request.body()

    try:
        # 使用 parser 解析收到的事件
        events = parser.parse(body.decode("utf-8"), x_line_signature)
    except InvalidSignatureError:
        logger.error("Invalid signature. Please check your channel access token/channel secret.")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 使用 asyncio.gather 並行處理所有事件，發揮非同步最大效益
    tasks = []
    for event in events:
        if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
            tasks.append(handle_message(event, messaging_api))

    if tasks:
        await asyncio.gather(*tasks)

    return "OK"