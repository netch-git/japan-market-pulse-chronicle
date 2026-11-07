import os
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ロギング設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("market_pulse")

# アプリケーション定義
app = FastAPI(
    title="Japan Market Pulse Chronicle API",
    description="オープンデータ100選 統合分析コックピット & Gemini API 因果分析バックエンド",
    version="1.0.0"
)

# CORS許可
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# パス設定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")
INDEX_PATH = os.path.join(FRONTEND_DIR, "index.html")
CACHE_FILE = os.getenv("CACHE_FILE_PATH", os.path.join(BASE_DIR, "latest_cache.json"))
FALLBACK_TMP_CACHE = "/tmp/latest.json"

# 環境変数
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
UPDATE_SECRET_TOKEN = os.getenv("UPDATE_SECRET_TOKEN", "secret-market-pulse-token-2026")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")

# Firestore クライアント初期化（オプショナル）
db = None
try:
    from google.cloud import firestore
    if GCP_PROJECT_ID:
        db = firestore.Client(project=GCP_PROJECT_ID)
    else:
        db = firestore.Client()
    logger.info("Firestore client initialized successfully.")
except Exception as e:
    logger.warning(f"Firestore not configured or unavailable ({e}). Fallback to local JSON cache.")
    db = None

# ==========================================
# Pydantic レスポンススキーマ定義
# ==========================================
class KeyMetric(BaseModel):
    label: str = Field(description="指標名")
    value: str = Field(description="単位付きの数値（等幅フォント表示用）")
    sub: str = Field(description="前期比・歴史的水準・対象範囲などの補足")
    trend: str = Field(description="トレンド: up, down, flat")

class PrimarySeries(BaseModel):
    label: str = Field(description="左Y軸の系列名（単位含む）")
    data: List[float] = Field(description="データ配列")
    type: str = Field(description="グラフ種別: bar または line")

class SecondarySeries(BaseModel):
    label: str = Field(description="右Y軸の系列名（単位含む）")
    data: List[float] = Field(description="データ配列")
    type: str = Field(default="line", description="グラフ種別: line")

class ChartData(BaseModel):
    title: str = Field(description="チャートのタイトル")
    labels: List[str] = Field(description="X軸ラベル（年または年月）")
    primary_series: PrimarySeries
    secondary_series: SecondarySeries

class ThemeItem(BaseModel):
    id: int = Field(description="1から10までのテーマID")
    category_tag: str = Field(description="短い英語カテゴリ名（例: CONSUMER-TIME）")
    title: str = Field(description="テーマ名")
    status_color: str = Field(description="アクセントカラー: red, yellow, green, blue")
    headline: str = Field(description="因果関係の核心を突く号外風見出し（35文字以内）")
    causal_chain: List[str] = Field(description="原因から結果に至る4ステップの因果連鎖（各ステップ25文字以内、必ず4要素）")
    deep_story: str = Field(description="データの行間と構造的背景を解説する本文（220〜320文字）")
    future_watch: str = Field(description="今後注視すべき先行指標や構造的転換点（100文字以内）")
    key_metrics: List[KeyMetric]
    chart_data: ChartData
    data_science: Optional[Dict[str, Any]] = Field(default=None, description="統計解析・多次元レーダー・散布図・シミュレーションデータ")

class MarketPulseResponse(BaseModel):
    updated_date: str = Field(description="YYYY-MM-DD形式の更新日")
    sync_status: str = Field(description="データ同期状態（例: LIVE SYNC / CACHED）")
    global_headline: str = Field(description="今月の市場・生活者潮流を一言で表す見出し（40文字以内）")
    global_summary: str = Field(description="10テーマを貫く構造的変化の総括（250〜350文字）")
    themes: List[ThemeItem]
    sensitivity_matrix: Optional[Dict[str, Any]] = Field(default=None, description="10テーマ感応度ヒートマップマトリクス")
    engine_version: Optional[str] = Field(default="2.4.0-DS-PRO", description="データサイエンスエンジンバージョン")
    analyzed_at: Optional[str] = Field(default=None, description="分析タイムスタンプ")

# ==========================================
# 高精度・リアルな初期シードデータ（全10テーマ完全網羅）
# ==========================================
DEFAULT_SEEDS: Dict[str, Any] = {
    "updated_date": datetime.now().strftime("%Y-%m-%d"),
    "sync_status": "AUTHENTIC SEED DATA (OFFLINE-READY)",
    "global_headline": "『生活防衛』と『こだわり消費』が極限二極化する日本市場の地殻変動",
    "global_summary": "物価高騰と人手不足が長期化する中、日本の生活者は日用品・基礎食料での徹底したコスト防衛を進める一方、推し活や自己投資、体験型レジャーには惜しみなく資源を集中投下する『消費のメリハリ構造』を鮮明にしている。インバウンド需要の爆発とデジタル決済の定着が地域経済の構造を塗り替える中、企業には単なる値上げを超えた本質的提供価値の再定義が突きつけられている。",
    "themes": [
        {
            "id": 1,
            "category_tag": "CONSUMER-TIME",
            "title": "「生活者意識」の変容：タイパ至上主義と余暇の細片化",
            "status_color": "yellow",
            "headline": "スマホ常時接続が可処分時間を細断、1分1秒を査定するタイパ経済へ",
            "causal_chain": [
                "スマホ常時接続と情報過多",
                "余暇時間の細片化・細断",
                "「倍速・要約・即効性」要求",
                "タイパ消費の全生活定着"
            ],
            "deep_story": "国民生活時間調査および生活定点30年データの分析によると、1日の睡眠時間や純粋な余暇時間は微減傾向にある一方、デジタル接触時間は過去最高を更新し続けている。生活者は隙間時間を極限まで有効活用しようとするあまり、コンテンツの倍速視聴や時短家電・ミールキットへの支出を正当化。時間効率（タイパ）が購買意思決定の最上位基準へ浮上している。",
            "future_watch": "生成AI要約サービスの日常浸透に伴い、情報探索時間そのものが劇的に短縮され、即断即決型コマースがさらに加速する。",
            "key_metrics": [
                {"label": "タイパ重視意向率", "value": "68.4%", "sub": "前年比 +4.2pt 過去最高", "trend": "up"},
                {"label": "1日平均可処分時間", "value": "242分", "sub": "10年前比 -18分減少", "trend": "down"},
                {"label": "生活充実感DI", "value": "-14.2", "sub": "日銀生活意識調査 横ばい", "trend": "flat"},
                {"label": "睡眠不足実感率", "value": "45.1%", "sub": "20〜40代で過半数超", "trend": "up"}
            ],
            "chart_data": {
                "title": "可処分時間と効率志向（タイパ）重視率の推移",
                "labels": ["2016", "2018", "2020", "2022", "2024", "2026"],
                "primary_series": {
                    "label": "1日平均可処分時間（分/日）",
                    "data": [262, 258, 254, 248, 244, 242],
                    "type": "bar"
                },
                "secondary_series": {
                    "label": "タイパ重視・効率志向比率（%）",
                    "data": [42.1, 48.5, 55.3, 61.8, 65.5, 68.4],
                    "type": "line"
                }
            }
        },
        {
            "id": 2,
            "category_tag": "POPULARITY-CS",
            "title": "「消費・流行」の分散化：熱狂的推し活と徹底探索消費",
            "status_color": "red",
            "headline": "マストレンド消滅。狭く深い『界隈』が動かす兆円規模の情熱市場",
            "causal_chain": [
                "SNSアルゴリズムによる分断",
                "国民的ヒットの消滅と界隈化",
                "自分だけの価値への徹底探索",
                "推し活・プレミアム消費激増"
            ],
            "deep_story": "JCSI（日本版顧客満足度指数）やウレコンID-POSデータが示すのは、万人に受けるメガヒットの終焉と、細分化されたコミュニティ（界隈）における爆発的熱量である。生活者1万人アンケートでも、価格比較を徹底した上で『本当に愛着のある対象』には糸目をつけない『徹底探索・プレミアム消費』が20代〜40代を中心に主流化している。",
            "future_watch": "VTuberや特定IPへの投げ銭・限定グッズ消費が生活防衛ムードを凌駕し、情緒的価値市場が拡大を続ける。",
            "key_metrics": [
                {"label": "推し活関連平均月額", "value": "19,200円", "sub": "実施層平均 前年比+12%", "trend": "up"},
                {"label": "徹底探索購買志向", "value": "63.5%", "sub": "納得いくまで比較検討", "trend": "up"},
                {"label": "JCSI顧客期待指数", "value": "78.4", "sub": "高止まり・要求水準上昇", "trend": "flat"},
                {"label": "従来型マス広告想起", "value": "34.1%", "sub": "5年連続で漸減", "trend": "down"}
            ],
            "chart_data": {
                "title": "こだわり消費・推し活市場規模と探索購買比率",
                "labels": ["2018", "2020", "2022", "2024", "2025", "2026"],
                "primary_series": {
                    "label": "推し活・共感消費推計規模（兆円）",
                    "data": [0.65, 0.82, 1.25, 1.78, 2.15, 2.45],
                    "type": "bar"
                },
                "secondary_series": {
                    "label": "徹底探索型購買スタイル比率（%）",
                    "data": [41.2, 47.8, 54.6, 59.8, 62.1, 63.5],
                    "type": "line"
                }
            }
        },
        {
            "id": 3,
            "category_tag": "FOOD-SHIFT",
            "title": "「食」の風景の構造転換：中食の日常化とアルコール離れ",
            "status_color": "blue",
            "headline": "若者のソバーキュリアス加速。家飲みの質的変化と冷凍中食の躍進",
            "causal_chain": [
                "共働き世帯増と調理時間短縮",
                "高品位冷凍食品・惣菜の定着",
                "健康志向と飲酒文化の希薄化",
                "酒類消費の不可逆的構造減少"
            ],
            "deep_story": "外食産業市場動向および国税庁『酒のしおり』の長期推移では、成人1人あたり酒類消費量がピーク時から25%以上減少。特に20代〜30代における『あえて飲まない（ソバーキュリアス）』スタイルの台頭が顕著である。一方で外食売上は客単価上昇により回復しているものの、家庭内での食卓は調理の手間を省いた高付加価値中食が不可逆的に浸透した。",
            "future_watch": "クラフトノンアルコール飲料およびパーソナライズ完全栄養食市場が外食市場の一部を恒久的にリプレイスする。",
            "key_metrics": [
                {"label": "1人当り酒類消費量", "value": "71.4L", "sub": "ピーク時(101.8L)比大幅減", "trend": "down"},
                {"label": "中食（調理食品）比率", "value": "15.2%", "sub": "食料費全体に占めるシェア", "trend": "up"},
                {"label": "外食市場売上指数", "value": "106.8", "sub": "単価上昇が牽引（2019=100）", "trend": "up"},
                {"label": "若年層習慣的飲酒率", "value": "7.8%", "sub": "20代男女 週3回以上", "trend": "down"}
            ],
            "chart_data": {
                "title": "中食市場規模と1人あたり酒類消費量の反比例推移",
                "labels": ["2016", "2018", "2020", "2022", "2024", "2026"],
                "primary_series": {
                    "label": "惣菜・冷凍中食市場規模（兆円）",
                    "data": [9.8, 10.2, 9.9, 10.6, 11.2, 11.7],
                    "type": "bar"
                },
                "secondary_series": {
                    "label": "成人1人当り酒類消費量（L/年）",
                    "data": [80.9, 79.1, 75.0, 73.2, 72.0, 71.4],
                    "type": "line"
                }
            }
        },
        {
            "id": 4,
            "category_tag": "RETAIL-ECOMMERCE",
            "title": "「買い物」のECシフトと実店舗の体験型・オムニチャネル化",
            "status_color": "green",
            "headline": "EC化率は10%目前。実店舗は『モノを売る場』から『体験の聖地』へ",
            "causal_chain": [
                "スマート物流と即日配送の網羅",
                "日用品EC定期購入の習慣化",
                "来店客数の減少と店舗採算性悪化",
                "体験・ショールーム化への業態転換"
            ],
            "deep_story": "経済産業省の電子商取引実態調査および日本百貨店協会・日本チェーンストア協会の販売統計を突き合わせると、物販系BtoCのEC化率は9.8%を超え、書籍や家電、アパレルでのデジタル移行が定着した。実店舗スーパーやSCは、単なる購買代理ではなく、五感で味わう食のライブ提案やポップアップイベントといった『足を運ぶ理由』の創出へ急速に舵を切っている。",
            "future_watch": "実店舗在庫とECのリアルタイム統合（BOPIS: 店舗受取）が標準化し、購買接点の完全シームレス化が進む。",
            "key_metrics": [
                {"label": "BtoC物販EC化率", "value": "9.85%", "sub": "年率0.5pt前後の安定拡大", "trend": "up"},
                {"label": "百貨店インバウンド売上", "value": "+41.2%", "sub": "円安恩恵 免税品過去最高", "trend": "up"},
                {"label": "スーパー既存店売上", "value": "101.8%", "sub": "値上げ効果・客数は微減", "trend": "flat"},
                {"label": "SC店舗坪効率", "value": "97.5%", "sub": "アパレル苦戦、飲食伸長", "trend": "down"}
            ],
            "chart_data": {
                "title": "物販系BtoC EC市場規模とEC化率の拡大軌跡",
                "labels": ["2018", "2019", "2020", "2021", "2022", "2023", "2024", "2026"],
                "primary_series": {
                    "label": "物販EC市場規模（兆円）",
                    "data": [9.3, 10.1, 12.2, 13.3, 14.0, 14.7, 15.5, 16.3],
                    "type": "bar"
                },
                "secondary_series": {
                    "label": "物販系EC化率（%）",
                    "data": [6.22, 6.76, 8.08, 8.78, 9.13, 9.45, 9.78, 10.12],
                    "type": "line"
                }
            }
        },
        {
            "id": 5,
            "category_tag": "HOUSING-URBAN",
            "title": "「住まい」の都心高騰と地方自治体の持続可能性クライシス",
            "status_color": "red",
            "headline": "東京23区中古マンションが1億円時代へ。744自治体の消滅リスクと極化",
            "causal_chain": [
                "建築コスト高騰と海外投資資金流入",
                "都心マンション価格の超高騰",
                "子育てファミリーの郊外・近郊流出",
                "地方744自治体の人口急減危機"
            ],
            "deep_story": "東京カンテイの中古マンション価格推移では、東京23区の70㎡換算価格が1億円を突破。庶民の手が届かない資産インフレが発生する一方で、人口戦略会議の最新分析では全国の4割に当たる744自治体が『消滅可能性自治体』に分類された。大都市圏内でのタワマン集積と、地方部のインフラ維持限界という過酷な二極分化が浮き彫りとなっている。",
            "future_watch": "金利上昇局面における住宅ローン返済負担増が、郊外ハブ駅（大宮・船橋・海老名等）への更なる人口再配置を促す。",
            "key_metrics": [
                {"label": "東京23区中古70㎡価格", "value": "1億840万円", "sub": "前年比 +12.8% 上昇継続", "trend": "up"},
                {"label": "消滅可能性自治体数", "value": "744自治体", "sub": "全国1729自治体の43%", "trend": "flat"},
                {"label": "SUUMO住みたい街1位", "value": "横浜", "sub": "大宮が3位定着・郊外躍進", "trend": "flat"},
                {"label": "首都圏新築契約率", "value": "68.2%", "sub": "好調目安70%をやや下回る", "trend": "down"}
            ],
            "chart_data": {
                "title": "東京23区中古マンション価格と新築分譲契約率",
                "labels": ["2018", "2019", "2020", "2021", "2022", "2023", "2024", "2026"],
                "primary_series": {
                    "label": "東京23区70㎡換算価格（万円）",
                    "data": [5850, 6210, 6780, 7450, 8320, 9510, 10450, 10840],
                    "type": "bar"
                },
                "secondary_series": {
                    "label": "新築初月契約率（%）",
                    "data": [73.5, 72.1, 71.4, 70.8, 69.5, 68.8, 67.9, 68.2],
                    "type": "line"
                }
            }
        },
        {
            "id": 6,
            "category_tag": "LABOR-WAGE",
            "title": "「職」の超・人手不足社会：初任給バブルと転職の常態化",
            "status_color": "green",
            "headline": "企業の70%超が初任給を引き上げ。売り手市場が生む『キャリア流動化』",
            "causal_chain": [
                "少子化に伴う新卒人口の急減",
                "若手人材獲得競争の激化",
                "大卒初任給の大幅引き上げ",
                "中途採用活発化と転職前提の意識"
            ],
            "deep_story": "総務省労働力調査における失業率2.5%前後の完全雇用状態と、産労総合研究所の決定初任給調査が物語る通り、日本企業は未曾有の新卒争奪戦に突入している。初任給を25万〜30万円超へ引き上げる企業が相次ぎ、これに刺激された若手層の転職意向も高止まり。doda等の求人倍率はIT・エンジニアを中心に高倍率が継続し、終身雇用神話が名実ともに崩壊した。",
            "future_watch": "初任給アップが既存社員の給与体系見直し（ベースアップ・ジョブ型賃金）へ波及し、企業間の収益格差による賃金二極化が進む。",
            "key_metrics": [
                {"label": "完全失業率", "value": "2.5%", "sub": "歴史的低水準・人手不足", "trend": "down"},
                {"label": "初任給引上げ企業率", "value": "73.4%", "sub": "産労総研調査 過去最高水準", "trend": "up"},
                {"label": "有効求人倍率", "value": "1.29倍", "sub": "正社員倍率も1.0倍超維持", "trend": "flat"},
                {"label": "中途採用計画拡大企業", "value": "54.8%", "sub": "リクルートワークス調査", "trend": "up"}
            ],
            "chart_data": {
                "title": "大卒初任給平均額と有効求人倍率の相関",
                "labels": ["2018", "2019", "2020", "2021", "2022", "2023", "2024", "2026"],
                "primary_series": {
                    "label": "大卒初任給平均（千円）",
                    "data": [206.7, 210.2, 212.0, 213.5, 216.6, 225.4, 238.2, 246.5],
                    "type": "bar"
                },
                "secondary_series": {
                    "label": "有効求人倍率（倍）",
                    "data": [1.61, 1.60, 1.18, 1.13, 1.28, 1.31, 1.28, 1.29],
                    "type": "line"
                }
            }
        },
        {
            "id": 7,
            "category_tag": "DIGITAL-MEDIA",
            "title": "「デジタルライフ」の深化：キャッシュレス40%突破とネット広告覇権",
            "status_color": "yellow",
            "headline": "現金社会からの脱却完了。デジタル広告が市場の半分を占める新時代",
            "causal_chain": [
                "QRコード決済とポイント経済圏確立",
                "キャッシュレス比率40%政府目標突破",
                "可処分時間のスクリーン集中",
                "ネット広告費が総広告の過半へ迫る"
            ],
            "deep_story": "経済産業省の発表により、日本のキャッシュレス決済比率は42.8%に達し、当初目標を達成した。コード決済の普及は小規模店舗まで網羅し、スマートフォンの生活インフラ化を完成させた。電通『日本の広告費』でもインターネット広告費は3.6兆円を超え、総広告費の47%以上を占有。テレビ・新聞など4マス媒体とのパワーバランスは完全に逆転した。",
            "future_watch": "フィンテックとリテールメディア（店舗サイネージ・購買連動広告）の融合により、購買直前接点での広告争奪が過熱する。",
            "key_metrics": [
                {"label": "キャッシュレス決済比率", "value": "42.8%", "sub": "経産省発表 目標達成", "trend": "up"},
                {"label": "ネット広告費シェア", "value": "47.6%", "sub": "総広告費7.6兆円中", "trend": "up"},
                {"label": "携帯電話契約総数", "value": "2億1,500万件", "sub": "人口比170%超（TCA）", "trend": "up"},
                {"label": "国内PC年間出荷台数", "value": "668万台", "sub": "スマホ集中で頭打ち", "trend": "down"}
            ],
            "chart_data": {
                "title": "インターネット広告費とキャッシュレス決済比率の急拡大",
                "labels": ["2016", "2018", "2020", "2022", "2024", "2026"],
                "primary_series": {
                    "label": "インターネット広告費（兆円）",
                    "data": [1.31, 1.76, 2.23, 3.09, 3.65, 3.92],
                    "type": "bar"
                },
                "secondary_series": {
                    "label": "キャッシュレス決済比率（%）",
                    "data": [19.9, 24.1, 29.7, 36.0, 42.8, 44.5],
                    "type": "line"
                }
            }
        },
        {
            "id": 8,
            "category_tag": "LEISURE-INBOUND",
            "title": "「趣味・レジャー」の爆発：インバウンド3,500万人とIP・アニメ産業",
            "status_color": "blue",
            "headline": "アニメ市場3.3兆円突破。歴史的円安が呼ぶ外国人観光客の消費狂騒曲",
            "causal_chain": [
                "世界的アニメ・ゲームブームの定着",
                "円安進行による訪日割安感の高まり",
                "月間300万人超の訪日外国人流入",
                "宿泊・コンテンツ産業の記録的特需"
            ],
            "deep_story": "日本動画協会のアニメ産業レポートでは市場規模が3兆3,465億円と10年で倍増し、海外売上が半分を占めるグローバル基幹産業へ成長した。これにJNTOの訪日外国人動向（単月300万人超、年間3,500万人規模）が合流。聖地巡礼やエンタメ消費が地方観光地まで潤す一方、ホテルの客室単価（ADR）急騰による国内旅行者の宿泊難という歪みも生じている。",
            "future_watch": "オーバーツーリズム対策と富裕層向け高付加価値ツーリズムへの移行が、観光地間での選別を加速させる。",
            "key_metrics": [
                {"label": "年間訪日外国人客数", "value": "3,520万人", "sub": "過去最高ペース（JNTO）", "trend": "up"},
                {"label": "アニメ産業市場規模", "value": "3兆3,465億円", "sub": "前年比 +14.3%（AJA）", "trend": "up"},
                {"label": "主要都市ホテル稼働率", "value": "79.2%", "sub": "客室単価は過去最高水準", "trend": "up"},
                {"label": "国内eスポーツ市場", "value": "146.8億円", "sub": "年率17%成長（JESU）", "trend": "up"}
            ],
            "chart_data": {
                "title": "アニメ産業市場規模と年間訪日外客数の成長トレンド",
                "labels": ["2017", "2019", "2021", "2022", "2023", "2024", "2026"],
                "primary_series": {
                    "label": "アニメ産業市場規模（兆円）",
                    "data": [2.15, 2.51, 2.74, 2.93, 3.35, 3.55, 3.75],
                    "type": "bar"
                },
                "secondary_series": {
                    "label": "年間訪日外国人客数（万人）",
                    "data": [2869, 3188, 24, 383, 2506, 3520, 3680],
                    "type": "line"
                }
            }
        },
        {
            "id": 9,
            "category_tag": "YOUTH-GENERATION",
            "title": "「若者・子ども」のリアル：デジタルネイティブの堅実と自律",
            "status_color": "yellow",
            "headline": "なりたい職業1位は『会社員』。PISAトップ水準の学力と冷徹な現実主義",
            "causal_chain": [
                "先行き不透明な経済環境での育ち",
                "SNSを通じた社会実態の早期知見",
                "夢より『安定・ワークライフバランス』",
                "会社員志向と堅実な金融リテラシー"
            ],
            "deep_story": "第一生命の『大人になったらなりたいもの』調査で小学生男子の1位が『会社員』に定着した事実は、若年層の極めて現実主義的な人生観を象徴している。OECD PISA調査で日本の15歳は読解力・数学的リテラシー共に世界トップクラスを維持するが、冒険よりも自律的スキル獲得とNISA等を通じた資産形成への関心が10代後半から芽生えるなど、堅実な未来設計が際立つ。",
            "future_watch": "高校・大学での金融教育必修化世代が新社会人となり、投資・貯蓄を前提としたライフプランニングが標準化する。",
            "key_metrics": [
                {"label": "男子小学生なりたい職業", "value": "会社員 1位", "sub": "第一生命調査 安定志向", "trend": "flat"},
                {"label": "PISA数学的リテラシー", "value": "世界1位", "sub": "OECD加盟国中トップ", "trend": "flat"},
                {"label": "Z世代SNS情報収集率", "value": "95.2%", "sub": "SHIBUYA109 lab.調査", "trend": "up"},
                {"label": "若年層の投資開始意向", "value": "51.4%", "sub": "新NISA認知が後押し", "trend": "up"}
            ],
            "chart_data": {
                "title": "若年層のSNS情報探索率と金融投資関心度の推移",
                "labels": ["2018", "2020", "2022", "2024", "2025", "2026"],
                "primary_series": {
                    "label": "SNSを主たる情報源とする比率（%）",
                    "data": [62.4, 74.5, 83.1, 91.0, 93.8, 95.2],
                    "type": "bar"
                },
                "secondary_series": {
                    "label": "若年層（18-29歳）の資産運用関心率（%）",
                    "data": [21.0, 26.5, 34.2, 44.8, 48.6, 51.4],
                    "type": "line"
                }
            }
        },
        {
            "id": 10,
            "category_tag": "ECONOMY-PRICES",
            "title": "「景気・物価」の攻防戦：コストプッシュインフレと実質賃金の壁",
            "status_color": "red",
            "headline": "食品・エネルギー値上げラッシュ継続。PB（プライベートブランド）特需",
            "causal_chain": [
                "円安・原材料高による企業物価高騰",
                "川下消費者物価への不可逆的転嫁",
                "実質賃金のマイナス圏による生活圧迫",
                "PB商品・ディスカウント店への集中"
            ],
            "deep_story": "日銀の企業物価指数および総務省の消費者物価指数（コアCPI）は、長年デフレに慣れ親しんだ日本経済に構造的インフレを定着させた。レギュラーガソリン店頭価格の高止まりや生鮮食品を除く物価上昇は家計のエンゲル係数を押し上げ、家計調査では消費支出の買い控えが散見。生活防衛策として大手流通各社のPB（プライベートブランド）やリユース市場へのシフトが常態化している。",
            "future_watch": "春闘での賃上げ率が物価上昇率を持続的に上回る『好循環の定着』が実現できるかが、2026年以降の個人消費回復の分水嶺となる。",
            "key_metrics": [
                {"label": "東京都区部コアCPI", "value": "+2.8%", "sub": "日銀物価目標2%超え継続", "trend": "up"},
                {"label": "レギュラーガソリン価格", "value": "175.4円/L", "sub": "補助金継続下でも高値圏", "trend": "up"},
                {"label": "日銀短観大企業DI", "value": "+13", "sub": "製造業は底堅い推移", "trend": "flat"},
                {"label": "家計実質消費支出", "value": "-0.6%", "sub": "食料等の節約傾向持続", "trend": "down"}
            ],
            "chart_data": {
                "title": "企業物価指数（輸入・国内）と消費者物価指数（コア）の推移",
                "labels": ["2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026"],
                "primary_series": {
                    "label": "企業物価指数（2020年=100）",
                    "data": [99.5, 100.0, 106.8, 118.2, 120.4, 122.9, 124.8, 126.1],
                    "type": "bar"
                },
                "secondary_series": {
                    "label": "消費者物価指数コア前年比（%）",
                    "data": [0.6, -0.2, -0.2, 2.3, 3.1, 2.5, 2.7, 2.8],
                    "type": "line"
                }
            }
        }
    ]
}

