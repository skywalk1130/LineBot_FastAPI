import logging
import sys
from config import settings

def setup_logging():
    """
    設定全域根日誌記錄器 (root logger)。
    從設定檔讀取日誌級別，並將日誌輸出到標準輸出。
    此函數應在應用程式啟動時僅調用一次。
    """
    # 獲取根日誌記錄器
    root_logger = logging.getLogger()

    # 如果根記錄器已經有處理器，則直接返回，防止日誌重複輸出
    if root_logger.handlers:
        return

    # 從設定檔設定日誌級別
    root_logger.setLevel(settings.LOG_LEVEL.upper())

    handler = logging.StreamHandler(sys.stdout)
    # 使用更詳細的日誌格式，包含檔案名稱和行號
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s (%(filename)s:%(lineno)d)'
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    logging.info(f"Logging configured with level: {settings.LOG_LEVEL}")