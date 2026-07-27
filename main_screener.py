import os
import yaml
import requests
import numpy as np
import pandas as pd
import yfinance as yf

# ------------------------------------------------------------------------------
# 1. LOAD CONFIGURATION
# ------------------------------------------------------------------------------
def load_config(config_path="config.yml"):
    with open(config_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)

config = load_config()

# ------------------------------------------------------------------------------
# 2. TELEGRAM ALERT SYSTEM
# ------------------------------------------------------------------------------
def send_telegram_alert(message):
    token = config['telegram']['bot_token']
    chat_id = config['telegram']['chat_id']
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending Telegram alert: {e}")
        return False

# ------------------------------------------------------------------------------
# 3. INTRINSIC VALUE CALCULATOR (Graham's Revised Formula)
# ------------------------------------------------------------------------------
def calculate_intrinsic_value(ticker_obj):
    """
    Graham's Revised Formula થી Intrinsic Value ની ગણતરી:
    Intrinsic Value = sqrt(22.5 * EPS * Book Value Per Share)
    """
    try:
        info = ticker_obj.info
        eps = info.get('trailingEps', None)
        book_value = info.get('bookValue', None)

        if eps is not None and book_value is not None and eps > 0 and book_value > 0:
            intrinsic_val = np.sqrt(22.5 * eps * book_value)
            return round(intrinsic_val, 2)
        else:
            return "N/A"
    except Exception:
        return "N/A"

# ------------------------------------------------------------------------------
# 4. TECHNICAL INDICATORS & LOGIC
# ------------------------------------------------------------------------------
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def check_fibonacci_618(df, tolerance=0.02):
    """52-Week High/Low પરથી 61.8% Fib Retracement Support Zone ચકાસે છે."""
    if len(df) < 52:
        return False, 0.0
    
    recent_df = df.tail(52)
    high_price = recent_df['High'].max()
    low_price = recent_df['Low'].min()
    
    # 61.8% Golden Ratio Calculation
    fib_618 = high_price - (0.618 * (high_price - low_price))
    latest_close = df.iloc[-1]['Close']
    
    lower_bound = fib_618 * (1 - tolerance)
    upper_bound = fib_618 * (1 + tolerance)
    
    is_at_fib = lower_bound <= latest_close <= upper_bound
    return is_at_fib, round(fib_618, 2)

def check_ema4_doji_reversal(df, doji_ratio=0.25):
    """
    EMA 4 પાસે Doji બન્યા બાદ Close < EMA_4 થાય અને પછી Reversal આપે તે ચકાસે છે.
    """
    if len(df) < 3:
        return False, "Insufficient Data"
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    prev_range = prev['High'] - prev['Low']
    prev_body = abs(prev['Close'] - prev['Open'])
    
    if prev_range == 0:
        return False, "Invalid Range"
        
    body_ratio = prev_body / prev_range
    is_doji = body_ratio <= doji_ratio
    
    below_ema4 = prev['Close'] < prev['EMA_4']
    is_reversal = (latest['Close'] > prev['High']) and (latest['Close'] > latest['EMA_4'])
    
    if is_doji and below_ema4 and is_reversal:
        return True, f"Doji Reversal Confirmed (Body Ratio: {round(body_ratio*100, 1)}%)"
        
    return False, "No Pattern"

# ------------------------------------------------------------------------------
# 5. FUNDAMENTAL & CWIP ANALYSIS
# ------------------------------------------------------------------------------
def analyze_cwip_expansion(ticker_obj):
    """3 વર્ષનો સતત CWIP YoY વધારો ચકાસે છે."""
    try:
        bs = ticker_obj.balance_sheet
        if bs is None or bs.empty:
            return False, 0.0
            
        cwip_keys = [k for k in bs.index if 'Capital Work In Progress' in str(k) or 'CWIP' in str(k)]
        if not cwip_keys:
            return False, 0.0
            
        cwip_data = bs.loc[cwip_keys[0]].dropna()
        if len(cwip_data) < 3:
            return False, 0.0
            
        cwip_t = cwip_data.iloc[0]
        cwip_t1 = cwip_data.iloc[1]
        cwip_t2 = cwip_data.iloc[2]
        
        is_consistently_growing = (cwip_t > cwip_t1) and (cwip_t1 > cwip_t2)
        return is_consistently_growing, cwip_t
    except Exception:
        return False, 0.0