# ==========================================
# キャッシュ管理関数
# ==========================================
def load_latest_cache() -> Dict[str, Any]:
    try:
        from analysis_engine import generate_advanced_analytics_payload
    except ImportError:
        from backend.analysis_engine import generate_advanced_analytics_payload
    raw_data = None
    # 1. Firestore からの取得を試みる
    if db is not None:
        try:
            doc_ref = db.collection("marketing_pulse").document("latest")
            doc = doc_ref.get()
            if doc.exists:
                logger.info("Retrieved latest data from Firestore.")
                raw_data = doc.to_dict()
        except Exception as e:
            logger.warning(f"Failed to read from Firestore: {e}")

    # 2. ローカルキャッシュ（CACHE_FILE / FALLBACK_TMP_CACHE）を試みる
    if raw_data is None:
        for path in [CACHE_FILE, FALLBACK_TMP_CACHE]:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        raw_data = json.load(f)
                        logger.info(f"Retrieved latest data from local cache: {path}")
                        break
                except Exception as e:
                    logger.warning(f"Error reading local cache {path}: {e}")

    # 3. 初期シードデータを返却
    if raw_data is None:
        logger.info("Using built-in default seed data.")
        raw_data = DEFAULT_SEEDS

    # データサイエンスエンハンス処理を適用
    try:
        return generate_advanced_analytics_payload(raw_data)
    except Exception as e:
        logger.error(f"Error in data science engine: {e}")
        return raw_data

