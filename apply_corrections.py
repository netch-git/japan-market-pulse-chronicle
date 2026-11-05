import pandas as pd

df = pd.read_csv('マーケティングデータ100選リスト - Table 1.csv', encoding='utf-8')

corrections = {
    "国民生活に関する世論調査": "https://survey.gov-online.go.jp/index.html",
    "PickUp Data & Contents": "https://ad.sankeiliving.co.jp/",
    "人気SNSのユーザー数まとめ": "https://www.comnico.jp/we-love-social/sns-users",
    "THE 日本大学ランキング": "https://www.timeshighereducation.com/world-university-rankings",
    "OECD生徒の学習到達度調査（PISA）": "https://www.nier.go.jp/05_kenkyu_seika/pisa/index.html",
    "経済レポート情報": "http://www3.keizaireport.com/",
    "訪日外国人統計": "https://www.jnto.go.jp/statistics/data/visitors-statistics/",
    "エデルマン・トラストバロメーター": "https://www.edelman.jp/insight/trust",
}

for name, new_url in corrections.items():
    mask = df['データ名'] == name
    if mask.any():
        df.loc[mask, 'URL'] = new_url
        print(f"Updated {name} -> {new_url}")

df.to_csv('マーケティングデータ100選リスト_修正版.csv', index=False, encoding='utf-8-sig')
print("Saved マーケティングデータ100選リスト_修正版.csv successfully.")
