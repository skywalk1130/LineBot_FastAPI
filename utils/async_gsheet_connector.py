import gspread_asyncio
from oauth2client.service_account import ServiceAccountCredentials
from config import settings
import json
import datetime
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class AsyncGSheetConnector:
    """一個使用 gspread-asyncio 的非同步 Google Sheets 連接器"""
    def __init__(self):
        self._agcm = None  # AsyncGspreadClientManager
        self._worksheet = None
        self._worksheet_last_fetched_time = None
        self._cache_timeout = datetime.timedelta(seconds=300)

    def _get_creds(self):
        """輔助函式，從設定檔載入憑證。"""
        creds_json = json.loads(settings.GOOGLE_SHEETS_CREDENTIALS_JSON)
        return ServiceAccountCredentials.from_json_keyfile_dict(
            creds_json,
            ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        )

    async def _initialize_client(self):
        """如果非同步客戶端管理器尚未初始化，則進行初始化。"""
        if self._agcm is None:
            self._agcm = gspread_asyncio.AsyncioGspreadClientManager(self._get_creds)
            logger.info("AsyncGspreadClientManager initialized.")

    async def get_worksheet(self):
        """非同步獲取工作表，並使用基於時間的快取。"""
        await self._initialize_client()
        now = datetime.datetime.now()
        if self._worksheet and self._worksheet_last_fetched_time and \
           (now - self._worksheet_last_fetched_time) < self._cache_timeout:
            return self._worksheet

        try:
            client = await self._agcm.authorize()
            spreadsheet = await client.open_by_key(settings.GOOGLE_SHEET_ID)
            worksheet = await spreadsheet.worksheet(settings.GOOGLE_SHEET_WORKSHEET_NAME)
            self._worksheet = worksheet
            self._worksheet_last_fetched_time = now
            logger.info("Worksheet cache refreshed.")
            return worksheet
        except Exception as e:
            logger.error(f"Error getting async worksheet: {e}", exc_info=True)
            raise

    async def get_new_serial(self) -> int:
        worksheet = await self.get_worksheet()
        try:
            all_serials = await worksheet.col_values(1)
            if not all_serials or not all_serials[-1].isdigit():
                return 1
            last_serial = int(all_serials[-1])
            return last_serial + 1
        except Exception as e:
            logger.error(f"Failed to get new serial number asynchronously: {e}", exc_info=True)
            return 1

    async def append_row(self, row_data: list):
        worksheet = await self.get_worksheet()
        await worksheet.append_row(row_data)
        logger.info(f"Successfully appended row asynchronously: {row_data}")

    async def update_status_by_serial(self, serial: str, new_status: str) -> bool:
        worksheet = await self.get_worksheet()
        try:
            cell = await worksheet.find(str(serial), in_column=1)
            header = await worksheet.row_values(1)
            status_col_idx = header.index('處理狀態') + 1
            await worksheet.update_cell(cell.row, status_col_idx, new_status)
            logger.info(f"Successfully updated status for serial {serial} to {new_status} asynchronously.")
            return True
        except (gspread_asyncio.gspread.exceptions.CellNotFound, ValueError):
            logger.warning(f"Async update failed: Serial '{serial}' not found or sheet format error.")
            return False
        except Exception as e:
            logger.error(f"Failed to update status for serial {serial} asynchronously: {e}", exc_info=True)
            raise

    async def find_row_by_serial(self, serial: str) -> Optional[dict]:
        worksheet = await self.get_worksheet()
        try:
            cell = await worksheet.find(str(serial), in_column=1)
            header = await worksheet.row_values(1)
            row_values = await worksheet.row_values(cell.row)
            while len(row_values) < len(header):
                row_values.append('')
            logger.info(f"Found row for serial {serial} asynchronously.")
            return dict(zip(header, row_values))
        except gspread_asyncio.gspread.exceptions.CellNotFound:
            logger.warning(f"Async search: Serial number {serial} not found.")
            return None
        except Exception as e:
            logger.error(f"Failed to find row by serial {serial} asynchronously: {e}", exc_info=True)
            raise