import asyncio
import logging
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from linebot.v3.messaging import (
    AsyncApiClient,
    Configuration,
    MessagingApi
)
from linebot.v3.exceptions import LineBotApiError
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
        self._initialized_at: Optional[datetime] = None
        
        # 監控指標
        self._metrics = {
            'total_requests': 0,
            'failed_requests': 0,
            'last_request_time': None,
            'initialization_time': None,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
    
    async def get_messaging_api(self) -> MessagingApi:
        """
        獲取 MessagingApi 實例，如果不存在則創建
        使用鎖確保線程安全
        """
        if self._is_closing:
            raise RuntimeError("LineApiManager is closing, cannot create new connections")
        
        start_time = datetime.now(timezone.utc)
        try:
            self._metrics['total_requests'] += 1
            self._metrics['last_request_time'] = start_time.isoformat()
            
            async with self._lock:
                if self._messaging_api is None:
                    await self._initialize_client()
                return self._messaging_api
                
        except Exception as e:
            self._metrics['failed_requests'] += 1
            logger.error(f"Failed to get messaging API: {e}")
            raise
    
    async def _initialize_client(self):
        """初始化 LINE API 客戶端"""
        init_start = datetime.now(timezone.utc)
        
        try:
            # 驗證配置
            if not settings.LINE_CHANNEL_ACCESS_TOKEN:
                raise ValueError("LINE_CHANNEL_ACCESS_TOKEN is not configured")
            
            if not settings.LINE_CHANNEL_ACCESS_TOKEN.strip():
                raise ValueError("LINE_CHANNEL_ACCESS_TOKEN cannot be empty")
            
            # 創建客戶端
            configuration = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
            self._client = AsyncApiClient(configuration)
            self._messaging_api = MessagingApi(self._client)
            self._initialized_at = datetime.now(timezone.utc)
            
            # 記錄初始化時間
            init_duration = (datetime.now(timezone.utc) - init_start).total_seconds()
            self._metrics['initialization_time'] = init_duration
            
            logger.info(f"LINE API client initialized successfully in {init_duration:.3f}s")
            
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize LINE API client: {e}")
            # 確保清理狀態
            self._client = None
            self._messaging_api = None
            raise
    
    async def close(self, timeout: float = 5.0):
        """
        正確關閉 API 客戶端，釋放資源
        """
        self._is_closing = True
        async with self._lock:
            if self._client is not None:
                try:
                    # 添加超時機制，避免無限等待
                    await asyncio.wait_for(self._client.close(), timeout=timeout)
                    logger.info("LINE API client closed successfully")
                except asyncio.TimeoutError:
                    logger.warning(f"LINE API client close timed out after {timeout}s")
                except Exception as e:
                    logger.error(f"Error closing LINE API client: {e}")
                finally:
                    self._client = None
                    self._messaging_api = None
                    self._initialized_at = None
    
    async def health_check(self) -> Dict[str, Any]:
        """
        全面的健康檢查，返回詳細狀態信息
        """
        health_info = {
            'is_healthy': False,
            'status': 'unknown',
            'details': {},
            'checked_at': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # 檢查基本狀態
            if self._is_closing:
                health_info.update({
                    'is_healthy': False,
                    'status': 'closing',
                    'details': {'message': 'Manager is in closing state'}
                })
                return health_info
            
            if self._client is None or self._messaging_api is None:
                health_info.update({
                    'is_healthy': False,
                    'status': 'not_initialized',
                    'details': {'message': 'Client not initialized'}
                })
                return health_info
            
            # 檢查客戶端是否已關閉
            if hasattr(self._client, 'is_closed') and self._client.is_closed:
                health_info.update({
                    'is_healthy': False,
                    'status': 'client_closed',
                    'details': {'message': 'AsyncApiClient is closed'}
                })
                return health_info
            
            # 可以添加實際的 API 調用來驗證連接
            # 註意：這會產生實際的 API 請求，在生產環境中要謹慎使用
            # try:
            #     await self._messaging_api.get_bot_info()
            # except LineBotApiError as e:
            #     health_info.update({
            #         'is_healthy': False,
            #         'status': 'api_error',
            #         'details': {'error': str(e), 'status_code': e.status_code}
            #     })
            #     return health_info
            
            # 所有檢查通過
            health_info.update({
                'is_healthy': True,
                'status': 'healthy',
                'details': {
                    'initialized_at': self._initialized_at.isoformat() if self._initialized_at else None,
                    'uptime_seconds': (
                        datetime.now(timezone.utc) - self._initialized_at
                    ).total_seconds() if self._initialized_at else None
                }
            })
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health_info.update({
                'is_healthy': False,
                'status': 'error',
                'details': {'error': str(e)}
            })
        
        return health_info
    
    def get_metrics(self) -> Dict[str, Any]:
        """獲取監控指標"""
        metrics = self._metrics.copy()
        metrics.update({
            'is_initialized': self._messaging_api is not None,
            'is_closing': self._is_closing,
            'initialized_at': self._initialized_at.isoformat() if self._initialized_at else None
        })
        return metrics

# 全域單例實例管理
_line_api_manager: Optional[LineApiManager] = None
_manager_lock = asyncio.Lock()

async def get_line_api_manager() -> LineApiManager:
    """
    獲取全域 LINE API 管理器實例
    使用雙重檢查鎖定模式確保線程安全的單例
    """
    global _line_api_manager
    
    # 第一次檢查（快速路徑）
    if _line_api_manager is not None:
        return _line_api_manager
    
    # 慢速路徑：需要加鎖
    async with _manager_lock:
        # 雙重檢查鎖定模式
        if _line_api_manager is None:
            _line_api_manager = LineApiManager()
            logger.info("Created new LineApiManager instance")
        return _line_api_manager

# FastAPI 依賴注入函數
async def get_messaging_api() -> MessagingApi:
    """
    FastAPI 依賴注入函數，提供 MessagingApi 實例
    使用共享的客戶端管理器，避免資源洩漏
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
        logger.info("LINE API manager has been closed and reset")

# 上下文管理器版本（適用於臨時使用）
@asynccontextmanager
async def line_api_context():
    """
    上下文管理器，確保在使用完畢後自動關閉客戶端
    適用於短期使用場景（不建議在主應用程式中使用）
    """
    manager = LineApiManager()
    try:
        yield await manager.get_messaging_api()
    finally:
        await manager.close()

# 健康檢查函數
async def line_api_health_check() -> Dict[str, Any]:
    """檢查 LINE API 客戶端健康狀態"""
    try:
        manager = await get_line_api_manager()
        return await manager.health_check()
    except Exception as e:
        logger.error(f"LINE API health check failed: {e}")
        return {
            'is_healthy': False,
            'status': 'error',
            'details': {'error': str(e)},
            'checked_at': datetime.now(timezone.utc).isoformat()
        }

# 監控指標獲取函數
async def get_line_api_metrics() -> Dict[str, Any]:
    """獲取 LINE API 客戶端監控指標"""
    try:
        manager = await get_line_api_manager()
        return manager.get_metrics()
    except Exception as e:
        logger.error(f"Failed to get LINE API metrics: {e}")
        return {
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }