#!/bin/bash

# 嚴格模式：遇到錯誤立即停止，使用未設定的變數時報錯
set -euo pipefail

# --- 設定 ---
# 請確保在執行此腳本前，已設定以下環境變數。
# 例如: export GCP_PROJECT_ID="your-project-id"
# ----------------
PROJECT_ID="${GCP_PROJECT_ID:?錯誤：請設定 GCP_PROJECT_ID 環境變數}"
SERVICE_NAME="${SERVICE_NAME:-linebot-service}" # 如果未設定，使用預設值 'linebot-service'
REGION="${GCP_REGION:-asia-east1}" # 如果未設定，使用預設值 'asia-east1'

# --- 安全性警告 ---
# 此腳本專為自動化 CI/CD 環境設計。
# 所有敏感資訊都必須儲存在 Google Secret Manager 中。
# 非敏感設定應在 Cloud Run 服務中直接設定，或透過環境變數傳入。
# 不要在這個腳本中硬式編碼任何密鑰或設定值。
# --------------------

# 步驟 1: 構建 Docker 映像並推送到 Google Container Registry
echo "Building Docker image..."
gcloud builds submit --tag "gcr.io/${PROJECT_ID}/${SERVICE_NAME}" .

# 步驟 2: 部署到 Cloud Run
echo "Deploying to Cloud Run..."

# 準備 Secret Manager 的參數 (確保這些 Secret 都已在您的 GCP 專案中建立)
SECRETS_CONFIG=(
  "LINE_CHANNEL_ACCESS_TOKEN=projects/${PROJECT_ID}/secrets/LINE_CHANNEL_ACCESS_TOKEN:latest"
  "LINE_CHANNEL_SECRET=projects/${PROJECT_ID}/secrets/LINE_CHANNEL_SECRET:latest"
  "SMTP_PASSWORD=projects/${PROJECT_ID}/secrets/SMTP_PASSWORD:latest"
  "GOOGLE_SHEETS_CREDENTIALS_JSON=projects/${PROJECT_ID}/secrets/GOOGLE_SHEETS_CREDENTIALS_JSON:latest"
)
SECRETS_PARAM=$(IFS=,; echo "${SECRETS_CONFIG[*]}")

# 準備非敏感環境變數的參數 (這些值應在您的 CI/CD 環境或本地 shell 中設定)
ENV_VARS_CONFIG=(
  "GOOGLE_SHEET_ID=${GOOGLE_SHEET_ID:?錯誤：請設定 GOOGLE_SHEET_ID}"
  "GOOGLE_SHEET_WORKSHEET_NAME=${GOOGLE_SHEET_WORKSHEET_NAME:-工作表1}"
  "SMTP_SERVER=${SMTP_SERVER:?錯誤：請設定 SMTP_SERVER}"
  "SMTP_USERNAME=${SMTP_USERNAME:?錯誤：請設定 SMTP_USERNAME}"
  "EMAIL_SENDER=${EMAIL_SENDER:?錯誤：請設定 EMAIL_SENDER}"
  "EMAIL_RECEIVER=${EMAIL_RECEIVER:?錯誤：請設定 EMAIL_RECEIVER}"
  "LINE_ADMIN_USER_ID=${LINE_ADMIN_USER_ID:-}" # 可選，允許為空
  "LOG_LEVEL=${LOG_LEVEL:-INFO}" # 可選，預設為 INFO
)
ENV_VARS_PARAM=$(IFS=,; echo "${ENV_VARS_CONFIG[*]}")

gcloud run deploy "${SERVICE_NAME}" \
  --image "gcr.io/${PROJECT_ID}/${SERVICE_NAME}" \
  --platform managed \
  --region "${REGION}" \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars="${ENV_VARS_PARAM}" \
  --set-secrets="${SECRETS_PARAM}"

echo "Deployment complete."
echo "Service URL: $(gcloud run services describe ${SERVICE_NAME} --platform managed --region ${REGION} --format 'value(status.url)')"