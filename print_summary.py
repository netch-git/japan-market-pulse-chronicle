import pandas as pd

df = pd.read_csv('data_collection_summary.csv', encoding='utf-8')
print("Failed items:")
for _, r in df[~df['success']].iterrows():
    print(f"#{r['index']} {r['name']} ({r['url']}) -> Error: {r['error']}")

total_mb = df['bytes_downloaded'].sum() / (1024 * 1024)
print(f"\nTotal bytes downloaded: {df['bytes_downloaded'].sum():,} bytes ({total_mb:.2f} MB)")
print("Total successful files:", df['success'].sum())
