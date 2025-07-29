import asyncio
import logging
from typing import Optional
from contextlib import asynccontextmanager

from linebot.v3.messaging import (
    AsyncApiClient,
    Configuration,
    MessagingApi
)
from config import settings

logger = logging.getLogger(__name__)

class LineApiManager:
    """
    LINE API 客戶端管理器，負責管理 AsyncApiClient 的生命週期
    使用單例模式確保整個應用程式共用同一個客戶端實例
    """
    
    def __init__(self):
        self._client: Optional[AsyncApiClient] = None
        self._messaging_api: Optional[MessagingApi] = None
        self._lock = asyncio.Lock()
        self._is_closing = False
    
    async def get_messaging_api(self) -> MessagingApi:
        """
        獲取 MessagingApi 實例，如果不存在則創建
        使用鎖確保線程安全
        """
        if self._is_closing:
            raise RuntimeError("LineApiManager is closing, cannot create new connections")
        
        async with self._lock:
            if self._messaging_api is None:
                await self._initialize_client()
            return self._messaging_api
    
    async def _initialize_client(self):
        """初始化 LINE API 客戶端"""
        try:
            configuration = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
            self._client = AsyncApiClient(configuration)
            self._messaging_api = MessagingApi(self._client)
            logger.info("LINE API client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LINE API client: {e}")
            raise
    
    async def close(self):
        """
        正確關閉 API 客戶端，釋放資源
        """
        self._is_closing = True
        async with self._lock:
            if self._client is not None:
                try:
                    await self._client.close()
                    logger.info("LINE API client closed successfully")
                except Exception as e:
                    logger.error(f"Error closing LINE API client: {e}")
                finally:
                    self._client = None
                    self._messaging_api = None
    
    async def health_check(self) -> bool:
        """
        健康檢查，驗證客戶端是否正常工作
        """
        try:
            if self._client is None:
                return False
            # 這裡可以添加簡單的 API 調用來驗證連接
            return not self._client.is_closed if hasattr(self._client, 'is_closed') else True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

# 全域單例實例
_line_api_manager: Optional[LineApiManager] = None

async def get_line_api_manager() -> LineApiManager:
    """獲取全域 LINE API 管理器實例"""
    global _line_api_manager
    if _line_api_manager is None:
        _line_api_manager = LineApiManager()
    return _line_api_manager

# FastAPI 依賴注入函數
async def get_messaging_api() -> MessagingApi:
    """
    FastAPI 依賴注入函數，提供 MessagingApi 實例
    現在使用共享的客戶端管理器，避免資源洩漏
    """
    manager = await get_line_api_manager()
    return await manager.get_messaging_api()

# 優雅關閉函數
async def close_line_api():
    """
    應用程式關閉時調用，確保正確釋放資源
    """
    global _line_api_manager
    if _line_api_manager is not None:
        await _line_api_manager.close()
        _line_api_manager = None

# 上下文管理器版本（可選）
@asynccontextmanager
async def line_api_context():
    """
    上下文管理器，確保在使用完畢後自動關閉客戶端
    適用於短期使用場景
    """
    manager = LineApiManager()
    try:
        yield await manager.get_messaging_api()
    finally:
        await manager.close()

# 健康檢查函數
async def line_api_health_check() -> bool:
    """檢查 LINE API 客戶端健康狀態"""
    try:
        manager = await get_line_api_manager()
        return await manager.health_check()
    except Exception as e:
        logger.error(f"LINE API health check failed: {e}")
        return False