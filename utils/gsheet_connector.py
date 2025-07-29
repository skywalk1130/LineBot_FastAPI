import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import settings
import json
import datetime
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class GSheetConnector:
    def __init__(self):
        self.client = None  # gspread client
        self._worksheet = None  # Cache for the worksheet object
        self._worksheet_last_fetched_time = None  # Timestamp of the last fetch
        self._cache_timeout = datetime.timedelta(seconds=300)  # 5-minute cache
        self._initialize_gspread_client()

    def _initialize_gspread_client(self):
        # 嘗試從環境變數 GOOGLE_SHEETS_CREDENTIALS_JSON 讀取 JSON 內容
        # 這比讀取檔案更安全，特別是在 Docker 環境中
        try:
            creds_json = json.loads(settings.GOOGLE_SHEETS_CREDENTIALS_JSON)
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
            self.client = gspread.authorize(creds)
            logger.info("Gspread client initialized successfully.")
        except Exception as e:
            # 在實際應用中，您可能希望在此處記錄更詳細的錯誤並妥善處理
            logger.error(f"Error initializing gspread client: {e}", exc_info=True)
            raise

    def get_worksheet(self):
        """
        獲取指定名稱的工作表，並使用快取機制以提高性能。
        快取每 5 分鐘會過期，以獲取最新的工作表參考。
        """
        now = datetime.datetime.now()
        # 檢查快取是否有效 (存在且未過期)
        if self._worksheet and self._worksheet_last_fetched_time and \
           (now - self._worksheet_last_fetched_time) < self._cache_timeout:
            return self._worksheet

        # 若快取無效或過期，則重新從 API 獲取
        try:
            spreadsheet = self.client.open_by_key(settings.GOOGLE_SHEET_ID)
            worksheet = spreadsheet.worksheet(settings.GOOGLE_SHEET_WORKSHEET_NAME)
            # 更新快取
            self._worksheet = worksheet
            self._worksheet_last_fetched_time = now
            return worksheet
        except gspread.exceptions.SpreadsheetNotFound:
            raise Exception(f"Google Sheet with ID {settings.GOOGLE_SHEET_ID} not found.")
        except gspread.exceptions.WorksheetNotFound:
            raise Exception(f"Worksheet '{settings.GOOGLE_SHEET_WORKSHEET_NAME}' not found in the spreadsheet.")
        except Exception as e:
            raise Exception(f"Error getting worksheet: {e}")

    def get_new_serial(self) -> int:
        """獲取新的序號 (從最後一列的序號加一)"""
        worksheet = self.get_worksheet()
        try:
            # 假設序號在第一列
            all_serials = worksheet.col_values(1)
            if not all_serials or not all_serials[-1].isdigit():
                return 1 # 如果沒有序號或最後一個不是數字，從 1 開始
            last_serial = int(all_serials[-1])
            return last_serial + 1
        except Exception as e:
            logger.error(f"Failed to get new serial number: {e}", exc_info=True)
            return 1 # 降級到從 1 開始

    def append_row(self, row_data: list):
        """向工作表追加一行資料"""
        worksheet = self.get_worksheet()
        try:
            worksheet.append_row(row_data)
            logger.info(f"Successfully appended row: {row_data}")
        except Exception as e:
            raise Exception(f"追加資料失敗: {e}")

    def update_status_by_serial(self, serial: str, new_status: str) -> bool:
        """根據序號高效地更新狀態"""
        worksheet = self.get_worksheet()
        try:
            # 假設序號在第一欄 (column 1)
            cell = worksheet.find(str(serial), in_column=1)
            if not cell:
                logger.warning(f"Serial number {serial} not found for status update.")
                return False

            # 獲取標頭以動態尋找 "處理狀態" 欄位
            header = worksheet.row_values(1)
            try:
                # gspread 列索引從 1 開始
                status_col_idx = header.index('處理狀態') + 1
            except ValueError:
                logger.error("Column '處理狀態' not found in the header. Please check the sheet format.")
                raise Exception("Sheet format error: '處理狀態' column is missing.")

            worksheet.update_cell(cell.row, status_col_idx, new_status)
            logger.info(f"Successfully updated status for serial {serial} to {new_status}")
            return True
        except gspread.exceptions.CellNotFound:
            logger.warning(f"Serial number {serial} not found for status update.")
            return False
        except Exception as e:
            logger.error(f"Failed to update status for serial {serial}: {e}", exc_info=True)
            raise Exception(f"更新狀態失敗: {e}")

    def find_row_by_serial(self, serial: str) -> Optional[dict]:
        """根據序號高效查找記錄，並將其作為字典返回。"""
        worksheet = self.get_worksheet()
        try:
            # 假設序號在第一欄 (column 1)
            cell = worksheet.find(str(serial), in_column=1)
            if not cell:
                logger.warning(f"Serial number {serial} not found in the sheet.")
                return None

            # 獲取標頭和找到的行
            header = worksheet.row_values(1)
            row_values = worksheet.row_values(cell.row)

            # 填充空值以確保 zip 操作時長度一致
            while len(row_values) < len(header):
                row_values.append('')

            logger.info(f"Found row for serial: {serial}")
            return dict(zip(header, row_values))
        except gspread.exceptions.CellNotFound:
            logger.warning(f"Serial number {serial} not found in the sheet.")
            return None
        except Exception as e:
            logger.error(f"Failed to find row by serial {serial}: {e}", exc_info=True)
            raise Exception(f"查詢失敗: {e}")