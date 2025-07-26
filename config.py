from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # Line Bot API Keys
    LINE_CHANNEL_ACCESS_TOKEN: str
    LINE_CHANNEL_SECRET: str

    # Google Sheets Settings
    GOOGLE_SHEETS_CREDENTIALS_JSON: str # 或路徑，建議使用 Secret Manager
    GOOGLE_SHEET_ID: str
    GOOGLE_SHEET_WORKSHEET_NAME: str = "工作表1" # 預設工作表名稱

    # SMTP Settings for Email
    SMTP_SERVER: str
    SMTP_PORT: int = 587
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    EMAIL_SENDER: str
    EMAIL_RECEIVER: List[str] # 收件人信箱，在 .env 中用逗號分隔

    # Line Bot Admin User ID (optional)
    LINE_ADMIN_USER_ID: str = ""

    # Docker container port
    PORT: int = 8080 # For Cloud Run

settings = Settings()