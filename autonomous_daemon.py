"""
Japan Market Pulse Chronicle - Autonomous Continuous Pipeline Daemon
1日1回自律的にデータ取得・統計解析・可視化更新・Git push・Cloudflareデプロイを実行（デイリーパイプライン）
"""

import os
import sys
import time
import json
import subprocess
import logging
from datetime import datetime, timedelta

# パス設定 & backend パスの追加
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

DAEMON_LOG_FILE = os.path.join(LOGS_DIR, "autonomous_pipeline.log")
METRICS_LOG_FILE = os.path.join(LOGS_DIR, "pipeline_metrics.json")
DEPLOY_LOG_FILE = os.path.join(LOGS_DIR, "deployment_history.log")

# ロギング設定
logger = logging.getLogger("autonomous_daemon")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler(DAEMON_LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s"))
    logger.addHandler(stream_handler)

def run_command(cmd, desc):
    """コマンド実行ヘルパー（UTF-8エンコーディング & エラー置換）"""
    logger.info(f"Running: {desc} -> {cmd}")
    try:
        res = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=BASE_DIR,
            timeout=180
        )
        stdout_txt = (res.stdout or "").strip()
        stderr_txt = (res.stderr or "").strip()
        if res.returncode == 0:
            logger.info(f"SUCCESS: {desc}")
            return True, stdout_txt
        else:
            logger.warning(f"WARNING: {desc} exited with {res.returncode}. Output: {stderr_txt or stdout_txt}")
            return False, stderr_txt
    except Exception as e:
        logger.error(f"ERROR: {desc} failed with exception: {e}")
        return False, str(e)

def update_pipeline_cycle(iteration: int):
    """1サイクルの実行"""
    cycle_start = datetime.now()
    logger.info("=" * 70)
    logger.info(f"CYCLE #{iteration:03d} STARTING AT {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)

    # 1. データサイエンス計算モジュールの実行
    logger.info("[Step 1/5] Executing Data Science Analytics Engine...")
    try:
        from analysis_engine import generate_advanced_analytics_payload
        from backend.main import load_latest_cache, save_latest_cache
        
        current_data = load_latest_cache()
        updated_data = generate_advanced_analytics_payload(current_data)
        updated_data["updated_date"] = cycle_start.strftime("%Y-%m-%d")
        updated_data["sync_status"] = f"AUTONOMOUS SYNC #{iteration:03d} ({cycle_start.strftime('%H:%M:%S JST')})"
        
        # キャッシュ保存
        save_latest_cache(updated_data)
        logger.info(f"Analytics engine calculated successfully: 10 themes, {len(updated_data['sensitivity_matrix']['rows'])} matrix rows.")
    except Exception as e:
        logger.error(f"Failed in Data Science Engine: {e}")

    # 2. フロントエンド 内蔵データセットの同期更新
    logger.info("[Step 2/5] Synchronizing Frontend Embedded Dataset...")
    frontend_path = os.path.join(BASE_DIR, "frontend", "index.html")
    if os.path.exists(frontend_path):
        try:
            with open(frontend_path, "r", encoding="utf-8") as f:
                content = f.read()

            content = content.replace(
                'id="updatedDateDisplay">2026-11-05<',
                f'id="updatedDateDisplay">{cycle_start.strftime("%Y-%m-%d")}<'
            )
            with open(frontend_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info("Frontend embedded metadata updated.")
        except Exception as e:
            logger.error(f"Error updating frontend file: {e}")

    # 3. Git コミット & GitHub への push
    logger.info("[Step 3/5] Pushing autonomous updates to GitHub...")
    commit_msg = f"chore(autonomous): sync cycle #{iteration:03d} at {cycle_start.strftime('%Y-%m-%d %H:%M JST')}"
    run_command(f'git add -A && git commit -m "{commit_msg}"', "Git Commit")
    ok_push, push_out = run_command("git push origin main", "Git Push")

    # 4. Cloudflare Pages への自動デプロイ
    logger.info("[Step 4/5] Deploying updated artifacts to Cloudflare Pages...")
    ok_deploy, deploy_out = run_command(
        "npx --yes wrangler pages deploy frontend --project-name japan-market-pulse --commit-dirty=true",
        "Cloudflare Pages Deployment"
    )

    # 5. 実行メトリクスの記録
    cycle_duration = (datetime.now() - cycle_start).total_seconds()
    metrics = {
        "cycle": iteration,
        "timestamp": cycle_start.isoformat(),
        "duration_seconds": round(cycle_duration, 2),
        "git_push_success": ok_push,
        "cloudflare_deploy_success": ok_deploy,
        "live_url": "https://japan-market-pulse.pages.dev"
    }
    
    with open(DEPLOY_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{cycle_start.strftime('%Y-%m-%d %H:%M:%S')}] Cycle #{iteration:03d} | Deploy: {ok_deploy} | Push: {ok_push} | URL: https://japan-market-pulse.pages.dev\n")

    history = []
    if os.path.exists(METRICS_LOG_FILE):
        try:
            with open(METRICS_LOG_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
    history.append(metrics)
    with open(METRICS_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    logger.info(f"CYCLE #{iteration:03d} COMPLETED in {cycle_duration:.1f}s.")
    logger.info("=" * 70)

def main():
    logger.info("*" * 70)
    logger.info("AUTONOMOUS CONTINUOUS PIPELINE DAEMON INITIALIZED (DAILY MODE)")
    logger.info("Schedule: 1 Execution / Day (Interval: 24 Hours)")
    logger.info(f"Logs: {DAEMON_LOG_FILE}")
    logger.info("*" * 70)

    iteration = 1
    INTERVAL_SECONDS = int(os.getenv("PIPELINE_INTERVAL_SECONDS", 86400))  # 1日1回（24時間）

    while True:
        try:
            update_pipeline_cycle(iteration)
        except Exception as e:
            logger.error(f"Unhandled exception in cycle #{iteration}: {e}")

        iteration += 1
        next_run = datetime.now() + timedelta(seconds=INTERVAL_SECONDS)
        logger.info(f"Sleeping for {INTERVAL_SECONDS} seconds (24h). Next cycle #{iteration:03d} scheduled at {next_run.strftime('%Y-%m-%d %H:%M:%S')}...")
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
