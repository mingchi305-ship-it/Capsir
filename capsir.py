import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
from datetime import datetime, timedelta

st.set_page_config(layout="wide")
st.title("📊 股票策略看板（專業穩定版）")

# ===== 使用者設定 =====
stocks = [
    {"股票代碼": "0050", "入手價格": 68.7},
    {"股票代碼": "0052", "入手價格": 40.67},
    {"股票代碼": "006208", "入手價格": 109.08},
    {"股票代碼": "00888", "入手價格": 68.7},
]

df = pd.DataFrame(stocks)

# ===== 自動判斷 TW / TWO =====
def format_symbol(code):
    two_list = ["00888", "006208", "00733"]
    return f"{code}.TWO" if code in two_list else f"{code}.TW"


# ===== yfinance =====
def get_yfinance(symbol):
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period="3mo")

        if hist.empty:
            return None

        price = hist["Close"].iloc[-1]
        ma20 = hist["Close"].rolling(20).mean().iloc[-1]
        high52 = stock.info.get("fiftyTwoWeekHigh", None)

        return price, ma20, high52
    except:
        return None


# ===== FinMind fallback =====
def get_finmind(code):
    try:
        url = "https://api.finmindtrade.com/api/v4/data"
        params = {
            "dataset": "TaiwanStockPrice",
            "data_id": code,
            "start_date": (datetime.today() - timedelta(days=120)).strftime("%Y-%m-%d"),
        }

        res = requests.get(url, params=params, timeout=10).json()
        data = res.get("data", [])

        if not data:
            return None

        df = pd.DataFrame(data)
        df["close"] = df["close"].astype(float)

        price = df["close"].iloc[-1]
        ma20 = df["close"].rolling(20).mean().iloc[-1]
        high52 = df["close"].max()

        return price, ma20, high52
    except:
        return None


# ===== 快取層（最重要）=====
@st.cache_data(ttl=300)  # 5分鐘cache
def get_stock_data(code):
    symbol = format_symbol(code)

    # 1️⃣ yfinance
    data = get_yfinance(symbol)
    if data:
        return data

    # 2️⃣ fallback
    data = get_finmind(code)
    if data:
        return data

    return None, None, None


# ===== 批次抓資料（含節流）=====
prices, ma20_list, high52_list = [], [], []

for code in df["股票代碼"]:
    p, m, h = get_stock_data(code)

    prices.append(p)
    ma20_list.append(m)
    high52_list.append(h)

    time.sleep(0.5)  # 🔥 防鎖關鍵

df["現價"] = prices
df["MA20"] = ma20_list
df["52週高點"] = high52_list

# ===== 計算（你的策略）=====
df["支撐下限"] = df["現價"] * (1 - (1 - 0.618) * ((df["現價"] - df["入手價格"]) / df["現價"]))
df["最後防線"] = df["現價"] * (1 - 0.618 * ((df["現價"] - df["入手價格"]) / df["現價"]))
df["獲利上限"] = df["入手價格"] * 1.618

df["K線乖離率"] = (df["現價"] - df["MA20"]) / df["MA20"]
df["獲利績效"] = (df["現價"] - df["入手價格"]) / df["入手價格"]

# ===== 判斷邏輯 =====
def judge(row):
    if pd.isna(row["現價"]):
        return "⚠️ 無資料"

    if row["現價"] < row["支撐下限"]:
        return "🚨 結構破壞：減碼"
    elif row["K線乖離率"] > 0.1:
        return "⚠️ 過熱警戒"
    elif row["現價"] > row["MA20"]:
        return "🚀 強勢續抱"
    else:
        return "👀 觀察"

df["目前狀態判斷"] = df.apply(judge, axis=1)

# ===== 顯示 =====
st.dataframe(
    df.style.format({
        "現價": "{:.2f}",
        "MA20": "{:.2f}",
        "52週高點": "{:.2f}",
        "支撐下限": "{:.2f}",
        "最後防線": "{:.2f}",
        "獲利上限": "{:.2f}",
        "K線乖離率": "{:.2%}",
        "獲利績效": "{:.2%}",
    }),
    use_container_width=True
)
