import os
import numpy as np
import pandas as pd
import requests
import yaml
import yfinance as yf


# ==============================================================================
# 1. LOAD CONFIGURATION (daily.yml)
# ==============================================================================
def load_config(config_path="daily.yml"):
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"કન્ફિગરેશન ફાઈલ '{config_path}' મળી નથી. કૃપા કરીને ચકાસો."
        )
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ==============================================================================
# 2. TELEGRAM ALERT FUNCTION (VIA GITHUB SECRETS)
# ==============================================================================
def send_telegram_alert(bot_token, chat_id, message):
    if not bot_token or not chat_id:
        print("⚠️ ટેલિગ્રામ બોટ ટોકન અથવા ચેટ આઈડી મળેલ નથી.")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
    }

    try:
        response = requests.post(url, json=payload, timeout=12)
        res_data = response.json()
        if res_data.get("ok"):
            print("✅ ટેલિગ્રામ અલર્ટ સફળતાપૂર્વક મોકલાઈ ગઈ.")
            return True
        else:
            print(f"❌ ટેલિગ્રામ API એરર: {res_data.get('description')}")
            return False
    except Exception as e:
        print(f"❌ ટેલિગ્રામ કનેક્શન એરર: {e}")
        return False


# ==============================================================================
# 3. TECHNICAL INDICATORS (DAILY CALCULATIONS)
# ==============================================================================
def calculate_ema(series, span):
    return series.ewm(span=span, adjust=False).mean()


def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_intrinsic_value(stock):
    try:
        info = stock.info
        eps = info.get("trailingEps", None)
        bvps = info.get("bookValue", None)
        if eps and bvps and eps > 0 and bvps > 0:
            iv = np.sqrt(22.5 * eps * bvps)
            return round(iv, 2)
        return "N/A"
    except Exception:
        return "N/A"


# ==============================================================================
# 4. ADVANCED TECHNICAL & FUNDAMENTAL ANALYSIS (DAILY CHART)
# ==============================================================================
def analyze_stock_daily(ticker_symbol, config):
    try:
        stock = yf.Ticker(ticker_symbol)

        period = config["data_settings"].get("period", "max")
        interval = "1d"  # Daily Interval

        df = stock.history(period=period, interval=interval)

        if df.empty or len(df) < 150:
            return None

        fc = config.get("fundamental_criteria", {})
        tc = config.get("technical_criteria", {})

        # Daily Technical Indicators
        df["EMA_20"] = calculate_ema(df["Close"], tc.get("ema_20", 20))
        df["EMA_55"] = calculate_ema(df["Close"], tc.get("ema_55", 55))
        df["EMA_200"] = calculate_ema(df["Close"], tc.get("ema_200", 200))
        df["RSI"] = calculate_rsi(df["Close"], period=14)

        latest = df.iloc[-1]
        close_price = latest["Close"]

        tech_score = 0
        fund_score = 0
        reasons = []

        # ----------------------------------------------------------------------
        # A. TECHNICAL ANALYSIS - DAILY (6 MARKS)
        # ----------------------------------------------------------------------
        df_150 = df.tail(150)
        high_150 = df_150["High"].max()

        # 1. 125-150 Days Consolidation
        if close_price < high_150:
            tech_score += 1
            reasons.append("125-150 Days Consolidation")

        # 2. Daily Super Junction
        ema20 = latest["EMA_20"]
        ema55 = latest["EMA_55"]
        ema200 = latest["EMA_200"]

        if pd.notna(ema20) and pd.notna(ema55) and pd.notna(ema200):
            ema_vals = [ema20, ema55, ema200]
            ema_spread = (max(ema_vals) - min(ema_vals)) / min(ema_vals)
            thresh = tc.get("junction_threshold", 0.025)

            if ema_spread <= thresh:
                diff_55 = (close_price - ema55) / ema55
                diff_200 = (close_price - ema200) / ema200
                if 0 <= diff_55 <= 0.02 and 0 <= diff_200 <= 0.02:
                    tech_score += 1
                    reasons.append("Daily Super Junction (EMA 20/55/200)")

        # 3. Daily Bottom Reversal
        recent_20_low = df["Low"].tail(20).min()
        recent_5_close_avg = df["Close"].tail(5).mean()
        if (
            close_price > recent_20_low * 1.03
            and recent_5_close_avg > recent_20_low
        ):
            tech_score += 1
            reasons.append("Daily Bottom Reversal Confirmed")

        # 4. RSI 60+ Breakout Zone (60.0 થી 63.0)
        rsi_min = tc.get("rsi_min", 60.0)
        rsi_max = tc.get("rsi_max", 63.0)
        if rsi_min <= latest["RSI"] <= rsi_max:
            tech_score += 1
            reasons.append(f"RSI 60+ Breakout ({latest['RSI']:.1f})")

        # 5. Daily 200 EMA Breakout
        df_60 = df.tail(60).copy()
        if "EMA_200" in df_60.columns and not df_60["EMA_200"].isnull().all():
            above_ema200 = (df_60["Close"] > df_60["EMA_200"]).astype(int)
            crossings = (above_ema200.diff() != 0).sum()
            if crossings >= 4 and close_price > latest["EMA_200"]:
                tech_score += 1
                reasons.append("Daily 200 EMA Breakout")

        # 6. Fibonacci Evaluation
        low_150 = df_150["Low"].min()
        fib_diff = high_150 - low_150
        fib_382 = low_150 + (fib_diff * 0.382)
        fib_500 = low_150 + (fib_diff * 0.500)

        if (
            abs(close_price - fib_382) / fib_382 <= 0.03
            or abs(close_price - fib_500) / fib_500 <= 0.03
        ):
            tech_score += 1
            reasons.append("Fibonacci Reversal Support")

        # ----------------------------------------------------------------------
        # B. FUNDAMENTAL ANALYSIS (6 MARKS)
        # ----------------------------------------------------------------------
        info = stock.info
        roe = info.get("returnOnEquity", 0) or 0
        roe = roe * 100 if roe < 1 else roe

        de = info.get("debtToEquity", 0) or 0
        if de > 10:
            de = de / 100

        promoter = (info.get("heldPercentInsiders", 0) or 0) * 100
        rev_growth = (info.get("revenueGrowth", 0) or 0) * 100
        profit_growth = (info.get("earningsGrowth", 0) or 0) * 100

        if roe >= fc.get("min_roe", 12):
            fund_score += 1
            reasons.append(f"ROE ({roe:.1f}%)")
        if de <= fc.get("max_debt_equity", 1.0):
            fund_score += 1
            reasons.append(f"D/E ({de:.2f})")
        if promoter >= fc.get("min_promoter", 40):
            fund_score += 1
            reasons.append(f"Promoter ({promoter:.1f}%)")
        if rev_growth >= fc.get("min_rev_growth", 5):
            fund_score += 1
            reasons.append(f"Rev Growth ({rev_growth:.1f}%)")
        if profit_growth >= fc.get("min_profit_growth", 5):
            fund_score += 1
            reasons.append(f"Profit Growth ({profit_growth:.1f}%)")

        # CWIP Expansion Analysis
        try:
            bs = stock.balance_sheet
            if "Capital Work In Progress" in bs.index:
                cwip_vals = bs.loc["Capital Work In Progress"].dropna().head(3)
                if (
                    len(cwip_vals) >= 3
                    and cwip_vals.iloc[0] > cwip_vals.iloc[1] > cwip_vals.iloc[2]
                ):
                    fund_score += 1
                    reasons.append("CWIP YoY Expansion")
        except Exception:
            pass

        iv_val = calculate_intrinsic_value(stock)
        total_score = tech_score + fund_score

        return {
            "symbol": ticker_symbol,
            "total_score": total_score,
            "tech_score": tech_score,
            "fund_score": fund_score,
            "close": round(close_price, 2),
            "rsi": round(latest["RSI"], 1),
            "iv": iv_val,
            "reasons": reasons,
        }

    except Exception as e:
        print(f"Error analyzing {ticker_symbol} (Daily): {e}")
        return None


