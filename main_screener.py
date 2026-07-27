import os
import yaml
import requests
import pandas as pd
import yfinance as yf
import ta

# ==============================================================================
# 1. LOAD CONFIGURATION
# ==============================================================================
def load_config(config_path="config.yml"):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"કન્ફિગરેશન ફાઈલ '{config_path}' મળી નથી. કૃપા કરીને ચકાસો.")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_yaml(f)

# ==============================================================================
# 2. TELEGRAM ALERT FUNCTION
# ==============================================================================
def send_telegram_alert(bot_token, chat_id, message):
    """
    ટેલિગ્રામ પર મેસેજ મોકલવા માટેનું ફંક્શન
    """
    if not bot_token or not chat_id or "YOUR_BOT" in bot_token:
        print("⚠️ ટેલિગ્રામ બોટ ટોકન અથવા ચેટ આઈડી કન્ફિગર કરેલ નથી.")
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
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
# 3. TECHNICAL & FUNDAMENTAL ANALYSIS (11 MARKS SYSTEM)
# ==============================================================================
def analyze_stock(ticker_symbol, config):
    try:
        stock = yf.Ticker(ticker_symbol)
        
        # --- Fetch Weekly Data ---
        period = config['data_settings']['period']
        interval = config['data_settings']['interval']
        df = stock.history(period=period, interval=interval)
        
        if df.empty or len(df) < 200:
            return None
            
        tc = config['technical_criteria']
        fc = config['fundamental_criteria']
        
        # Technical Calculations
        df['EMA_4'] = ta.trend.ema_indicator(df['Close'], window=tc['ema_4'])
        df['EMA_20'] = ta.trend.ema_indicator(df['Close'], window=tc['ema_20'])
        df['EMA_55'] = ta.trend.ema_indicator(df['Close'], window=tc['ema_55'])
        df['EMA_200'] = ta.trend.ema_indicator(df['Close'], window=tc['ema_200'])
        df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        close_price = latest['Close']
        
        score = 0
        reasons = []
        
        # Rule 1: Trend Alignment (Price > EMA 200) -> 1 Mark
        if close_price > latest['EMA_200']:
            score += 1
            reasons.append("Price > EMA 200")
            
        # Rule 2: EMA Junction (EMA 4, 20, 55 closeness) -> 1 Mark
        ema_vals = [latest['EMA_4'], latest['EMA_20'], latest['EMA_55']]
        ema_spread = (max(ema_vals) - min(ema_vals)) / min(ema_vals)
        if ema_spread <= tc['junction_threshold']:
            score += 1
            reasons.append("EMA Junction Formed")
            
        # Rule 3: Doji Reversal at EMA 4 -> 1 Mark
        body_size = abs(latest['Close'] - latest['Open'])
        total_range = latest['High'] - latest['Low']
        if total_range > 0 and (body_size / total_range) <= tc['doji_body_ratio']:
            if latest['Low'] <= latest['EMA_4'] and latest['Close'] >= latest['EMA_4']:
                score += 1
                reasons.append("EMA 4 Doji Reversal")
                
        # Rule 4: Strict RSI (55-58 Zone) -> 1 Mark
        if tc['rsi_min'] <= latest['RSI'] <= tc['rsi_max']:
            score += 1
            reasons.append(f"Strict RSI Zone ({latest['RSI']:.1f})")
            
        # Rule 5: Fibonacci Support (~61.8%) -> 1 Mark
        high_52 = df['High'].max()
        low_52 = df['Low'].min()
        fib_618 = high_52 - (high_52 - low_52) * tc['fib_level']
        if abs(close_price - fib_618) / fib_618 <= tc['fib_tolerance']:
            score += 1
            reasons.append("Fib 61.8% Support Zone")

        # --- Fundamental Data Fetching ---
        info = stock.info
        roe = info.get('returnOnEquity', 0) or 0
        roe = roe * 100 if roe < 1 else roe
        
        de = info.get('debtToEquity', 0) or 0
        if de > 10: de = de / 100  # Normalization
        
        promoter = (info.get('heldPercentInsiders', 0) or 0) * 100
        rev_growth = (info.get('revenueGrowth', 0) or 0) * 100
        profit_growth = (info.get('earningsGrowth', 0) or 0) * 100

        # Rule 6: ROE Criteria -> 1 Mark
        if roe >= fc['min_roe']:
            score += 1
            reasons.append(f"Good ROE ({roe:.1f}%)")
            
        # Rule 7: Debt/Equity Criteria -> 1 Mark
        if de <= fc['max_debt_equity']:
            score += 1
            reasons.append(f"Low Debt/Equity ({de:.2f})")
            
        # Rule 8: Promoter Holding Criteria -> 1 Mark
        if promoter >= fc['min_promoter']:
            score += 1
            reasons.append(f"Strong Promoter Holding ({promoter:.1f}%)")
            
        # Rule 9: Revenue Growth -> 1 Mark
        if rev_growth >= fc['min_rev_growth']:
            score += 1
            reasons.append(f"Revenue Growth ({rev_growth:.1f}%)")
            
        # Rule 10: Profit Growth -> 1 Mark
        if profit_growth >= fc['min_profit_growth']:
            score += 1
            reasons.append(f"Profit Growth ({profit_growth:.1f}%)")
            
        # Rule 11: CWIP Capex Expansion -> 1 Mark
        try:
            bs = stock.balance_sheet
            cwip_score_given = False
            if 'Capital Work In Progress' in bs.index:
                cwip_vals = bs.loc['Capital Work In Progress'].dropna().head(3)
                if len(cwip_vals) >= 3:
                    if cwip_vals.iloc[0] > cwip_vals.iloc[1] > cwip_vals.iloc[2]:
                        score += 1
                        reasons.append("CWIP YoY Expansion (3 Yrs)")
                        cwip_score_given = True
            if not cwip_score_given:
                reasons.append("CWIP Data Missing/Flat")
        except Exception:
            pass

        return {
            "symbol": ticker_symbol,
            "score": score,
            "close": close_price,
            "rsi": latest['RSI'],
            "reasons": reasons
        }

    except Exception as e:
        print(f" Error analyzing {ticker_symbol}: {e}")
        return None

