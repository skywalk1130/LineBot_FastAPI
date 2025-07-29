import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, List, Any

import gspread_asyncio
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError, CellNotFound

from config import settings # 假設設定檔位於專案根目錄

logger = logging.getLogger(__name__)

class GSheetApiClientError(Exception):
    """用於 Google Sheets API 特定錯誤的自訂例外。"""
    pass

class AsyncGSheetConnector:
    """
    一個使用 gspread-asyncio 的非同步 Google Sheets 連接器。
    - 支援基於時間的快取。
    - 寫入操作後自動清除快取，確保資料一致性。
    - 透過 config 進行配置。
    """
    def __init__(self, cache_timeout_seconds: int = 60):
        def get_creds():
            """輔助函式，從設定檔載入憑證。"""
            creds_json = json.loads(settings.GOOGLE_SHEETS_CREDENTIALS_JSON)
            return Credentials.from_service_account_info(
                creds_json,
                scopes=['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            )

        self._agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)
        self._cache_timeout = timedelta(seconds=cache_timeout_seconds)
        self._worksheet: Optional[gspread_asyncio.AsyncioGspreadWorksheet] = None
        self._worksheet_last_fetched_time: Optional[datetime] = None
        self._lock = asyncio.Lock()  # 確保快取操作的原子性
        logger.info(f"AsyncGSheetConnector initialized with a cache timeout of {cache_timeout_seconds} seconds.")

    async def get_worksheet(self) -> gspread_asyncio.AsyncioGspreadWorksheet:
        """
        獲取工作表實例，優先從快取中讀取。
        如果快取過期或不存在，則重新從 API 獲取。
        """
        async with self._lock:
            now = datetime.utcnow()
            is_cache_valid = (
                self._worksheet and
                self._worksheet_last_fetched_time and
                (now - self._worksheet_last_fetched_time) < self._cache_timeout
            )
            if is_cache_valid:
                logger.debug("Returning cached worksheet.")
                return self._worksheet

            logger.info("Refreshing worksheet cache (expired or invalidated).")
            try:
                agc = await self._agcm.authorize()
                spreadsheet = await agc.open_by_key(settings.GOOGLE_SHEET_ID)
                self._worksheet = await spreadsheet.worksheet(settings.GOOGLE_SHEET_WORKSHEET_NAME)
                self._worksheet_last_fetched_time = now
                return self._worksheet
            except APIError as e:
                raise GSheetApiClientError(f"Failed to fetch worksheet from Google API: {e}") from e

    async def invalidate_cache(self):
        """手動清除工作表快取，通常在寫入操作後呼叫。"""
        async with self._lock:
            if self._worksheet is not None:
                self._worksheet = None
                self._worksheet_last_fetched_time = None
                logger.info("Worksheet cache has been manually invalidated.")

    async def append_row(self, row_data: List[Any], value_input_option: str = 'USER_ENTERED'):
        """向工作表追加一行資料，並自動清除快取。"""
        try:
            worksheet = await self.get_worksheet()
            await worksheet.append_row(row_data, value_input_option=value_input_option)
            await self.invalidate_cache() # 寫入後自動清除快取
        except APIError as e:
            raise GSheetApiClientError(f"Failed to append row: {e}") from e

    async def get_new_serial(self) -> int:
        """獲取新的序號。假設序號是資料行的數量。"""
        try:
            worksheet = await self.get_worksheet()
            all_values = await worksheet.get_all_values()
            # 假設第一行為標題。新序號等於現有資料行總數。
            # 例：只有標題時 len=1，新序號為1。有標題+1筆資料時 len=2，新序號為2。
            return len(all_values)
        except APIError as e:
            raise GSheetApiClientError(f"Failed to get all values for new serial: {e}") from e

    async def update_status_by_serial(self, serial: str, new_status: str) -> bool:
        """根據序號更新狀態，並自動清除快取。"""
        worksheet = await self.get_worksheet()
        try:
            cell = await worksheet.find(str(serial), in_column=1)
            header = await worksheet.row_values(1)
            status_col_idx = header.index('處理狀態') + 1
            await worksheet.update_cell(cell.row, status_col_idx, new_status)
            await self.invalidate_cache() # 更新後自動清除快取
            logger.info(f"Successfully updated status for serial {serial} to {new_status}.")
            return True
        except (CellNotFound, ValueError) as e:
            logger.warning(f"Update failed: Serial '{serial}' not found or '處理狀態' column missing. Error: {e}")
            return False
        except APIError as e:
            raise GSheetApiClientError(f"Failed to update status for serial {serial}: {e}") from e

    async def find_row_by_serial(self, serial: str) -> Optional[dict]:
        """根據序號查找整行資料。"""
        worksheet = await self.get_worksheet()
        try:
            cell = await worksheet.find(str(serial), in_column=1)
            header = await worksheet.row_values(1)
            row_values = await worksheet.row_values(cell.row)
            logger.info(f"Found row for serial {serial}.")
            return dict(zip(header, row_values))
        except CellNotFound:
            logger.warning(f"Search failed: Serial number {serial} not found.")
            return None
        except APIError as e:
            raise GSheetApiClientError(f"Failed to find row by serial {serial}: {e}") from e