# ==============================================================================
# 5. MAIN DISPATCHER
# ==============================================================================
def main():
    print("🚀 Starting Advanced DAILY Stock Screener Pipeline...")
    config = load_config("daily.yml")

    # Read secrets from GitHub Environment
    bot_token = os.getenv("TELEGRAM_TOKEN_PRADIP")
    chat_id = os.getenv("TELEGRAM_CHAT_ID_PRADIP")

    if not bot_token or not chat_id:
        telegram_cfg = config.get("telegram", {})
        bot_token = bot_token or telegram_cfg.get("bot_token")
        chat_id = chat_id or telegram_cfg.get("chat_id")

    watchlist = config.get("watchlist", [])
    total_stocks = len(watchlist)

    start_msg = f"⚡ *12-Marks Advanced DAILY Screener Started*\nScrutinizing total *{total_stocks}* stocks on Daily Timeframe..."
    send_telegram_alert(bot_token, chat_id, start_msg)

    passed_stocks = []

    for idx, symbol in enumerate(watchlist, 1):
        print(f"[{idx}/{total_stocks}] Analyzing {symbol} (Daily)...")
        res = analyze_stock_daily(symbol, config)

        if (
            res
            and res["total_score"]
            >= config.get("scoring_rules", {}).get("watch_score_pass", 6)
        ):
            passed_stocks.append(res)

    print("\n==================================================")
    print(
        f"✅ Advanced Daily Screening Finished. Candidates: {len(passed_stocks)}"
    )
    print("==================================================\n")

    if not passed_stocks:
        nil_message = (
            "📊 *12-Marks Advanced DAILY Stock Screener Report*\n\n"
            "❌ *Result:* No stocks met strict criteria today on Daily Chart (0 Stocks Found).\n\n"
            "💡 RSI 60-63 Breakout, Super Junction & Reversal filters applied."
        )
        send_telegram_alert(bot_token, chat_id, nil_message)
    else:
        passed_stocks.sort(key=lambda x: x["total_score"], reverse=True)
        report_msg = f"⚡ *12-Marks Advanced DAILY Screener Found {len(passed_stocks)} Candidates!*\n\n"

        for st in passed_stocks:
            min_pass = config.get("scoring_rules", {}).get("min_score_pass", 8)
            tag = (
                "🔥 *STRONG BUY (DAILY)*"
                if st["total_score"] >= min_pass
                else "👀 *WATCHLIST (DAILY)*"
            )
            report_msg += f"{tag}\n"
            report_msg += f"• *Stock:* {st['symbol']}\n"
            report_msg += f"• *Total Score:* {st['total_score']}/12 Marks\n"
            report_msg += f"• *Technical:* {st['tech_score']}/6  |  *Fundamental:* {st['fund_score']}/6\n"
            report_msg += f"• *Price:* ₹{st['close']}\n"
            report_msg += f"• *Intrinsic Value:* ₹{st['iv']}\n"
            report_msg += f"• *Daily RSI:* {st['rsi']}\n"
            report_msg += f"• *Triggers:* {', '.join(st['reasons'][:3])}\n\n"

        send_telegram_alert(bot_token, chat_id, report_msg)


if __name__ == "__main__":
    main()