# ------------------------------------------------------------------------------
# 6. MAIN SCREENING PIPELINE
# ------------------------------------------------------------------------------
def screen_stock(symbol):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=config['data_settings']['period'], 
                            interval=config['data_settings']['interval'])
        
        if len(df) < 200:
            return None

        # Technical Calculations
        df['EMA_4'] = df['Close'].ewm(span=config['technical_criteria']['ema_4'], adjust=False).mean()
        df['EMA_20'] = df['Close'].ewm(span=config['technical_criteria']['ema_20'], adjust=False).mean()
        df['EMA_55'] = df['Close'].ewm(span=config['technical_criteria']['ema_55'], adjust=False).mean()
        df['EMA_200'] = df['Close'].ewm(span=config['technical_criteria']['ema_200'], adjust=False).mean()
        df['RSI'] = calculate_rsi(df['Close'])
        
        latest = df.iloc[-1]
        score = 0
        details = []

        # Intrinsic Value Calculation
        intrinsic_val = calculate_intrinsic_value(ticker)
        iv_display = f"₹{intrinsic_val}" if isinstance(intrinsic_val, (int, float)) else "N/A"

        # --- TECHNICAL TESTS (Max 5 Points) ---
        # 1. EMA Alignment
        if latest['EMA_4'] > latest['EMA_20'] > latest['EMA_55'] > latest['EMA_200']:
            score += 1
            details.append("EMA Alignment: PASS")
            
        # 2. Strict RSI (55 to 58)
        if config['technical_criteria']['rsi_min'] <= latest['RSI'] <= config['technical_criteria']['rsi_max']:
            score += 1
            details.append(f"Strict RSI ({round(latest['RSI'], 2)}): PASS")
            
        # 3. EMA Junction (20, 55, 200)
        max_ema = max(latest['EMA_20'], latest['EMA_55'], latest['EMA_200'])
        min_ema = min(latest['EMA_20'], latest['EMA_55'], latest['EMA_200'])
        if (max_ema - min_ema) / min_ema <= config['technical_criteria']['junction_threshold']:
            score += 1
            details.append("EMA Junction Compression: PASS")
            
        # 4. Fibonacci 61.8% Support Zone
        is_fib, fib_val = check_fibonacci_618(df, tolerance=config['technical_criteria']['fib_tolerance'])
        if is_fib:
            score += 1
            details.append(f"Fib 61.8% Support ({fib_val}): PASS")
            
        # 5. EMA 4 Doji Reversal
        is_doji_rev, doji_msg = check_ema4_doji_reversal(
            df, 
            doji_ratio=config['technical_criteria']['doji_body_ratio']
        )
        if is_doji_rev:
            score += 1
            details.append(f"EMA4 Doji Reversal: PASS ({doji_msg})")

        # --- FUNDAMENTAL TESTS (Max 6 Points) ---
        info = ticker.info
        roe = info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0
        de = info.get('debtToEquity', 0) / 100 if info.get('debtToEquity') else 0
        promoter = info.get('heldPercentInsiders', 0) * 100 if info.get('heldPercentInsiders') else 0
        rev_growth = info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') else 0
        profit_growth = info.get('earningsGrowth', 0) * 100 if info.get('earningsGrowth') else 0

        if roe >= config['fundamental_criteria']['min_roe']:
            score += 1
            details.append("ROE: PASS")
        if de <= config['fundamental_criteria']['max_debt_equity']:
            score += 1
            details.append("Debt/Equity: PASS")
        if promoter >= config['fundamental_criteria']['min_promoter']:
            score += 1
            details.append("Promoter Holding: PASS")
        if rev_growth >= config['fundamental_criteria']['min_rev_growth']:
            score += 1
            details.append("Revenue Growth: PASS")
        if profit_growth >= config['fundamental_criteria']['min_profit_growth']:
            score += 1
            details.append("Profit Growth: PASS")

        # 6. CWIP Expansion Analysis
        has_cwip_growth, cwip_val = analyze_cwip_expansion(ticker)
        if has_cwip_growth:
            score += 1
            details.append("CWIP 3-Yr YoY Growth: PASS")

        # --- CONSOLE PRINT & TELEGRAM NOTIFICATION ---
        cmp = round(latest['Close'], 2)

        if score >= config['scoring_rules']['min_score_pass']:
            # Terminal Print Output
            print(f"[{symbol}] Strong Buy Alert! Score: {score}/11 | CMP: ₹{cmp} | Intrinsic Val: {iv_display}")
            
            # Telegram Alert
            msg = f"🔥 *STRONG BUY ALERT: {symbol}*\n\n" \
                  f"📊 *Score:* {score}/11\n" \
                  f"💰 *CMP:* ₹{cmp}\n" \
                  f"💎 *Intrinsic Value:* {iv_display}\n" \
                  f"📈 *RSI:* {round(latest['RSI'], 2)}\n\n" \
                  f"*Matched Rules:*\n" + "\n".join([f"• {d}" for d in details])
            send_telegram_alert(msg)

        elif score >= config['scoring_rules']['watch_score_pass']:
            # Terminal Print Output
            print(f"[{symbol}] Watchlist Alert! Score: {score}/11 | CMP: ₹{cmp} | Intrinsic Val: {iv_display}")

            # Telegram Alert
            msg = f"👀 *WATCHLIST ALERT: {symbol}*\n\n" \
                  f"📊 *Score:* {score}/11\n" \
                  f"💰 *CMP:* ₹{cmp}\n" \
                  f"💎 *Intrinsic Value:* {iv_display}\n\n" \
                  f"*Matched Rules:*\n" + "\n".join([f"• {d}" for d in details])
            send_telegram_alert(msg)

        return {"Symbol": symbol, "Score": score, "CMP": cmp, "IntrinsicValue": iv_display}

    except Exception as e:
        print(f"Error processing {symbol}: {e}")
        return None

# ------------------------------------------------------------------------------
# RUN SCREENER
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    print("🚀 Running Screener with Intrinsic Value & Complete 11-Mark Pipeline...\n")
    results = []
    for stock in config['watchlist']:
        res = screen_stock(stock)
        if res:
            results.append(res)
    print("\n✅ Screening Complete!")