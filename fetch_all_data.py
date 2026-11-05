import asyncio
import io
import os
import re
import sys
import json
import pandas as pd
import httpx
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "collected_opendata")
os.makedirs(DATA_DIR, exist_ok=True)

df = pd.read_csv('マーケティングデータ100選リスト_修正版.csv', encoding='utf-8')

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
}

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>| ]', '_', name)

async def fetch_item(client, semaphore, idx, row):
    name = row['データ名']
    category = row['カテゴリ']
    url = row['URL']
    provider = row['提供元']
    summary = row['概要・特徴']
    
    clean_name = sanitize_filename(f"{idx:03d}_{name}")
    save_path = os.path.join(DATA_DIR, f"{clean_name}.html")
    meta_path = os.path.join(DATA_DIR, f"{clean_name}_meta.json")
    
    record = {
        "index": idx,
        "name": name,
        "category": category,
        "provider": provider,
        "summary": summary,
        "url": url,
        "fetched_at": datetime.now().isoformat(),
        "status_code": None,
        "success": False,
        "bytes_downloaded": 0,
        "content_type": "",
        "saved_file": None,
        "error": None
    }
    
    async with semaphore:
        try:
            resp = await client.get(url, headers=headers, follow_redirects=True, timeout=20.0)
            record["status_code"] = resp.status_code
            record["content_type"] = resp.headers.get("content-type", "")
            
            if resp.status_code < 400:
                record["success"] = True
                content = resp.content
                record["bytes_downloaded"] = len(content)
                
                # Save file
                ext = ".html"
                ct = record["content_type"].lower()
                if "pdf" in ct or url.lower().endswith(".pdf"):
                    ext = ".pdf"
                elif "csv" in ct or url.lower().endswith(".csv"):
                    ext = ".csv"
                elif "json" in ct or url.lower().endswith(".json"):
                    ext = ".json"
                    
                actual_file_path = os.path.join(DATA_DIR, f"{clean_name}{ext}")
                with open(actual_file_path, "wb") as f:
                    f.write(content)
                record["saved_file"] = os.path.basename(actual_file_path)
            else:
                record["error"] = f"HTTP {resp.status_code}"
        except Exception as e:
            record["error"] = str(e)
            
    # Save meta json
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
        
    return record

async def main():
    semaphore = asyncio.Semaphore(10) # 10 concurrent requests
    records = []
    
    async with httpx.AsyncClient(verify=False) as client:
        tasks = [
            fetch_item(client, semaphore, idx + 1, row)
            for idx, row in df.iterrows()
        ]
        records = await asyncio.gather(*tasks)
        
    res_df = pd.DataFrame(records)
    res_df.to_csv("data_collection_summary.csv", index=False, encoding="utf-8-sig")
    
    success_count = res_df['success'].sum()
    print("=" * 60)
    print(f"Data Collection Completed!")
    print(f"Total: {len(res_df)}")
    print(f"Successfully downloaded: {success_count} / {len(res_df)}")
    print(f"Failed: {len(res_df) - success_count}")
    print("Summary saved to data_collection_summary.csv")
    print(f"Data directory: {DATA_DIR}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
