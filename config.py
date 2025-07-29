from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Any, Literal
from pydantic import validator, EmailStr

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
    EMAIL_SENDER: EmailStr
    EMAIL_RECEIVER: List[EmailStr] # 收件人信箱，在 .env 中用逗號分隔

    # Line Bot Admin User ID (optional)
    LINE_ADMIN_USER_ID: str = ""

    # Logging Level
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Docker container port
    PORT: int = 8080 # For Cloud Run

    @validator('EMAIL_RECEIVER', pre=True)
    def parse_email_list(cls, v: Any) -> List[str]:
        """允許從逗號分隔的字串解析收件人列表"""
        if isinstance(v, str):
            return [email.strip() for email in v.split(',')]
        if isinstance(v, list):
            return v
        raise ValueError("EMAIL_RECEIVER must be a comma-separated string or a list")

    @validator('PORT', 'SMTP_PORT')
    def validate_port(cls, v: int) -> int:
        """驗證端口號是否在有效範圍內"""
        if not 1 <= v <= 65535:
            raise ValueError('Port number must be between 1 and 65535')
        return v

settings = Settings()