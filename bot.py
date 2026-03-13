import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime

API_KEY = os.getenv("TWELVE_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

SYMBOL = "XAU/USD"
INTERVAL = "5min"
OUTPUT_SIZE = 120


def send_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": CHANNEL_ID,
        "text": text
    }
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print("Telegram error:", e)


def get_data():
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={INTERVAL}&outputsize={OUTPUT_SIZE}&apikey={API_KEY}"

    r = requests.get(url).json()

    if "values" not in r:
        print("API error:", r)
        return None

    df = pd.DataFrame(r["values"])

    df = df.iloc[::-1]

    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)

    return df


def calculate_indicators(df):

    df["ema9"] = df["close"].ewm(span=9).mean()
    df["ema15"] = df["close"].ewm(span=15).mean()

    return df


def trend_filter(df):

    ema_now = df["ema15"].iloc[-2]
    ema_old = df["ema15"].iloc[-7]

    slope = ema_now - ema_old

    ema_distance = abs(df["ema9"].iloc[-2] - df["ema15"].iloc[-2])

    trending = abs(slope) > 0.6 and ema_distance > 0.2

    return trending, slope


def candle_patterns(c):

    body = abs(c["close"] - c["open"])
    rng = c["high"] - c["low"]

    upper_wick = c["high"] - max(c["open"], c["close"])
    lower_wick = min(c["open"], c["close"]) - c["low"]

    bullish = c["close"] > c["open"]
    bearish = c["close"] < c["open"]

    pinbar_bull = lower_wick > body * 2
    pinbar_bear = upper_wick > body * 2

    full_body = body > rng * 0.6

    big_candle = rng > 1.5 * rng

    return {
        "bullish": bullish,
        "bearish": bearish,
        "pinbar_bull": pinbar_bull,
        "pinbar_bear": pinbar_bear,
        "full_body": full_body,
        "big": big_candle
    }


def check_signal(df):

    c = df.iloc[-2]

    patterns = candle_patterns(c)

    trending, slope = trend_filter(df)

    if not trending:
        print("Sideways market")
        return

    ema9 = c["ema9"]
    ema15 = c["ema15"]

    touch_ema_buy = c["low"] <= ema9 or c["low"] <= ema15
    touch_ema_sell = c["high"] >= ema9 or c["high"] >= ema15

    # BUY condition
    if slope > 0 and touch_ema_buy:

        if patterns["bullish"] and (patterns["pinbar_bull"] or patterns["full_body"]):

            entry = c["high"]
            sl = c["low"]

            msg = f"""
BUY XAUUSD

Entry: {entry}
SL: {sl}

Strategy: EMA 9-15 Pullback
"""

            send_msg(msg)

    # SELL condition
    if slope < 0 and touch_ema_sell:

        if patterns["bearish"] and (patterns["pinbar_bear"] or patterns["full_body"]):

            entry = c["low"]
            sl = c["high"]

            msg = f"""
SELL XAUUSD

Entry: {entry}
SL: {sl}

Strategy: EMA 9-15 Pullback
"""

            send_msg(msg)


def main():

    df = get_data()

    if df is None:
        return

    df = calculate_indicators(df)

    check_signal(df)


if __name__ == "__main__":
    main()
