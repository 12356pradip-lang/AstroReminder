import os
import time
import math
import yaml
import requests
import yfinance as yf
import pandas as pd
import numpy as np
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

# ----------------------------------------------------
# 1. Load YAML Configuration
# ----------------------------------------------------
def load_config(config_path="config.yml"):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file '{config_path}' not found.")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# ----------------------------------------------------
# 2. Telegram Alert Integration
# ----------------------------------------------------
def send_telegram_alert(df_output, csv_filename, config):
    telegram_cfg = config.get('telegram', {})
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", telegram_cfg.get('bot_token'))
    chat_id = os.getenv("TELEGRAM_CHAT_ID", telegram_cfg.get('chat_id'))

    if not bot_token or not chat_id or bot_token == "YOUR_TELEGRAM_BOT_TOKEN":
        print("\n⚠️ Telegram credentials invalid or missing in config.yml. Skipping alert.")
        return

    df_strong = df_output[df_output['Signal'].str.contains("STRONG BUY", na=False)].copy()

    msg = f"🌟 *TOP PRIORITY CREAM STOCKS*\n"
    msg += f"📅 {datetime.now().strftime('%d-%b-%Y | %I:%M %p')}\n"
    msg += "─────────────────────────\n\n"

    if not df_strong.empty:
        for idx, row in df_strong.iterrows():
            msg += f"🔥 *{row['Symbol']}*\n"
            msg += f"📊 Score: `{row['Total Score']}` | CMP: `₹{row['CMP']}`\n"
            msg += f"💎 Intrinsic Val: `₹{row['Intrinsic Value']}` ({row['Undervalued']})\n"
            msg += f"📈 Pattern: `{row['EMA Pattern']}` | RSI: `{row['W-RSI']}`\n"
            msg += f"🎯 ROE: `{row['ROE (%)']}%` | D/E: `{row['D/E']}`\n"
            msg += "─────────────────────────\n"
    else:
        msg += "⚠️ *આજે કોઈ સ્ટોક એક્સ્ટ્રીમ-સ્ટ્રિક્ટ ક્રાઈટેરિયામાં મેચ થયો નથી.*\n"
        msg += "💡 (નકામા સિગ્નલથી બચવા માટે સિસ્ટમ શાંત રહી છે).\n\n"

    msg += "\n📁 *આખી સ્ક્રીનિંગ ફાઈલ જોવા માટે નીચે આપેલી CSV ડાઉનલોડ કરો.*"

    try:
        text_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        requests.post(text_url, data={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}, timeout=10)

        doc_url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
        with open(csv_filename, 'rb') as f:
            requests.post(doc_url, data={"chat_id": chat_id}, files={"document": f}, timeout=15)

        print("📱 Telegram Alert Sent Successfully!")
    except Exception as e:
        print(f"❌ Failed to send Telegram alert: {e}")

