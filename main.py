import uvicorn
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

from routers import line_webhook, commands
# 導入非同步連接器以進行啟動檢查
from utils.async_gsheet_connector import AsyncGSheetConnector
from utils.logger import setup_logging
# 導入更新的 LINE API 客戶端管理器
from utils.line_api_client import close_line_api, line_api_health_check, get_line_api_metrics
from config import settings

# 在應用程式啟動的最開始就設定日誌系統
setup_logging()

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 應用程式啟動時執行的程式碼
    startup_time = datetime.now(timezone.utc)
    logger.info("--- Application startup ---")
    
    startup_checks = {
        'google_sheets': {'status': 'unknown', 'error': None},
        'line_api': {'status': 'unknown', 'error': None}
    }
    
    try:
        # 1. 初始化非同步 Google Sheets 連接器並預熱快取
        logger.info("Initializing and warming up async Google Sheets connection...")
        try:
            gsheet_connector = AsyncGSheetConnector()
            await gsheet_connector.get_worksheet()  # 驗證連線並預熱快取
            startup_checks['google_sheets']['status'] = 'healthy'
            logger.info("✓ Google Sheets connection verified and cache warmed up.")
        except Exception as e:
            startup_checks['google_sheets']['status'] = 'unhealthy'
            startup_checks['google_sheets']['error'] = str(e)
            logger.error(f"✗ Google Sheets initialization failed: {e}", exc_info=True)
        
        # 2. 檢查 LINE API 客戶端健康狀態
        logger.info("Checking LINE API client health...")
        try:
            line_health = await line_api_health_check()
            if line_health.get('is_healthy', False):
                startup_checks['line_api']['status'] = 'healthy'
                logger.info("✓ LINE API client is healthy.")
            else:
                startup_checks['line_api']['status'] = 'unhealthy'
                startup_checks['line_api']['error'] = line_health.get('details', {}).get('message', 'Unknown error')
                logger.warning(f"✗ LINE API client health check failed: {line_health}")
        except Exception as e:
            startup_checks['line_api']['status'] = 'unhealthy'
            startup_checks['line_api']['error'] = str(e)
            logger.error(f"✗ LINE API health check failed: {e}", exc_info=True)
        
        # 3. 評估整體啟動狀態
        healthy_services = sum(1 for check in startup_checks.values() if check['status'] == 'healthy')
        total_services = len(startup_checks)
        
        if healthy_services == total_services:
            startup_status = 'healthy'
            logger.info(f"🎉 All {total_services} services started successfully.")
        elif healthy_services > 0:
            startup_status = 'degraded'
            logger.warning(f"⚠️ {healthy_services}/{total_services} services started successfully (degraded mode).")
        else:
            startup_status = 'unhealthy'
            logger.critical(f"💥 All services failed to start.")
        
        logger.info("All startup checks completed.")
        
    except Exception as e:
        # 捕獲任何未預期的啟動錯誤
        logger.critical(f"CRITICAL: Unexpected startup error: {e}", exc_info=True)
        startup_status = 'failed'
        startup_checks['unexpected_error'] = {'status': 'error', 'error': str(e)}
    
    # 將啟動資訊存儲在應用程式狀態中
    app.state.startup_time = startup_time.isoformat()
    app.state.startup_status = startup_status
    app.state.startup_checks = startup_checks
    app.state.startup_duration = (datetime.now(timezone.utc) - startup_time).total_seconds()
    
    logger.info(f"Application startup completed in {app.state.startup_duration:.3f}s with status: {startup_status}")

    yield

    # 應用程式關閉時執行的程式碼
    shutdown_time = datetime.now(timezone.utc)
    logger.info("--- Application shutdown ---")
    
    shutdown_errors = []
    
    try:
        # 1. 關閉 LINE API 客戶端
        logger.info("Closing LINE API client...")
        try:
            await close_line_api()
            logger.info("✓ LINE API client closed successfully.")
        except Exception as e:
            error_msg = f"✗ Error closing LINE API client: {e}"
            logger.error(error_msg, exc_info=True)
            shutdown_errors.append(error_msg)
        
        # 2. 可以添加其他清理邏輯
        # 例如：關閉資料庫連接、清理快取等
        
        # 3. 記錄關閉完成狀態
        shutdown_duration = (datetime.now(timezone.utc) - shutdown_time).total_seconds()
        
        if shutdown_errors:
            logger.warning(f"Application shutdown completed with {len(shutdown_errors)} errors in {shutdown_duration:.3f}s")
            for error in shutdown_errors:
                logger.error(f"Shutdown error: {error}")
        else:
            logger.info(f"✓ Application shutdown completed successfully in {shutdown_duration:.3f}s")
        
    except Exception as e:
        logger.error(f"💥 Critical error during application shutdown: {e}", exc_info=True)


