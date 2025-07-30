# LINE Bot Service with Google Sheets Integration

> 一個基於 FastAPI 的 LINE Bot 服務，整合 Google Sheets 進行數據管理，支援自動郵件通知功能。

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-green.svg)](https://fastapi.tiangolo.com/)
[![LINE Bot SDK](https://img.shields.io/badge/LINE%20Bot%20SDK-3.17.1-brightgreen.svg)](https://github.com/line/line-bot-sdk-python)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ 功能特色

- 🤖 **LINE Bot 整合**: 基於 LINE Bot SDK v3 的現代化聊天機器人
- 📊 **Google Sheets 數據管理**: 異步操作 Google Sheets 進行數據存取
- 📧 **自動郵件通知**: 支援 SMTP 郵件發送功能
- 🚀 **高性能異步架構**: 使用 FastAPI + asyncio 實現高併發處理
- 📋 **健康檢查**: 完整的健康檢查和監控端點
- 🔒 **安全配置**: 使用 Google Secret Manager 進行敏感資料管理
- 🐳 **容器化部署**: 支援 Docker 和 Google Cloud Run 部署
- 📝 **完整日誌系統**: 結構化日誌記錄和錯誤追蹤

## 🏗️ 系統架構

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   LINE Platform │────│   FastAPI App   │────│  Google Sheets  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                       ┌──────┴──────┐
                       │             │
                ┌──────▼──────┐ ┌───▼────┐
                │ Email SMTP  │ │ Logger │
                └─────────────┘ └────────┘
```

## 🚀 快速開始

### 環境需求

- Python 3.9+
- Google Cloud Platform 帳戶
- LINE Developers 帳戶
- SMTP 郵件服務（如 Gmail）

### 安裝步驟

1. **複製專案**
   ```bash
   git clone <repository-url>
   cd linebot-service
   ```

2. **安裝依賴**
   ```bash
   pip install -r requirements.txt
   ```

3. **環境變數設定**
   
   創建 `.env` 檔案：
   ```env
   # LINE Bot Settings
   LINE_CHANNEL_ACCESS_TOKEN=your_line_access_token
   LINE_CHANNEL_SECRET=your_line_channel_secret
   LINE_ADMIN_USER_ID=your_admin_user_id
   
   # Google Sheets Settings
   GOOGLE_SHEETS_CREDENTIALS_JSON={"type":"service_account",...}
   GOOGLE_SHEET_ID=your_google_sheet_id
   GOOGLE_SHEET_WORKSHEET_NAME=工作表1
   
   # Email Settings
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your_email@gmail.com
   SMTP_PASSWORD=your_app_password
   EMAIL_SENDER=your_email@gmail.com
   EMAIL_RECEIVER=receiver1@gmail.com,receiver2@gmail.com
   
   # Application Settings
   LOG_LEVEL=INFO
   PORT=8080
   ```

4. **本地運行**
   ```bash
   python main.py
   ```

## 📦 Docker 部署

### 本地 Docker 運行

```bash
# 建構映像
docker build -t linebot-service .

# 運行容器
docker run -p 8080:8080 --env-file .env linebot-service
```

### Google Cloud Run 部署

1. **設定環境變數**
   ```bash
   export GCP_PROJECT_ID="your-project-id"
   export SERVICE_NAME="linebot-service"
   export GCP_REGION="asia-east1"
   ```

2. **執行部署腳本**
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

## 🔧 API 文檔

### 主要端點

| 端點 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 服務基本資訊 |
| `/health` | GET | 基本健康檢查 |
| `/health/detailed` | GET | 詳細健康檢查 |
| `/metrics` | GET | 監控指標 |
| `/callback` | POST | LINE Webhook 回調 |
| `/commands/send-test-email` | POST | 發送測試郵件 |

### 健康檢查回應範例

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "startup_time": "2024-01-01T11:59:30Z",
  "startup_duration": 2.5,
  "version": "1.0.0",
  "summary": {
    "healthy_services": 2,
    "total_services": 2,
    "health_percentage": 100.0
  }
}
```

## 💬 LINE Bot 指令

| 指令 | 功能 |
|------|------|
| `登記` | 進行用戶登記，自動分配序號並記錄到 Google Sheets |

### 使用流程

1. 用戶在 LINE 中發送「登記」
2. 系統自動獲取用戶資料
3. 分配新序號並記錄到 Google Sheets
4. 發送確認訊息給用戶
5. 自動發送通知郵件給管理員

## 📊 Google Sheets 格式

建議的工作表欄位結構：

| 序號 | 使用者ID | 使用者名稱 | 登記時間 | 處理狀態 |
|------|----------|-----------|----------|----------|
| 1 | U1234... | 張三 | 2024-01-01 12:00:00 | 已處理 |

## 🔒 安全性考量

### Google Secret Manager 設定

在 GCP 中創建以下 Secrets：

- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_CHANNEL_SECRET`
- `SMTP_PASSWORD`
- `GOOGLE_SHEETS_CREDENTIALS_JSON`

### 最佳實踐

- ✅ 使用 Service Account 金鑰進行 Google Sheets 授權
- ✅ 敏感資料存放在 Secret Manager
- ✅ 啟用 HTTPS 和請求簽名驗證
- ✅ 定期輪換 API 金鑰
- ✅ 限制 Service Account 權限範圍

## 📈 監控與日誌

### 日誌級別

- `DEBUG`: 詳細調試資訊
- `INFO`: 一般運行資訊
- `WARNING`: 警告訊息
- `ERROR`: 錯誤訊息
- `CRITICAL`: 嚴重錯誤

### 監控指標

系統提供以下監控指標：

- LINE API 請求統計
- Google Sheets 操作性能
- 郵件發送成功率
- 系統健康狀態
- 回應時間統計

## 🧪 測試

### 單元測試

```bash
# 安裝測試依賴
pip install pytest pytest-asyncio

# 運行測試
pytest tests/ -v
```

### 手動測試

1. **健康檢查**
   ```bash
   curl http://localhost:8080/health
   ```

2. **發送測試郵件**
   ```bash
   curl -X POST http://localhost:8080/commands/send-test-email
   ```

## 🚨 故障排除

### 常見問題

1. **Google Sheets 連接失敗**
   - 檢查 Service Account 金鑰格式
   - 確認工作表 ID 和名稱正確
   - 驗證工作表共享權限

2. **LINE Webhook 無法接收**
   - 確認 Webhook URL 設定正確
   - 檢查網路連通性
   - 驗證簽名設定

3. **郵件發送失敗**
   - 檢查 SMTP 設定
   - 確認應用程式密碼正確
   - 驗證收件者信箱格式

### 日誌分析

查看詳細錯誤資訊：

```bash
# Docker 容器日誌
docker logs <container-id>

# Cloud Run 日誌
gcloud logs read --service=linebot-service
```

## 📝 開發指南

### 專案結構

```
linebot-service/
├── main.py                 # FastAPI 應用程式入口
├── config.py              # 配置管理
├── requirements.txt       # Python 依賴
├── Dockerfile            # Docker 配置
├── deploy.sh             # 部署腳本
├── routers/              # API 路由
│   ├── line_webhook.py   # LINE Webhook 處理
│   └── commands.py       # 管理指令
├── services/             # 業務邏輯服務
│   ├── line_message_handler.py  # 訊息處理
│   ├── email_sender.py          # 郵件發送
│   └── async_email_sender.py    # 異步郵件發送
├── utils/                # 工具類
│   ├── async_gsheet_connector.py  # Google Sheets 連接器
│   ├── line_api_client.py         # LINE API 客戶端
│   └── logger.py                  # 日誌設定
└── tests/                # 測試檔案
```

### 代碼規範

- 使用 Type Hints
- 遵循 PEP 8 代碼風格
- 異步函數優先使用 `async/await`
- 完整的錯誤處理和日誌記錄

## 🤝 貢獻指南

1. Fork 此專案
2. 創建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 開啟 Pull Request

## 📄 授權

本專案採用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 檔案

## 📞 支援與聯繫

- 🐛 回報問題：[GitHub Issues](https://github.com/your-username/linebot-service/issues)
- 📧 Email：your-email@example.com
- 📖 文檔：[Wiki](https://github.com/your-username/linebot-service/wiki)

## 🎯 未來規劃

- [ ] 支援多語言回應
- [ ] 添加更多 LINE 互動功能（Quick Reply、Flex Message）
- [ ] 實現用戶狀態管理
- [ ] 添加資料分析儀表板
- [ ] 支援檔案上傳功能
- [ ] 整合更多第三方服務

---

⭐ 如果這個專案對您有幫助，請給我們一個 Star！