# ----------------------------------------------------
# 3. Technical & Weekly EMA Junction + Volume
# ----------------------------------------------------
def analyze_weekly_ema_junction(df_weekly, config):
    tc = config['technical_criteria']
    
    if df_weekly is None or df_weekly.empty or len(df_weekly) < tc['ema_slow']:
        return {
            "Tech_Score": 0, 
            "EMA_Status": "Data Deficit", 
            "Correction_Ended": "NO",
            "Weekly_RSI": 0.0,
            "Volume_Spike": "NO",
            "CMP": 0.0
        }

    df_weekly['EMA20'] = df_weekly['Close'].ewm(span=tc['ema_fast'], adjust=False).mean()
    df_weekly['EMA50'] = df_weekly['Close'].ewm(span=tc['ema_mid'], adjust=False).mean()
    df_weekly['EMA200'] = df_weekly['Close'].ewm(span=tc['ema_slow'], adjust=False).mean()

    delta = df_weekly['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / (loss + 1e-10)
    df_weekly['RSI'] = 100 - (100 / (1 + rs))

    latest = df_weekly.iloc[-1]
    prev = df_weekly.iloc[-2]

    avg_volume = df_weekly['Volume'].tail(20).mean()
    vol_spike = "YES" if latest['Volume'] > (avg_volume * 1.2) else "NO"

    ema_diff = abs(latest['EMA20'] - latest['EMA50']) / latest['EMA50']
    is_ema_junction = ema_diff <= tc['junction_threshold']

    above_all_emas = (latest['Close'] > latest['EMA20']) and (latest['Close'] > latest['EMA50'])
    ema_crossover = (prev['EMA20'] <= prev['EMA50']) and (latest['EMA20'] > latest['EMA50'])
    ema200_bounce = (prev['Low'] <= prev['EMA200']) and (latest['Close'] > latest['EMA200'])

    is_correction_ended = above_all_emas and (is_ema_junction or ema_crossover or ema200_bounce)
    rsi_ok = tc['rsi_min'] <= latest['RSI'] <= tc['rsi_max']

    tech_score = 0
    if above_all_emas: tech_score += 1
    if is_ema_junction or ema_crossover or ema200_bounce: tech_score += 1
    if rsi_ok: tech_score += 1

    junction_desc = "SQUEEZE" if is_ema_junction else ("CROSSOVER" if ema_crossover else "SUPPORT BOUNCE")

    return {
        "Tech_Score": tech_score,
        "Weekly_RSI": round(float(latest['RSI']), 1),
        "EMA_Status": junction_desc,
        "Correction_Ended": "YES 🎯" if is_correction_ended else "NO ⏳",
        "Volume_Spike": vol_spike,
        "CMP": round(float(latest['Close']), 2)
    }

# ----------------------------------------------------
# 4. Fundamental, Balance Sheet & Intrinsic Value Check
# ----------------------------------------------------
def analyze_fundamentals(stock_obj, cmp, config):
    fc = config['fundamental_criteria']
    
    try:
        info = stock_obj.info or {}
        balance_sheet = stock_obj.balance_sheet
    except Exception:
        return {"Fund_Score": 0, "ROE (%)": 0, "D/E": 0, "FA_Increasing": "NO", "Intrinsic_Value": 0.0, "Undervalued": "NO"}

    roe = info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') is not None else 0
    debt_equity = info.get('debtToEquity', 0) / 100 if info.get('debtToEquity') is not None else 0
    promoter = info.get('heldPercentInsiders', 0) * 100 if info.get('heldPercentInsiders') is not None else 0
    earnings_growth = info.get('earningsGrowth', 0) * 100 if info.get('earningsGrowth') is not None else 0
    rev_growth = info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') is not None else 0

    # Intrinsic Value Calculation (Benjamin Graham's Formula)
    eps = info.get('trailingEps', 0)
    bvps = info.get('bookValue', 0)
    
    intrinsic_value = 0.0
    is_undervalued = False
    if eps > 0 and bvps > 0:
        intrinsic_value = round(math.sqrt(22.5 * eps * bvps), 2)
        if cmp > 0 and cmp <= intrinsic_value:
            is_undervalued = True

    fa_increasing = False
    possible_fa_keys = ['Net Tangible Assets', 'Gross Property Plant Equipment', 'Properties', 'Total Non Current Assets']
    fa_series = None

    if balance_sheet is not None and not balance_sheet.empty:
        for key in possible_fa_keys:
            if key in balance_sheet.index:
                fa_series = balance_sheet.loc[key].dropna()
                break

    if fa_series is not None and len(fa_series) >= 2:
        fa_history = fa_series.iloc[::-1]
        if fa_history.iloc[-1] > fa_history.iloc[0]:
            fa_increasing = True

    f_checks = {
        "ROE": roe >= fc['min_roe'],
        "DebtToEquity": debt_equity <= fc['max_debt_equity'],
        "PromoterHold": promoter >= fc['min_promoter'],
        "RevGrowth": rev_growth >= fc['min_rev_growth'],
        "ProfitGrowth": earnings_growth >= fc['min_profit_growth'],
        "FA_Growth": fa_increasing if fc['require_fa_growth'] else True,
        "Valuation": is_undervalued if fc.get('require_fair_valuation', False) else True
    }

    fund_score = sum(f_checks.values())

    return {
        "Fund_Score": fund_score,
        "ROE (%)": round(roe, 1),
        "D/E": round(debt_equity, 2),
        "FA_Increasing": "YES" if fa_increasing else "NO",
        "Intrinsic_Value": intrinsic_value,
        "Undervalued": "YES 💎" if is_undervalued else "NO"
    }

# ----------------------------------------------------
# 5. Safe History Fetcher
# ----------------------------------------------------
def fetch_safe_history(stock_obj, config):
    req_period = config['data_settings']['period']
    req_interval = config['data_settings']['interval']
    
    try:
        df = stock_obj.history(period=req_period, interval=req_interval)
        if df is None or df.empty:
            df = stock_obj.history(period="max", interval=req_interval)
        return df
    except Exception:
        return pd.DataFrame()

# ----------------------------------------------------
# 6. Main Screener Execution
# ----------------------------------------------------
def run_screener():
    print("=" * 80)
    print(f"🚀 ULTRA-CREAM STOCK SCREENER | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    config = load_config("config.yml")
    symbols = config.get("watchlist", [])
    
    if not symbols:
        print("❌ Error: No stock symbols found in config watchlist.")
        return

    final_reports = []
    total_symbols = len(symbols)

    for idx, symbol in enumerate(symbols, 1):
        print(f"[{idx:03d}/{total_symbols:03d}] Scanning: {symbol:<15}", end="\r")
        
        try:
            stock = yf.Ticker(symbol)
            
            df_weekly = fetch_safe_history(stock, config)
            if df_weekly.empty:
                continue

            tech_res = analyze_weekly_ema_junction(df_weekly, config)
            cmp = tech_res.get('CMP', 0.0)
            
            fund_res = analyze_fundamentals(stock, cmp, config)

            raw_total_score = tech_res.get('Tech_Score', 0) + fund_res.get('Fund_Score', 0)
            
            pass_mark = config['scoring_rules']['min_score_pass']   
            watch_mark = config['scoring_rules']['watch_score_pass'] 

            if raw_total_score >= pass_mark and tech_res.get('Correction_Ended') == "YES 🎯":
                decision = "🟢 STRONG BUY"
            elif raw_total_score >= watch_mark:
                decision = "🟡 WATCHLIST"
            else:
                decision = "🔴 REJECT"

            row = {
                "Symbol": symbol,
                "Signal": decision,
                "RawScore": raw_total_score,
                "Total Score": f"{raw_total_score}/10",
                "CMP": cmp,
                "Intrinsic Value": fund_res.get('Intrinsic_Value', 0.0),
                "Undervalued": fund_res.get('Undervalued', 'NO'),
                "Tech Score": f"{tech_res.get('Tech_Score', 0)}/3",
                "Fund Score": f"{fund_res.get('Fund_Score', 0)}/7",
                "Correction End?": tech_res.get('Correction_Ended', 'N/A'),
                "EMA Pattern": tech_res.get('EMA_Status', 'N/A'),
                "Volume Spike": tech_res.get('Volume_Spike', 'NO'),
                "W-RSI": tech_res.get('Weekly_RSI', 'N/A'),
                "ROE (%)": fund_res.get('ROE (%)', 'N/A'),
                "D/E": fund_res.get('D/E', 'N/A'),
                "FA Growth": fund_res.get('FA_Increasing', 'N/A')
            }
            final_reports.append(row)

        except Exception as e:
            continue
        finally:
            time.sleep(0.2)

    print("\n\n✅ Scanning Completed Successfully!\n")
    
    df_output = pd.DataFrame(final_reports)
    
    if df_output.empty:
        print("⚠️ No valid data processed.")
        return

    df_output = df_output.sort_values(by="RawScore", ascending=False).drop(columns=["RawScore"])

    output_filename = "nifty200_screening_results.csv"
    df_output.to_csv(output_filename, index=False)
    
    send_telegram_alert(df_output, output_filename, config)

if __name__ == "__main__":
    run_screener()