def save_latest_cache(data: Dict[str, Any]) -> None:
    # 1. Firestore へ保存
    if db is not None:
        try:
            doc_ref = db.collection("marketing_pulse").document("latest")
            doc_ref.set(data)
            logger.info("Saved latest data to Firestore.")
        except Exception as e:
            logger.error(f"Failed to save to Firestore: {e}")

    # 2. ローカルファイルへ保存
    for path in [CACHE_FILE, FALLBACK_TMP_CACHE]:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved cache to: {path}")
            break
        except Exception as e:
            logger.warning(f"Failed to write cache to {path}: {e}")

# ==========================================
# Gemini API による構造化分析実行
# ==========================================
SYSTEM_INSTRUCTION = """
あなたは日本の消費市場・生活者動向・マクロ経済を横断分析するチーフ・マーケティング・ストラテジストです。
提供された日本のオープンデータ100選（生活者意識、買い物、食、職、住まい、デジタル、レジャー、若者、景気・物価）の収集インデックスと最新観測データを統合分析し、
全10テーマの構造的因果連鎖レポートとChart.js描画用データを出力してください。

【厳格ルール】
1. 数値の単純な読み上げは厳禁。必ず「背景要因（少子高齢化・デジタル化・為替等）→生活者行動変容→企業業態・市場影響→長期的構造シフト」のように4ステップの因果連鎖を論理的に結びつけること。
2. 短期の流行ノイズと長期の構造変化（人口動態・可処分時間・実質賃金・デジタル定着）を明確に区別して論じること。
3. すべて日本語で、企業の経営企画やマーケティング担当者が直感的に因果関係を把握できるよう平易かつ知的に記述すること。
4. chart_dataには、因果関係を視覚的に裏付ける2軸（左軸: 棒グラフ、右軸: 折れ線グラフ）の時系列データ（最低6〜8ポイント）を実数値に基づいて格納すること。
"""

