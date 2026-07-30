import os
import numpy as np
import pandas as pd
import requests
import yaml
import yfinance as yf


# ==============================================================================
# 1. LOAD CONFIGURATION (config.yml)
# ==============================================================================
def load_config(config_path="config.yml"):
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"કન્ફિગરેશન ફાઈલ '{config_path}' મળી નથી. કૃપા કરીને ચકાસો."
        )
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ==============================================================================
# 2. TELEGRAM ALERT & DOCUMENT FUNCTION
# ==============================================================================
def send_telegram_alert(bot_token, chat_id, message):
    """સામાન્ય ટેક્સ્ટ મેસેજ મોકલવા માટેનું ફંક્શન (દા.ત. Starting / Nil report)."""
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


def send_telegram_top10_and_csv(
    bot_token, chat_id, passed_stocks, min_pass_score
):
    """Top 10 સ્ટોક્સને ટૂંકા કેપ્શન તરીકે મોકલશે અને બાકીના સ્ટોક્સની CSV અટેચ કરશે (1024 Char Limit Safe)."""
    if not bot_token or not chat_id:
        print("⚠️ ટેલિગ્રામ બોટ ટોકન અથવા ચેટ આઈડી મળેલ નથી.")
        return False

    # 1. Top 10 અને બાકીના સ્ટોક્સનું વિભાજન (Splitting)
    top_10_stocks = passed_stocks[:10]
    remaining_stocks = passed_stocks[10:]

    # 2. Telegram Caption 1024 char ની લિમિટમાં રહે તેવો ટૂંકો બનાવો
    caption = f"🎯 *12-Marks Weekly Screener Report*\n"
    caption += f"📊 Total Candidates: *{len(passed_stocks)}*\n\n"
    caption += f"🔥 *TOP {len(top_10_stocks)} CANDIDATES:* 🔥\n"

    for idx, st in enumerate(top_10_stocks, 1):
        tag = "🔥BUY" if st["total_score"] >= min_pass_score else "👀WATCH"
        # મેસેજ ટૂંકો રાખવો જેથી 1024 અક્ષરોની લિમિટ ક્રોસ ન થાય
        caption += f"*{idx}. {st['symbol']}* [{tag}]\n"
        caption += f"• Score: *{st['total_score']}/12* | Price: ₹{st['close']} | RSI: {st['rsi']}\n"

    # 3. જો 10 થી વધુ સ્ટોક્સ હોય તો CSV મોકલો, નહીંતર ફક્ત ટેક્સ્ટ મોકલો
    if remaining_stocks:
        caption += f"\n📁 *બાકીના {len(remaining_stocks)} સ્ટોક્સની વિગતવાર CSV નીચે જોડેલ છે.*"

        # CSV ફાઈલ તૈયાર કરો (બાકીના તમામ સ્ટોક્સ માટે)
        csv_filename = "remaining_weekly_stocks.csv"
        clean_data = []
        for st in remaining_stocks:
            clean_data.append({
                "Symbol": st["symbol"],
                "Total Score": st["total_score"],
                "Tech Score": st["tech_score"],
                "Fund Score": st["fund_score"],
                "Close Price": st["close"],
                "Intrinsic Value": st["iv"],
                "Weekly RSI": st["rsi"],
                "Triggers": " | ".join(st["reasons"]),
            })

        df = pd.DataFrame(clean_data)
        df.to_csv(csv_filename, index=False)

        # Telegram sendDocument API વાપરીને ફાઈલ સાથે કેપ્શન મોકલો
        url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
        payload = {
            "chat_id": chat_id,
            "caption": caption,
            "parse_mode": "Markdown",
        }

        try:
            with open(csv_filename, "rb") as file:
                files = {"document": file}
                response = requests.post(
                    url, data=payload, files=files, timeout=20
                )
                res_data = response.json()

            # ટેમ્પરરી ફાઈલ ડીલીટ કરો
            if os.path.exists(csv_filename):
                os.remove(csv_filename)

            if res_data.get("ok"):
                print(
                    "✅ Top 10 Alert અને બાકીના સ્ટોક્સની CSV ફાઈલ સફળતાપૂર્વક મોકલાઈ ગઈ."
                )
                return True
            else:
                print(
                    f"❌ ટેલિગ્રામ API એરર (CSV): {res_data.get('description')}"
                )
                return False
        except Exception as e:
            print(f"❌ ટેલિગ્રામ CSV કનેક્શન એરર: {e}")
            return False
    else:
        # જો કુલ સ્ટોક્સ 10 કે તેથી ઓછા જ હોય તો ફક્ત મેસેજ જ મોકલો
        return send_telegram_alert(bot_token, chat_id, caption)


