import asyncio
import io
import sys
import pandas as pd
import httpx
import re
from urllib.parse import urlparse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

df = pd.read_csv('マーケティングデータ100選リスト - Table 1.csv', encoding='utf-8')

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

results = []

async def check_url(idx, row, client):
    name = row['データ名']
    category = row['カテゴリ']
    url = row['URL']
    
    res_entry = {
        "index": idx + 1,
        "name": name,
        "category": category,
        "original_url": url,
        "status_code": None,
        "final_url": None,
        "is_ok": False,
        "content_type": "",
        "content_length": 0,
        "error": None
    }
    
    try:
        resp = await client.get(url, headers=headers, follow_redirects=True, timeout=15.0)
        res_entry["status_code"] = resp.status_code
        res_entry["final_url"] = str(resp.url)
        res_entry["content_type"] = resp.headers.get("content-type", "")
        res_entry["content_length"] = len(resp.content)
        if resp.status_code < 400:
            res_entry["is_ok"] = True
        else:
            res_entry["error"] = f"HTTP {resp.status_code}"
    except Exception as e:
        res_entry["error"] = str(e)
        
    return res_entry

async def main():
    async with httpx.AsyncClient(verify=False) as client:
        tasks = [check_url(idx, row, client) for idx, row in df.iterrows()]
        results = await asyncio.gather(*tasks)
        
    res_df = pd.DataFrame(results)
    res_df.to_csv("url_check_results_raw.csv", index=False, encoding="utf-8-sig")
    
    ok_count = res_df["is_ok"].sum()
    print(f"Total checked: {len(res_df)}")
    print(f"OK (status < 400): {ok_count}")
    print(f"Failed / Error: {len(res_df) - ok_count}")
    
    failed = res_df[~res_df["is_ok"]]
    print("\n--- Failed / Issues ---")
    for _, r in failed.iterrows():
        print(f"#{r['index']} [{r['name']}]: {r['original_url']} -> Status: {r['status_code']}, Error: {r['error']}")

if __name__ == "__main__":
    asyncio.run(main())
