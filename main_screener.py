import os
import yaml
import requests
import numpy as np
import pandas as pd
import yfinance as yf

# ==============================================================================
# 1. LOAD CONFIGURATION (config.yml)
# ==============================================================================
def load_config(config_path="config.yml"):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"કન્ફિગરેશન ફાઈલ '{config_path}' મળી નથી. કૃપા કરીને ચકાસો.")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# ==============================================================================
# 2. TELEGRAM ALERT FUNCTION
# ==============================================================================
def send_telegram_alert(bot_token, chat_id, message):
    if not bot_token or not chat_id or "YOUR_BOT" in str(bot_token):
        print("⚠️ ટેલિગ્રામ બોટ ટોકન અથવા ચેટ આઈડી કન્ફિગર કરેલ નથી.")
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
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
        eps = info.get('trailingEps', None)
        bvps = info.get('bookValue', None)
        if eps and bvps and eps > 0 and bvps > 0:
            iv = np.sqrt(22.5 * eps * bvps)
            return round(iv, 2)
        return "N/A"
    except Exception:
        return "N/A"

# ==============================================================================
# 4. TECHNICAL & FUNDAMENTAL ANALYSIS (WEEKLY CHART)
# ==============================================================================
def analyze_stock(ticker_symbol, config):
    try:
        stock = yf.Ticker(ticker_symbol)
        
        period = config['data_settings'].get('period', 'max')
        interval = config['data_settings'].get('interval', '1wk')
        
        df = stock.history(period=period, interval=interval)
        
        if df.empty or len(df) < 200:
            return None
            
        tc = config['technical_criteria']
        fc = config['fundamental_criteria']
        
        # Weekly Technical Indicators
        df['EMA_4'] = calculate_ema(df['Close'], tc['ema_4'])
        df['EMA_20'] = calculate_ema(df['Close'], tc['ema_20'])
        df['EMA_55'] = calculate_ema(df['Close'], tc['ema_55'])
        df['EMA_200'] = calculate_ema(df['Close'], tc['ema_200'])
        df['RSI'] = calculate_rsi(df['Close'], period=14)
        
        latest = df.iloc[-1]
        close_price = latest['Close']
        score = 0
        reasons = []
        
        # 1. Price > Weekly EMA 200
        if close_price > latest['EMA_200']:
            score += 1
            reasons.append("Price > Weekly EMA 200")
            
        # 2. Weekly EMA Junction
        ema_vals = [latest['EMA_4'], latest['EMA_20'], latest['EMA_55']]
        ema_spread = (max(ema_vals) - min(ema_vals)) / min(ema_vals)
        if ema_spread <= tc['junction_threshold']:
            score += 1
            reasons.append("Weekly EMA Junction")
            
        # 3. 3-Week EMA 4 Doji Reversal Breakout Logic
        doji_breakout_found = False
        # Look back over the last 3 weekly candles for a Doji at EMA 4
        for i in range(1, 4):
            if len(df) <= i:
                break
            candle = df.iloc[-i]
            body_size = abs(candle['Close'] - candle['Open'])
            total_range = candle['High'] - candle['Low']
            
            # Check if candle is a Doji at EMA 4
            if total_range > 0 and (body_size / total_range) <= tc['doji_body_ratio']:
                if candle['Low'] <= candle['EMA_4'] and candle['Close'] >= candle['EMA_4']:
                    # Reversal Confirmation: Current close must break above this Doji's High
                    if close_price > candle['High']:
                        doji_breakout_found = True
                        break

        if doji_breakout_found:
            score += 1
            reasons.append("3-Week EMA 4 Doji Breakout")
                
        # 4. Strict Weekly RSI Zone (55-58)
        if tc['rsi_min'] <= latest['RSI'] <= tc['rsi_max']:
            score += 1
            reasons.append(f"Strict Weekly RSI ({latest['RSI']:.1f})")
            
        # 5. Fibonacci Support Zone (52 Weeks High/Low)
        high_52 = df['High'].tail(52).max()
        low_52 = df['Low'].tail(52).min()
        fib_618 = high_52 - (high_52 - low_52) * tc['fib_level']
        if abs(close_price - fib_618) / fib_618 <= tc['fib_tolerance']:
            score += 1
            reasons.append("Fib 61.8% Support")

        # Fundamentals Analysis
        info = stock.info
        roe = (info.get('returnOnEquity', 0) or 0)
        roe = roe * 100 if roe < 1 else roe
        
        de = (info.get('debtToEquity', 0) or 0)
        if de > 10: de = de / 100
        
        promoter = (info.get('heldPercentInsiders', 0) or 0) * 100
        rev_growth = (info.get('revenueGrowth', 0) or 0) * 100
        profit_growth = (info.get('earningsGrowth', 0) or 0) * 100

        if roe >= fc['min_roe']: score += 1; reasons.append(f"ROE ({roe:.1f}%)")
        if de <= fc['max_debt_equity']: score += 1; reasons.append(f"D/E ({de:.2f})")
        if promoter >= fc['min_promoter']: score += 1; reasons.append(f"Promoter ({promoter:.1f}%)")
        if rev_growth >= fc['min_rev_growth']: score += 1; reasons.append(f"Rev Growth ({rev_growth:.1f}%)")
        if profit_growth >= fc['min_profit_growth']: score += 1; reasons.append(f"Profit Growth ({profit_growth:.1f}%)")
            
        # CWIP Expansion Analysis
        try:
            bs = stock.balance_sheet
            if 'Capital Work In Progress' in bs.index:
                cwip_vals = bs.loc['Capital Work In Progress'].dropna().head(3)
                if len(cwip_vals) >= 3 and cwip_vals.iloc[0] > cwip_vals.iloc[1] > cwip_vals.iloc[2]:
                    score += 1
                    reasons.append("CWIP YoY Expansion")
        except Exception:
            pass

        iv_val = calculate_intrinsic_value(stock)

        return {
            "symbol": ticker_symbol,
            "score": score,
            "close": round(close_price, 2),
            "rsi": round(latest['RSI'], 1),
            "iv": iv_val,
            "reasons": reasons
        }

    except Exception as e:
        print(f"Error analyzing {ticker_symbol}: {e}")
        return None