app = FastAPI(
    lifespan=lifespan,
    title="LINE Bot Service",
    description="A FastAPI-based LINE Bot with Google Sheets integration",
    version="1.0.0"
)

# 包含來自其他模組的路由
app.include_router(line_webhook.router, tags=["Line Webhook"])
app.include_router(commands.router, prefix="/commands", tags=["Admin Commands"])

# 健康檢查端點
@app.get("/health")
async def basic_health_check():
    """基本健康檢查"""
    startup_status = getattr(app.state, 'startup_status', 'unknown')
    
    return {
        "status": startup_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "startup_time": getattr(app.state, 'startup_time', 'unknown'),
        "startup_duration": getattr(app.state, 'startup_duration', 0),
        "version": "1.0.0"
    }

@app.get("/health/detailed")
async def detailed_health_check():
    """詳細健康檢查 - 包含實時檢查"""
    checks = {}
    
    # 1. 啟動狀態檢查
    startup_checks = getattr(app.state, 'startup_checks', {})
    checks.update(startup_checks)
    
    # 2. 實時 LINE API 檢查
    try:
        line_health = await line_api_health_check()
        checks["line_api_realtime"] = {
            "status": "healthy" if line_health.get('is_healthy', False) else "unhealthy",
            "details": line_health
        }
    except Exception as e:
        checks["line_api_realtime"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # 3. 實時 Google Sheets 檢查
    try:
        gsheet_connector = AsyncGSheetConnector()
        await gsheet_connector.get_worksheet()
        checks["google_sheets_realtime"] = {"status": "healthy"}
    except Exception as e:
        checks["google_sheets_realtime"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # 4. 計算整體狀態
    healthy_count = sum(1 for check in checks.values() 
                       if isinstance(check, dict) and check.get("status") == "healthy")
    total_count = len([check for check in checks.values() if isinstance(check, dict)])
    
    if healthy_count == total_count and total_count > 0:
        overall_status = "healthy"
    elif healthy_count > 0:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"
    
    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "startup_time": getattr(app.state, 'startup_time', 'unknown'),
        "startup_duration": getattr(app.state, 'startup_duration', 0),
        "version": "1.0.0",
        "summary": {
            "healthy_services": healthy_count,
            "total_services": total_count,
            "health_percentage": round((healthy_count / total_count * 100) if total_count > 0 else 0, 1)
        },
        "checks": checks
    }

@app.get("/metrics")
async def get_metrics():
    """獲取應用程式監控指標"""
    try:
        line_metrics = await get_line_api_metrics()
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "application": {
                "name": "LINE Bot Service",
                "version": "1.0.0",
                "startup_time": getattr(app.state, 'startup_time', 'unknown'),
                "startup_duration": getattr(app.state, 'startup_duration', 0),
                "startup_status": getattr(app.state, 'startup_status', 'unknown')
            },
            "line_api": line_metrics,
            "system": {
                "python_version": f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}.{__import__('sys').version_info.micro}",
                "fastapi_version": __import__('fastapi').__version__
            }
        }
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

@app.get("/")
async def root():
    """根端點 - 提供基本服務資訊"""
    return {
        "service": "LINE Bot Service",
        "version": "1.0.0",
        "status": getattr(app.state, 'startup_status', 'unknown'),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoints": {
            "health": "/health",
            "detailed_health": "/health/detailed",
            "metrics": "/metrics",
            "webhook": "/callback",
            "admin_commands": "/commands"
        }
    }

if __name__ == "__main__":
    # 使用 uvicorn 啟動應用程式
    # log_config=None 確保 uvicorn 使用我們透過 setup_logging() 設定的 root logger
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=settings.PORT, 
        reload=True, 
        log_config=None,
        access_log=True
    )