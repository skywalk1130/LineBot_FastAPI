import uvicorn
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

from routers import line_webhook, commands
from utils.gsheet_connector import GSheetConnector
from config import settings
from utils.logger import setup_logger

logger = setup_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 應用程式啟動時執行的程式碼
    logger.info("--- Application startup ---")
    try:
        # 初始化並檢查 Google Sheets 連線
        logger.info("Checking Google Sheets connection...")
        gsheet_connector = GSheetConnector()
        gsheet_connector.check_connection()
    except Exception as e:
        # 如果啟動時發生嚴重錯誤，可以選擇在這裡處理或讓應用程式停止
        logger.critical(f"FATAL: Startup check failed. {e}", exc_info=True)
        # raise e # 如果希望錯誤導致應用程式無法啟動，可以取消註解此行

    yield

    # 應用程式關閉時執行的程式碼
    logger.info("--- Application shutdown ---")


app = FastAPI(lifespan=lifespan)

# 包含來自其他模組的路由
app.include_router(line_webhook.router, tags=["Line Webhook"])
app.include_router(commands.router, prefix="/commands", tags=["Admin Commands"])


if __name__ == "__main__":
    # 使用 uvicorn 啟動應用程式
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)