# ==============================================================================
# 4. MAIN RUNNER & TELEGRAM DISPATCHER
# ==============================================================================
def main():
    print("🚀 Starting Stock Screener Pipeline...")
    config = load_config()
    
    bot_token = config['telegram']['bot_token']
    chat_id = config['telegram']['chat_id']
    
    watchlist = config.get('watchlist', [])
    total_stocks = len(watchlist)
    
    # 🔔 STEP 1: INITIAL TELEGRAM NOTIFICATION
    start_msg = f"🔍 *Stock Screener Started*\n\nScrutinizing total *{total_stocks}* stocks based on 11-Marks Criteria..."
    send_telegram_alert(bot_token, chat_id, start_msg)
    
    passed_stocks = []
    
    # Process Stock List
    for idx, symbol in enumerate(watchlist, 1):
        print(f"[{idx}/{total_stocks}] Analyzing {symbol}...")
        res = analyze_stock(symbol, config)
        
        if res:
            # Check minimum watch threshold (Score >= 7)
            if res['score'] >= config['scoring_rules']['watch_score_pass']:
                passed_stocks.append(res)

    print("\n==================================================")
    print(f"✅ Screening Finished. Total candidates found: {len(passed_stocks)}")
    print("==================================================\n")
    
    # 🔔 STEP 2: DISPATCH RESULTS TO TELEGRAM (EVEN IF NIL)
    if not passed_stocks:
        # NIL Stock Case
        nil_message = (
            "📊 *11-Marks Stock Screener Report*\n\n"
            "❌ *Result:* No stocks met the selection criteria today (0 Stocks Found).\n\n"
            "💡 *Note:* The technical & fundamental conditions are strict, so no candidates qualified for Strong Buy (9+) or Watchlist (7+)."
        )
        send_telegram_alert(bot_token, chat_id, nil_message)
    else:
        # Stocks Found Case
        # Sort by score descending
        passed_stocks.sort(key=lambda x: x['score'], reverse=True)
        
        report_msg = f"🎯 *11-Marks Screener Found {len(passed_stocks)} Candidates!*\n\n"
        
        for st in passed_stocks:
            tag = "🔥 *STRONG BUY*" if st['score'] >= config['scoring_rules']['min_score_pass'] else "👀 *WATCHLIST*"
            report_msg += f"{tag}\n"
            report_msg += f"• *Stock:* {st['symbol']}\n"
            report_msg += f"• *Score:* {st['score']}/11 Marks\n"
            report_msg += f"• *Price:* ₹{st['close']:.2f}\n"
            report_msg += f"• *RSI:* {st['rsi']:.1f}\n"
            report_msg += f"• *Triggers:* {', '.join(st['reasons'][:3])}\n\n"
            
        send_telegram_alert(bot_token, chat_id, report_msg)

if __name__ == "__main__":
    main()