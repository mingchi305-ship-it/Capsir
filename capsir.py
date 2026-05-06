import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(layout="wide")
st.title("📊 LOVE Cap sir策略看板（即時版）")

# ===== 使用者輸入 =====
stocks = [
    {"股票代碼": "00888", "yahoo代碼": "00888.TW", "入手價格": 68.7},
    {"股票代碼": "0052", "yahoo代碼": "0052.TW", "入手價格": 40.67},
    {"股票代碼": "006208", "yahoo代碼": "006208.TW", "入手價格": 109.08},
]

df = pd.DataFrame(stocks)

# ===== 抓即時資料 =====
@st.cache_data(ttl=300)  # 5分鐘更新
def get_data(symbol):
    stock = yf.Ticker(symbol)
    hist = stock.history(period="3mo")

    if hist.empty:
        return None

    current_price = hist["Close"].iloc[-1]
    ma20 = hist["Close"].rolling(20).mean().iloc[-1]
    high52 = stock.info.get("fiftyTwoWeekHigh", None)

    return current_price, ma20, high52

prices = []
ma20_list = []
high52_list = []

for s in df["yahoo代碼"]:
    data = get_data(s)
    if data:
        p, m, h = data
    else:
        p, m, h = None, None, None

    prices.append(p)
    ma20_list.append(m)
    high52_list.append(h)

df["現價"] = prices
df["MA20"] = ma20_list
df["52週高點"] = high52_list

# ===== 計算欄位（照你Excel）=====
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
        return "🚨 結構破壞：考慮減碼出場"
    elif row["K線乖離率"] > 0.1:
        return "⚠️ 過熱警戒：分批停利"
    elif row["現價"] > row["MA20"]:
        return "🚀 強勢主升：穩健續抱"
    else:
        return "👀 持續觀察"

df["目前狀態判斷"] = df.apply(judge, axis=1)

# ===== 格式優化 =====
st.dataframe(
    df.style.format({
        "現價": "{:.2f}",
        "MA20": "{:.2f}",
        "52週高點": "{:.2f}",
        "K線乖離率": "{:.2%}",
        "獲利績效": "{:.2%}",
        "支撐下限": "{:.2f}",
        "最後防線": "{:.2f}",
        "獲利上限": "{:.2f}"
    }),
    use_container_width=True
)
