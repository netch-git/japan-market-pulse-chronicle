import sys
import io
import pandas as pd
import httpx
import asyncio

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

df = pd.read_csv('マーケティングデータ100選リスト - Table 1.csv', encoding='utf-8')
print("Total rows:", len(df))
print("Columns:", df.columns.tolist())
print("\nCategories breakdown:")
print(df['カテゴリ'].value_counts())
print("\nFirst 10 items:")
for i, r in df.head(10).iterrows():
    print(f"{i+1:3d}. [{r['カテゴリ']}] {r['データ名']} ({r['提供元']}) -> {r['URL']}")