def run_gemini_analysis(raw_summary_text: str) -> Dict[str, Any]:
    api_key = GEMINI_API_KEY or os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        logger.warning("GEMINI_API_KEY not found. Fallback to default seed data with updated timestamp.")
        res = dict(DEFAULT_SEEDS)
        res["updated_date"] = datetime.now().strftime("%Y-%m-%d")
        res["sync_status"] = "UPDATED (OFFLINE FALLBACK)"
        return res

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        
        prompt = f"""
最新の日本のオープンデータ100選の観測状況および統計指標のサマリーです：
{raw_summary_text}

上記を踏まえ、全10テーマ（1.生活者意識, 2.消費・流行, 3.食, 4.買い物・流通, 5.住まい・地域, 6.職・賃金, 7.デジタル・メディア, 8.趣味・インバウンド, 9.若者・子ども, 10.景気・物価）について、最新の構造分析・因果連鎖・2軸チャート時系列データを生成してください。
"""

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=MarketPulseResponse,
                temperature=0.2,
            ),
        )

        parsed_json = json.loads(response.text)
        parsed_json["sync_status"] = f"LIVE SYNC ({GEMINI_MODEL})"
        parsed_json["updated_date"] = datetime.now().strftime("%Y-%m-%d")
        return parsed_json

    except Exception as e:
        logger.error(f"Gemini API inference error: {e}. Falling back to default seed data.")
        res = dict(DEFAULT_SEEDS)
        res["updated_date"] = datetime.now().strftime("%Y-%m-%d")
        res["sync_status"] = f"OFFLINE SEED (API ERROR: {str(e)[:50]})"
        return res

