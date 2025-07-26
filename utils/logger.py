import logging
import sys

def setup_logger():
    """設定一個簡單的日誌記錄器，將日誌輸出到標準輸出"""
    logger = logging.getLogger("linebot_logger")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger