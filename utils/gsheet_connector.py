import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import settings
import json
import datetime

class GSheetConnector:
    def __init__(self):
        self.client = None
        self._initialize_gspread_client()

    def _initialize_gspread_client(self):
        # 嘗試從環境變數 GOOGLE_SHEETS_CREDENTIALS_JSON 讀取 JSON 內容
        # 這比讀取檔案更安全，特別是在 Docker 環境中
        try:
            creds_json = json.loads(settings.GOOGLE_SHEETS_CREDENTIALS_JSON)
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
            self.client = gspread.authorize(creds)
            print("Gspread client initialized successfully.")
        except Exception as e:
            print(f"Error initializing gspread client: {e}")
            # 在實際應用中，您可能希望在此處記錄更詳細的錯誤並妥善處理
            raise

    def get_worksheet(self):
        """獲取指定名稱的工作表"""
        try:
            spreadsheet = self.client.open_by_key(settings.GOOGLE_SHEET_ID)
            worksheet = spreadsheet.worksheet(settings.GOOGLE_SHEET_WORKSHEET_NAME)
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
            print(f"獲取新序號失敗: {e}")
            return 1 # 降級到從 1 開始

    def append_row(self, row_data: list):
        """向工作表追加一行資料"""
        worksheet = self.get_worksheet()
        try:
            worksheet.append_row(row_data)
            print(f"成功追加資料: {row_data}")
        except Exception as e:
            raise Exception(f"追加資料失敗: {e}")

    def update_status_by_serial(self, serial: str, new_status: str) -> bool:
        """根據序號更新狀態"""
        worksheet = self.get_worksheet()
        try:
            list_of_lists = worksheet.get_all_values()
            header = list_of_lists[0]
            data_rows = list_of_lists[1:]

            serial_col_idx = 0 # 假設序號在第一列
            status_col_idx = 4 # 假設狀態在第五列 (索引 4)

            for r_idx, row in enumerate(data_rows):
                if len(row) > serial_col_idx and row[serial_col_idx] == serial:
                    if len(row) > status_col_idx:
                        worksheet.update_cell(r_idx + 2, status_col_idx + 1, new_status) # +2 是因為標題行和基於 1 的索引
                        print(f"成功更新序號 {serial} 的狀態為 {new_status}")
                        return True
                    else:
                        print(f"行 {r_idx+2} 的列數不足以更新狀態。")
                        return False # 行太短無法更新狀態
            print(f"未找到序號 {serial}。")
            return False
        except Exception as e:
            raise Exception(f"更新狀態失敗: {e}")