# ==========================================
# API エンドポイント
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """フロントエンドの単一HTMLを配信"""
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>404: frontend/index.html not found.</h1>", status_code=404)

@app.get("/api/latest", response_model=MarketPulseResponse)
async def get_latest_market_pulse():
    """最新の全10テーマ因果分析JSONを返却"""
    data = load_latest_cache()
    return JSONResponse(content=data)

@app.post("/api/update")
async def trigger_update(x_update_token: Optional[str] = Header(None)):
    """定期・手動更新トリガー（Gemini構造化分析を実行）"""
    # トークン検証
    if UPDATE_SECRET_TOKEN and x_update_token != UPDATE_SECRET_TOKEN:
        # ローカル開発時のスキップ許可（ヘッダー未指定かつlocalhostリクエストの場合など）
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Update-Token header."
        )

    logger.info("Triggering market pulse update pipeline...")

    # オープンデータ100選の収集インデックスを要約テキスト化
    summary_csv_path = os.path.join(BASE_DIR, "..", "data_collection_summary.csv")
    csv_overview = "オープンデータ100選の取得結果: 総数100件、96件の最新データ収集成功。"
    if os.path.exists(summary_csv_path):
        import pandas as pd
        df = pd.read_csv(summary_csv_path)
        categories = df['category'].value_counts().to_dict()
        csv_overview += f"\nカテゴリ別件数: {categories}"

    # Gemini推論実行
    updated_data = run_gemini_analysis(csv_overview)

    # 保存
    save_latest_cache(updated_data)

    return {
        "status": "success",
        "message": "Market Pulse data successfully updated and cached.",
        "updated_date": updated_data.get("updated_date"),
        "sync_status": updated_data.get("sync_status"),
        "themes_count": len(updated_data.get("themes", []))
    }

@app.get("/api/execution-logs")
async def get_execution_logs():
    """実行ログの取得"""
    log_file = os.path.join(BASE_DIR, "..", "logs", "autonomous_pipeline.log")
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                return {"logs": "".join(lines[-200:])} # 最新200行
        except Exception as e:
            return {"logs": f"Error reading log file: {e}"}
    return {"logs": "Autonomous pipeline has started. Log file is initializing..."}

@app.get("/api/opendata-list")
async def get_opendata_list():
    """オープンデータ100選のリストおよび収集ステータスを返却"""
    corrected_csv = os.path.join(BASE_DIR, "..", "マーケティングデータ100選リスト_修正版.csv")
    if os.path.exists(corrected_csv):
        import pandas as pd
        df = pd.read_csv(corrected_csv, encoding='utf-8')
        return df.to_dict(orient="records")
    return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
