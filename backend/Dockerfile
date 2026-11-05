# ==========================================
# Dockerfile: Japan Market Pulse Chronicle
# Cloud Run 最適化 Python 3.11-slim コンテナ
# ==========================================

FROM python:3.11-slim

# 標準出力のバッファリング無効化 & pyc生成防止
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app

# システム依存パッケージのインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 依存ライブラリのインストール
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコード & フロントエンド資材のコピー
COPY backend /app/backend
COPY frontend /app/frontend
COPY マーケティングデータ100選リスト_修正版.csv /app/マーケティングデータ100選リスト_修正版.csv
COPY data_collection_summary.csv /app/data_collection_summary.csv

# セキュリティのため非rootユーザー作成と権限設定
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

# Cloud Run の $PORT 環境変数を反映して uvicorn 起動
CMD exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT} --workers 1
