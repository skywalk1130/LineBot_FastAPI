#!/bin/bash

PROJECT_ID="your-gcp-project-id" # 替換為您的 GCP 專案 ID
SERVICE_NAME="your-linebot-service" # 替換為您的 Cloud Run 服務名稱
REGION="asia-east1" # 替換為您的 Cloud Run 部署區域，例如 asia-east1 (台灣) 或 asia-northeast1 (東京)

# 警告: 以下環境變數設定不應包含敏感資訊在腳本中！
# 敏感資訊 (如 LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET, SMTP_PASSWORD, GOOGLE_SHEETS_CREDENTIALS_JSON)
# 應透過 Google Secret Manager 或在 Cloud Run 控制台手動設定。

# 建議使用 Secret Manager (最佳實踐)
# 首先，確保您已將敏感資訊儲存到 Secret Manager 中，並授予 Cloud Run 服務帳戶 Secret Manager Secret Accessor 角色。
# 例如：
# gcloud secrets create LINE_CHANNEL_ACCESS_TOKEN --data-file=/path/to/token.txt
# gcloud secrets add-iam-policy-binding LINE_CHANNEL_ACCESS_TOKEN --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" --role="roles/secretmanager.secretAccessor"

# 構建 Docker 映像
echo "Building Docker image..."
gcloud builds submit --tag gcr.io/${PROJECT_ID}/${SERVICE_NAME} .

# 部署到 Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image gcr.io/${PROJECT_ID}/${SERVICE_NAME} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars=GOOGLE_SHEET_ID="您的GoogleSheetID",GOOGLE_SHEET_WORKSHEET_NAME="工作表1",SMTP_SERVER="您的SMTP伺服器",SMTP_USERNAME="您的SMTP使用者名稱",EMAIL_SENDER="您的寄件人信箱",EMAIL_RECEIVER="您的收件人信箱",LINE_ADMIN_USER_ID="您的管理員LineID" \
  --set-secrets=LINE_CHANNEL_ACCESS_TOKEN=projects/${PROJECT_ID}/secrets/LINE_CHANNEL_ACCESS_TOKEN/versions/latest,\
                LINE_CHANNEL_SECRET=projects/${PROJECT_ID}/secrets/LINE_CHANNEL_SECRET/versions/latest,\
                SMTP_PASSWORD=projects/${PROJECT_ID}/secrets/SMTP_PASSWORD/versions/latest,\
                GOOGLE_SHEETS_CREDENTIALS_JSON=projects/${PROJECT_ID}/secrets/GOOGLE_SHEETS_CREDENTIALS_JSON/versions/latest

# 如果您不使用 Secret Manager，而是直接傳遞 JSON 字串 (不推薦用於生產環境)
# --set-env-vars=GOOGLE_SHEETS_CREDENTIALS_JSON="$(cat path/to/your/credentials.json | tr -d '\n\r')" # 注意：需要將 JSON 檔案內容轉為單行字串
# 但強烈建議使用 Secret Manager。

echo "Deployment complete."