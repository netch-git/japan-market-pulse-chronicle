import requests
import urllib3
urllib3.disable_warnings()

candidates = [
    (2, "エデルマン・トラストバロメーター", "https://www.edelman.jp/insight/trust"),
    (5, "ソニー生命 調査レポート", "https://www.sonylife.co.jp/company/news/report/"),
    (13, "PickUp Data & Contents", "https://ad.sankeiliving.co.jp/"),
    (16, "国民生活に関する世論調査", "https://survey.gov-online.go.jp/index.html"),
    (50, "doda転職求人倍率レポート", "https://doda.jp/guide/kyujin_bairitsu/"),
    (58, "人気SNSのユーザー数まとめ", "https://www.comnico.jp/wls/sns-user-number"),
    (66, "訪日外国人統計", "https://www.jnto.go.jp/statistics/data/visitors-statistics/"),
    (72, "OECD生徒の学習到達度調査（PISA）", "https://www.nier.go.jp/05_kenkyu_seika/pisa/index.html"),
    (78, "THE 日本大学ランキング", "https://www.timeshighereducation.com/world-university-rankings"),
    (94, "経済レポート情報", "http://www3.keizaireport.com/"),
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

for idx, name, url in candidates:
    try:
        r = requests.get(url, headers=headers, timeout=15, verify=False, allow_redirects=True)
        print(f"#{idx} {name}: SUCCESS ({r.status_code}) -> {r.url}")
    except Exception as e:
        print(f"#{idx} {name}: FAILED -> {e}")