# ==============================================================================
# 3. NATIVE TECHNICAL INDICATORS
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
# 4. ADVANCED TECHNICAL & FUNDAMENTAL ANALYSIS (WEEKLY CHART)
# ==============================================================================
def analyze_stock(ticker_symbol, config):
    try:
        stock = yf.Ticker(ticker_symbol)

        period = config["data_settings"].get("period", "max")
        interval = config["data_settings"].get("interval", "1wk")

        df = stock.history(period=period, interval=interval)

        if df.empty or len(df) < 150:
            return None

        fc = config.get("fundamental_criteria", {})

        # Weekly Technical Indicators
        df["EMA_20"] = calculate_ema(df["Close"], 20)
        df["EMA_55"] = calculate_ema(df["Close"], 55)
        df["EMA_200"] = calculate_ema(df["Close"], 200)
        df["RSI"] = calculate_rsi(df["Close"], period=14)

        latest = df.iloc[-1]
        close_price = latest["Close"]

        tech_score = 0
        fund_score = 0
        reasons = []

        # ----------------------------------------------------------------------
        # A. TECHNICAL ANALYSIS (6 MARKS)
        # ----------------------------------------------------------------------
        df_150 = df.tail(150)
        high_150 = df_150["High"].max()

        # 1. 125-150 Wks Consolidation
        if close_price < high_150:
            tech_score += 1
            reasons.append("125-150 Wks Consolidation")

        # 2. Super Junction
        ema20 = latest["EMA_20"]
        ema55 = latest["EMA_55"]
        ema200 = latest["EMA_200"]

        if pd.notna(ema20) and pd.notna(ema55) and pd.notna(ema200):
            ema_vals = [ema20, ema55, ema200]
            ema_spread = (max(ema_vals) - min(ema_vals)) / min(ema_vals)

            if ema_spread <= 0.025:
                diff_55 = (close_price - ema55) / ema55
                diff_200 = (close_price - ema200) / ema200
                if 0 <= diff_55 <= 0.02 and 0 <= diff_200 <= 0.02:
                    tech_score += 1
                    reasons.append("Super Junction (EMA 20/55/200)")

        # 3. Bottom Reversal
        recent_20_low = df["Low"].tail(20).min()
        recent_5_close_avg = df["Close"].tail(5).mean()
        if (
            close_price > recent_20_low * 1.03
            and recent_5_close_avg > recent_20_low
        ):
            tech_score += 1
            reasons.append("Bottom Reversal Confirmed")

        # 4. Strict RSI Zone
        if 55.0 <= latest["RSI"] <= 58.0:
            tech_score += 1
            reasons.append(f"Strict RSI 55-58 ({latest['RSI']:.1f})")

        # 5. 200 EMA 3rd Breakout
        df_60 = df.tail(60).copy()
        if "EMA_200" in df_60.columns and not df_60["EMA_200"].isnull().all():
            above_ema200 = (df_60["Close"] > df_60["EMA_200"]).astype(int)
            crossings = (above_ema200.diff() != 0).sum()
            if crossings >= 4 and close_price > latest["EMA_200"]:
                tech_score += 1
                reasons.append("200 EMA 3rd Breakout")

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

        # CWIP Expansion
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
        print(f"Error analyzing {ticker_symbol}: {e}")
        return None


# ==============================================================================
# 5. MAIN DISPATCHER
# ==============================================================================
def main():
    print("🚀 Starting Advanced Weekly Stock Screener Pipeline...")
    config = load_config("config.yml")

    # GitHub Secrets માંથી ઓટોમેટિક ટોકન અને આઈડી રીડ કરશે
    bot_token = os.getenv("TELEGRAM_TOKEN_PRADIP")
    chat_id = os.getenv("TELEGRAM_CHAT_ID_PRADIP")

    # જો એન્વાયરમેન્ટમાંથી ન મળે તો fallback તરીકે config.yml ચેક કરશે
    if not bot_token or not chat_id:
        telegram_cfg = config.get("telegram", {})
        bot_token = bot_token or telegram_cfg.get("bot_token")
        chat_id = chat_id or telegram_cfg.get("chat_id")

    watchlist = config.get("watchlist", [])
    total_stocks = len(watchlist)

    start_msg = f"🔍 *12-Marks Advanced Weekly Screener Started*\nScrutinizing total *{total_stocks}* stocks using config.yml..."
    send_telegram_alert(bot_token, chat_id, start_msg)

    passed_stocks = []

    for idx, symbol in enumerate(watchlist, 1):
        print(f"[{idx}/{total_stocks}] Analyzing {symbol} (Weekly)...")
        res = analyze_stock(symbol, config)

        if (
            res
            and res["total_score"]
            >= config.get("scoring_rules", {}).get("watch_score_pass", 6)
        ):
            passed_stocks.append(res)

    print("\n==================================================")
    print(
        f"✅ Advanced Weekly Screening Finished. Candidates: {len(passed_stocks)}"
    )
    print("==================================================\n")

    if not passed_stocks:
        nil_message = (
            "📊 *12-Marks Advanced Weekly Stock Screener Report*\n\n"
            "❌ *Result:* No stocks met strict criteria this week on Weekly Chart (0 Stocks Found).\n\n"
            "💡 Super Junction, Bottom Reversal & 200 EMA Breakout filters applied strictly."
        )
        send_telegram_alert(bot_token, chat_id, nil_message)
    else:
        # સ્કોર પ્રમાણે સૌથી સારા સ્ટોક્સ સૌથી ઉપર રહે તે રીતે સોર્ટ કરો
        passed_stocks.sort(key=lambda x: x["total_score"], reverse=True)

        min_pass = config.get("scoring_rules", {}).get("min_score_pass", 8)

        # Top 10 + બાકીના સ્ટોક્સની CSV મોકલો
        send_telegram_top10_and_csv(
            bot_token, chat_id, passed_stocks, min_pass
        )


if __name__ == "__main__":
    main()