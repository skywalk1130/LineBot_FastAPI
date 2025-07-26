from linebot.v3.messaging import (
    AsyncApiClient,
    Configuration,
    MessagingApi
)
from config import settings

# v3 SDK 使用非同步客戶端
# 我們建立一個 FastAPI 的依賴注入函數來提供 MessagingApi 實例
def get_messaging_api() -> MessagingApi:
    """
    提供一個透過 FastAPI 依賴注入使用的 MessagingApi 實例。
    """
    configuration = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
    api_client = AsyncApiClient(configuration)
    # MessagingApi 包含了所有發送訊息相關的非同步方法
    return MessagingApi(api_client)