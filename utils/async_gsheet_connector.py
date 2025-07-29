import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json

import gspread_asyncio
from oauth2client.service_account import ServiceAccountCredentials
from config import settings

logger = logging.getLogger(__name__)

class GSheetApiClientError(Exception):
    """Google Sheets API 客戶端異常"""
    pass

class AsyncGSheetConnector:
    """
    非同步 Google Sheets 連接器
    使用 gspread-asyncio 實現真正的非同步操作
    """
    
    def __init__(self):
        self._client_manager = None
        self._worksheet_cache = None
        self._cache_timestamp = None
        self._cache_ttl = timedelta(minutes=5)
        self._lock = asyncio.Lock()
    
    async def _get_client_manager(self):
        """獲取 gspread-asyncio 客戶端管理器"""
        if self._client_manager is None:
            try:
                # 從環境變數載入憑證
                creds_dict = json.loads(settings.GOOGLE_SHEETS_CREDENTIALS_JSON)
                
                def auth_callback():
                    scope = [
                        'https://spreadsheets.google.com/feeds',
                        'https://www.googleapis.com/auth/drive'
                    ]
                    return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
                
                self._client_manager = gspread_asyncio.AsyncioGspreadClientManager(auth_callback)
                logger.info("Async Google Sheets client manager initialized")
                
            except json.JSONDecodeError as e:
                error_msg = f"Invalid JSON in GOOGLE_SHEETS_CREDENTIALS_JSON: {e}"
                logger.error(error_msg)
                raise GSheetApiClientError(error_msg)
            except Exception as e:
                error_msg = f"Failed to initialize async gspread client: {e}"
                logger.error(error_msg, exc_info=True)
                raise GSheetApiClientError(error_msg)
        
        return self._client_manager
    
    async def get_worksheet(self):
        """
        獲取工作表，使用快取提升性能
        """
        async with self._lock:
            now = datetime.now()
            
            # 檢查快取是否有效
            if (self._worksheet_cache is not None and 
                self._cache_timestamp is not None and 
                now - self._cache_timestamp < self._cache_ttl):
                return self._worksheet_cache
            
            try:
                # 重新獲取工作表
                client_manager = await self._get_client_manager()
                client = await client_manager.authorize()
                
                spreadsheet = await client.open_by_key(settings.GOOGLE_SHEET_ID)
                worksheet = await spreadsheet.worksheet(settings.GOOGLE_SHEET_WORKSHEET_NAME)
                
                # 更新快取
                self._worksheet_cache = worksheet
                self._cache_timestamp = now
                
                logger.debug(f"Worksheet '{settings.GOOGLE_SHEET_WORKSHEET_NAME}' loaded and cached")
                return worksheet
                
            except Exception as e:
                error_msg = f"Failed to get worksheet: {e}"
                logger.error(error_msg, exc_info=True)
                raise GSheetApiClientError(error_msg)
    
    async def get_new_serial(self) -> int:
        """獲取新的序號"""
        try:
            worksheet = await self.get_worksheet()
            # 獲取第一列的所有值
            col_values = await worksheet.col_values(1)
            
            if not col_values:
                return 1
            
            # 找到最後一個數字序號
            last_serial = 0
            for value in reversed(col_values):
                if value.isdigit():
                    last_serial = int(value)
                    break
            
            return last_serial + 1
            
        except Exception as e:
            logger.error(f"Failed to get new serial: {e}", exc_info=True)
            raise GSheetApiClientError(f"Failed to get new serial: {e}")
    
    async def append_row(self, row_data: List[Any]):
        """新增一行資料"""
        try:
            worksheet = await self.get_worksheet()
            await worksheet.append_row(row_data)
            logger.info(f"Row appended successfully: {row_data}")
            
        except Exception as e:
            error_msg = f"Failed to append row: {e}"
            logger.error(error_msg, exc_info=True)
            raise GSheetApiClientError(error_msg)
    
    async def find_row_by_serial(self, serial: str) -> Optional[Dict[str, Any]]:
        """根據序號查找行資料"""
        try:
            worksheet = await self.get_worksheet()
            
            # 尋找序號
            try:
                cell = await worksheet.find(str(serial), in_column=1)
            except Exception:
                logger.warning(f"Serial {serial} not found")
                return None
            
            if not cell:
                return None
            
            # 獲取標題行和資料行
            header_values = await worksheet.row_values(1)
            row_values = await worksheet.row_values(cell.row)
            
            # 確保長度一致
            while len(row_values) < len(header_values):
                row_values.append('')
            
            return dict(zip(header_values, row_values))
            
        except Exception as e:
            error_msg = f"Failed to find row by serial {serial}: {e}"
            logger.error(error_msg, exc_info=True)
            raise GSheetApiClientError(error_msg)
    
    async def update_status_by_serial(self, serial: str, new_status: str) -> bool:
        """根據序號更新狀態"""
        try:
            worksheet = await self.get_worksheet()
            
            # 尋找序號
            try:
                cell = await worksheet.find(str(serial), in_column=1)
            except Exception:
                logger.warning(f"Serial {serial} not found for status update")
                return False
            
            if not cell:
                return False
            
            # 找到狀態欄位
            header_values = await worksheet.row_values(1)
            try:
                status_col_idx = header_values.index('處理狀態') + 1
            except ValueError:
                raise GSheetApiClientError("Column '處理狀態' not found in header")
            
            # 更新狀態
            await worksheet.update_cell(cell.row, status_col_idx, new_status)
            logger.info(f"Status updated for serial {serial}: {new_status}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to update status for serial {serial}: {e}"
            logger.error(error_msg, exc_info=True)
            raise GSheetApiClientError(error_msg)

# 全域實例管理
_gsheet_connector: Optional[AsyncGSheetConnector] = None
_connector_lock = asyncio.Lock()

async def get_gsheet_connector() -> AsyncGSheetConnector:
    """獲取全域 Google Sheets 連接器實例"""
    global _gsheet_connector
    
    if _gsheet_connector is not None:
        return _gsheet_connector
    
    async with _connector_lock:
        if _gsheet_connector is None:
            _gsheet_connector = AsyncGSheetConnector()
            logger.info("Created new AsyncGSheetConnector instance")
        return _gsheet_connector