# ==============================================================================
# 5. MAIN DISPATCHER
# ==============================================================================
def main():
    print("🚀 Starting Weekly Stock Screener Pipeline...")
    config = load_config("config.yml")
    
    bot_token = config['telegram']['bot_token']
    chat_id = config['telegram']['chat_id']
    
    watchlist = config.get('watchlist', [])
    total_stocks = len(watchlist)
    
    start_msg = f"🔍 *11-Marks Weekly Screener Started*\nScrutinizing total *{total_stocks}* stocks using config.yml..."
    send_telegram_alert(bot_token, chat_id, start_msg)
    
    passed_stocks = []
    
    for idx, symbol in enumerate(watchlist, 1):
        print(f"[{idx}/{total_stocks}] Analyzing {symbol} (Weekly)...")
        res = analyze_stock(symbol, config)
        
        if res and res['score'] >= config['scoring_rules']['watch_score_pass']:
            passed_stocks.append(res)

    print("\n==================================================")
    print(f"✅ Weekly Screening Finished. Candidates: {len(passed_stocks)}")
    print("==================================================\n")
    
    if not passed_stocks:
        nil_message = (
            "📊 *11-Marks Weekly Stock Screener Report*\n\n"
            "❌ *Result:* No stocks met criteria this week on Weekly Chart (0 Stocks Found).\n\n"
            "💡 All technical & fundamental rules applied strictly."
        )
        send_telegram_alert(bot_token, chat_id, nil_message)
    else:
        passed_stocks.sort(key=lambda x: x['score'], reverse=True)
        report_msg = f"🎯 *11-Marks Weekly Screener Found {len(passed_stocks)} Candidates!*\n\n"
        
        for st in passed_stocks:
            tag = "🔥 *STRONG BUY*" if st['score'] >= config['scoring_rules']['min_score_pass'] else "👀 *WATCHLIST*"
            report_msg += f"{tag}\n"
            report_msg += f"• *Stock:* {st['symbol']}\n"
            report_msg += f"• *Score:* {st['score']}/11 Marks\n"
            report_msg += f"• *Price:* ₹{st['close']}\n"
            report_msg += f"• *Intrinsic Value:* ₹{st['iv']}\n"
            report_msg += f"• *Weekly RSI:* {st['rsi']}\n"
            report_msg += f"• *Triggers:* {', '.join(st['reasons'][:3])}\n\n"
            
        send_telegram_alert(bot_token, chat_id, report_msg)

if __name__ == "__main__":
    main()