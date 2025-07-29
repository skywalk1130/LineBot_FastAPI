import uvicorn
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

from routers import line_webhook, commands
# 導入非同步連接器以進行啟動檢查
from utils.async_gsheet_connector import AsyncGSheetConnector
from utils.logger import setup_logging
from config import settings

# 在應用程式啟動的最開始就設定日誌系統
setup_logging()

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 應用程式啟動時執行的程式碼
    logger.info("--- Application startup ---")
    try:
        # 初始化非同步 Google Sheets 連接器並預熱快取
        logger.info("Initializing and warming up async Google Sheets connection...")
        gsheet_connector = AsyncGSheetConnector()
        await gsheet_connector.get_worksheet()  # 透過獲取工作表來驗證連線並預熱快取
        logger.info("Async Google Sheets connection verified and cache warmed up.")
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
    # log_config=None 確保 uvicorn 使用我們透過 setup_logging() 設定的 root logger
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True, log_config=None)