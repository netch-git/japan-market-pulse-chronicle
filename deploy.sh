#!/usr/bin/env bash
# ==============================================================================
# deploy.sh: Japan Market Pulse Chronicle デプロイ & スケジューラ登録スクリプト
# GCP Always Free（常時無料枠）構成対応
# ==============================================================================

set -euo pipefail

# 1. 基本設定パラメータ（必要に応じて変更）
PROJECT_ID=${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || echo "")}
REGION=${GCP_REGION:-"asia-northeast1"}
SERVICE_NAME="market-pulse-chronicle"
JOB_NAME="market-pulse-weekly-update"
GEMINI_API_KEY=${GEMINI_API_KEY:-""}
GEMINI_MODEL=${GEMINI_MODEL:-"gemini-2.5-flash"}
UPDATE_SECRET_TOKEN=${UPDATE_SECRET_TOKEN:-"secret-market-pulse-token-2026"}

if [ -z "$PROJECT_ID" ]; then
  echo "Error: GCP Project ID is not set. Please set GCP_PROJECT_ID or run 'gcloud config set project <PROJECT_ID>'."
  exit 1
fi

echo "=========================================================="
echo " Starting Deployment for $SERVICE_NAME"
echo " Project: $PROJECT_ID | Region: $REGION"
echo " AI Model: $GEMINI_MODEL"
echo "=========================================================="

# 2. 必要なGCP APIの有効化
echo "[Step 1/4] Enabling required Google Cloud APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  cloudscheduler.googleapis.com \
  firestore.googleapis.com \
  --project="$PROJECT_ID"

# 3. Cloud Run へのビルド & デプロイ（Always Free 最適化構成）
# - memory: 512Mi, cpu: 1, max-instances: 1, min-instances: 0, timeout: 300s
echo "[Step 2/4] Building container and deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --platform managed \
  --region "$REGION" \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 1 \
  --timeout 300 \
  --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID,GEMINI_API_KEY=$GEMINI_API_KEY,GEMINI_MODEL=$GEMINI_MODEL,UPDATE_SECRET_TOKEN=$UPDATE_SECRET_TOKEN" \
  --project="$PROJECT_ID"

# サービスURLの取得
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --platform managed --region "$REGION" --format 'value(status.url)' --project="$PROJECT_ID")
echo "Deployed successfully! Service URL: $SERVICE_URL"

# 4. Cloud Scheduler ジョブの登録・更新（毎週月曜 09:00 JST = UTC 日曜 24:00 / 月曜 00:00）
echo "[Step 3/4] Configuring Cloud Scheduler (Every Monday 09:00 JST)..."
if gcloud scheduler jobs describe "$JOB_NAME" --location="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "Updating existing Cloud Scheduler job..."
  gcloud scheduler jobs update http "$JOB_NAME" \
    --location="$REGION" \
    --schedule="0 9 * * 1" \
    --time-zone="Asia/Tokyo" \
    --uri="${SERVICE_URL}/api/update" \
    --http-method=POST \
    --headers="X-Update-Token=${UPDATE_SECRET_TOKEN}" \
    --project="$PROJECT_ID"
else
  echo "Creating new Cloud Scheduler job..."
  gcloud scheduler jobs create http "$JOB_NAME" \
    --location="$REGION" \
    --schedule="0 9 * * 1" \
    --time-zone="Asia/Tokyo" \
    --uri="${SERVICE_URL}/api/update" \
    --http-method=POST \
    --headers="X-Update-Token=${UPDATE_SECRET_TOKEN}" \
    --project="$PROJECT_ID"
fi

# 5. 初期データの投入テスト（手動トリガー実行）
echo "[Step 4/4] Triggering initial update via API..."
curl -s -X POST "${SERVICE_URL}/api/update" \
  -H "X-Update-Token: ${UPDATE_SECRET_TOKEN}" || true

echo ""
echo "=========================================================="
echo " Deployment Completed!"
echo " Web Application URL: $SERVICE_URL"
echo " API Endpoint: ${SERVICE_URL}/api/latest"
echo " Scheduler: Weekly Monday 09:00 JST"
echo "=========================================================="
