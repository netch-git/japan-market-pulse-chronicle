"""
Japan Market Pulse Chronicle - Autonomous Continuous Pipeline Daemon
明朝04:00まで自律的にデータ取得・統計解析・可視化更新・Git push・Cloudflareデプロイを反復実行
"""

import os
import sys
import time
import json
import subprocess
import logging
from datetime import datetime, timedelta

# パス設定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

DAEMON_LOG_FILE = os.path.join(LOGS_DIR, "autonomous_pipeline.log")
METRICS_LOG_FILE = os.path.join(LOGS_DIR, "pipeline_metrics.json")
DEPLOY_LOG_FILE = os.path.join(LOGS_DIR, "deployment_history.log")

# ロギング設定
logger = logging.getLogger("autonomous_daemon")
logger.setLevel(logging.INFO)

# ファイルハンドラ & ストリームハンドラ
file_handler = logging.FileHandler(DAEMON_LOG_FILE, encoding="utf-8")
file_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
logger.addHandler(file_handler)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s"))
logger.addHandler(stream_handler)

def run_command(cmd, desc):
    """コマンド実行ヘルパー"""
    logger.info(f"Running: {desc} -> {cmd}")
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=BASE_DIR, timeout=180)
        if res.returncode == 0:
            logger.info(f"SUCCESS: {desc}")
            return True, res.stdout.strip()
        else:
            logger.warning(f"WARNING: {desc} exited with {res.returncode}. Output: {res.stderr.strip() or res.stdout.strip()}")
            return False, res.stderr.strip()
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
        from backend.analysis_engine import generate_advanced_analytics_payload
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

            # updated_date & sync_status の置換
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

    # JSONメトリクス追記
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

    logger.info(f"CYCLE #{iteration:03d} COMPLETED in {cycle_duration:.1f}s. Next cycle in 30 minutes.")
    logger.info("=" * 70)

def main():
    logger.info("*" * 70)
    logger.info("AUTONOMOUS CONTINUOUS PIPELINE DAEMON INITIALIZED")
    logger.info(f"Target Time: Tomorrow 04:00:00 JST")
    logger.info(f"Logs: {DAEMON_LOG_FILE}")
    logger.info("*" * 70)

    # 終了目標時刻: 翌朝 04:00 JST
    now = datetime.now()
    target_end = (now + timedelta(days=1)).replace(hour=4, minute=0, second=0, microsecond=0)
    if now.hour < 4: # もし現在が深夜0時〜4時の間なら本日4時
        target_end = now.replace(hour=4, minute=0, second=0, microsecond=0)

    iteration = 1
    # サイクル間隔: 30分 (1800秒)
    INTERVAL_SECONDS = 1800

    while True:
        current_now = datetime.now()
        if current_now >= target_end:
            logger.info("*" * 70)
            logger.info(f"REACHED SCHEDULED TARGET TIME: {target_end.strftime('%Y-%m-%d %H:%M:%S')}. DAEMON FINISHED.")
            logger.info("*" * 70)
            break

        try:
            update_pipeline_cycle(iteration)
        except Exception as e:
            logger.error(f"Unhandled exception in cycle #{iteration}: {e}")

        iteration += 1
        logger.info(f"Sleeping for {INTERVAL_SECONDS} seconds until next cycle...")
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
