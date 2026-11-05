import requests
import urllib3
urllib3.disable_warnings()

test_items = [
    (2, "エデルマン・トラストバロメーター", "https://www.edelman.com/jp/research/"),
    (5, "ソニー生命 調査レポート", "https://www.sonylife.co.jp/company/news/report.html"),
    (13, "PickUp Data & Contents", "https://www.kurashihow.co.jp/"),
    (16, "国民生活に関する世論調査", "https://survey.gov-online.go.jp/search/research_search/_?category=312&filter=survey"),
    (50, "doda転職求人倍率レポート", "https://doda.jp/guide/kyujin_bairitsu/"),
    (58, "人気SNSのユーザー数まとめ", "https://www.comnico.co.jp/we-love-social/sns-users"),
    (66, "訪日外国人統計", "https://statistics.jnto.go.jp/"),
    (72, "OECD生徒の学習到達度調査（PISA）", "https://www.nier.go.jp/kokusai/pisa/"),
    (78, "THE 日本大学ランキング", "https://japanuniversityrankings.jp/rankings/"),
    (94, "経済レポート情報", "https://www3.keizaireport.com"),
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
}

for idx, name, url in test_items:
    try:
        r = requests.get(url, headers=headers, timeout=10, verify=False)
        print(f"#{idx} {name}: Status {r.status_code}, Final URL: {r.url}")
    except Exception as e:
        print(f"#{idx} {name}: FAILED with {type(e).__name__}: {e}")
