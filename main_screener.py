import os
import yaml
import yfinance as yf
import pandas as pd
import numpy as np
import warnings
from datetime import datetime

# Ignore unnecessary technical pandas warnings
warnings.filterwarnings('ignore')

# ----------------------------------------------------
# 1. Load YAML Configuration
# ----------------------------------------------------
def load_config(config_path="config.yml"):
    """
    Reads parameters and stock watchlist from config.yml
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file '{config_path}' not found. Please ensure it exists in the root folder.")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# ----------------------------------------------------
# 2. Phase 1: Technical & Weekly EMA Junction Logic
# ----------------------------------------------------
def analyze_weekly_ema_junction(df_weekly, config):
    """
    Analyzes Weekly EMA 20, 50, 200, Squeeze/Junction, and RSI
    """
    tc = config['technical_criteria']
    
    # Validation: Minimum data length required for 200 EMA
    if df_weekly is None or df_weekly.empty or len(df_weekly) < tc['ema_slow']:
        return {
            "Tech_Score": 0, 
            "EMA_Status": "Data Deficit", 
            "Correction_Ended": "NO",
            "Weekly_RSI": 0.0
        }

    # Calculate Weekly Exponential Moving Averages (EMAs)
    df_weekly['EMA20'] = df_weekly['Close'].ewm(span=tc['ema_fast'], adjust=False).mean()
    df_weekly['EMA50'] = df_weekly['Close'].ewm(span=tc['ema_mid'], adjust=False).mean()
    df_weekly['EMA200'] = df_weekly['Close'].ewm(span=tc['ema_slow'], adjust=False).mean()

    # Calculate 14-period Weekly RSI
    delta = df_weekly['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df_weekly['RSI'] = 100 - (100 / (1 + rs))

    latest = df_weekly.iloc[-1]
    prev = df_weekly.iloc[-2]

    # 1. EMA Junction / Squeeze Check (Gap between EMA 20 & 50 <= Threshold %)
    ema_diff = abs(latest['EMA20'] - latest['EMA50']) / latest['EMA50']
    is_ema_junction = ema_diff <= tc['junction_threshold']

    # 2. Correction End Rules
    above_all_emas = (latest['Close'] > latest['EMA20']) and (latest['Close'] > latest['EMA50'])
    ema_crossover = (prev['EMA20'] <= prev['EMA50']) and (latest['EMA20'] > latest['EMA50'])
    ema200_support_bounce = (prev['Low'] <= prev['EMA200']) and (latest['Close'] > latest['EMA200'])

    is_correction_ended = above_all_emas and (is_ema_junction or ema_crossover or ema200_support_bounce)

    # Technical Scoring (Max 3 Points)
    rsi_ok = tc['rsi_min'] <= latest['RSI'] <= tc['rsi_max']

    tech_score = 0
    if above_all_emas: tech_score += 1
    if is_ema_junction or ema_crossover: tech_score += 1
    if rsi_ok: tech_score += 1

    # Pattern Status Label
    if is_ema_junction:
        junction_desc = "SQUEEZE"
    elif ema_crossover:
        junction_desc = "CROSSOVER"
    else:
        junction_desc = "SPREAD"

    return {
        "Tech_Score": tech_score,
        "Weekly_RSI": round(latest['RSI'], 1),
        "EMA_Status": junction_desc,
        "Correction_Ended": "YES 🎯" if is_correction_ended else "NO ⏳"
    }

# ----------------------------------------------------
# 3. Phase 2: Fundamental & Fixed Assets (CAPEX) Logic
# ----------------------------------------------------
def analyze_fundamentals(stock_obj, config):
    """
    Evaluates Fundamental Ratios and 5-Year Fixed Assets (CAPEX) Growth
    """
    fc = config['fundamental_criteria']
    
    try:
        info = stock_obj.info or {}
        balance_sheet = stock_obj.balance_sheet
    except Exception:
        return {"Fund_Score": 0, "ROE (%)": 0, "D/E": 0, "FA_Increasing": "NO"}

    # Extract Fundamental Metrics
    roe = info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') is not None else 0
    debt_equity = info.get('debtToEquity', 0) / 100 if info.get('debtToEquity') is not None else 0
    promoter = info.get('heldPercentInsiders', 0) * 100 if info.get('heldPercentInsiders') is not None else 0
    earnings_growth = info.get('earningsGrowth', 0) * 100 if info.get('earningsGrowth') is not None else 0
    rev_growth = info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') is not None else 0

    # Fixed Assets Trend Check (CAPEX Growth over years)
    fa_increasing = False
    possible_fa_keys = ['Net Tangible Assets', 'Gross Property Plant Equipment', 'Properties', 'Total Non Current Assets']
    fa_series = None

    if balance_sheet is not None and not balance_sheet.empty:
        for key in possible_fa_keys:
            if key in balance_sheet.index:
                fa_series = balance_sheet.loc[key].dropna()
                break

    if fa_series is not None and len(fa_series) >= 2:
        fa_history = fa_series.iloc[::-1]  # Sort chronologically
        if fa_history.iloc[-1] > fa_history.iloc[0]:
            fa_increasing = True

    # Fundamental Rule Checks (Max 6 Points)
    f_checks = {
        "ROE": roe >= fc['min_roe'],
        "DebtToEquity": debt_equity <= fc['max_debt_equity'],
        "PromoterHold": promoter >= fc['min_promoter'],
        "RevGrowth": rev_growth >= fc['min_rev_growth'],
        "ProfitGrowth": earnings_growth >= fc['min_profit_growth'],
        "FA_Growth": fa_increasing if fc['require_fa_growth'] else True
    }

    fund_score = sum(f_checks.values())

    return {
        "Fund_Score": fund_score,
        "ROE (%)": round(roe, 1),
        "D/E": round(debt_equity, 2),
        "FA_Increasing": "YES" if fa_increasing else "NO"
    }

# ----------------------------------------------------
# 4. Phase 3: Main Execution & Pipeline Integration
# ----------------------------------------------------
def run_screener():
    print("=" * 80)
    print(f"🚀 NIFTY 200 SCREENER RUNNING | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    config = load_config("config.yml")
    symbols = config.get("watchlist", [])
    
    if not symbols:
        print("❌ Error: No stock symbols found under 'watchlist' in config.yml.")
        return

    final_reports = []
    total_symbols = len(symbols)

    for idx, symbol in enumerate(symbols, 1):
        print(f"[{idx:03d}/{total_symbols:03d}] Scanning: {symbol:<15}", end="\r")
        
        try:
            stock = yf.Ticker(symbol)
            
            # Download Weekly Historical Data
            df_weekly = stock.history(
                period=config['data_settings']['period'], 
                interval=config['data_settings']['interval']
            )
            
            # Execute Technical & Fundamental Analyses
            tech_res = analyze_weekly_ema_junction(df_weekly, config)
            fund_res = analyze_fundamentals(stock, config)

            # Combined Scoring (Out of 9)
            total_score = tech_res.get('Tech_Score', 0) + fund_res.get('Fund_Score', 0)
            
            pass_mark = config['scoring_rules']['min_score_pass']
            watch_mark = config['scoring_rules']['watch_score_pass']

            # Decision Matrix
            if total_score >= pass_mark and tech_res.get('Correction_Ended') == "YES 🎯":
                decision = "🟢 STRONG BUY"
            elif total_score >= watch_mark:
                decision = "🟡 WATCHLIST"
            else:
                decision = "🔴 REJECT"

            # Prepare Consolidated Record
            row = {
                "Symbol": symbol,
                "Signal": decision,
                "Correction End?": tech_res.get('Correction_Ended', 'N/A'),
                "Total Score": f"{total_score}/9",
                "Tech Score": f"{tech_res.get('Tech_Score', 0)}/3",
                "Fund Score": f"{fund_res.get('Fund_Score', 0)}/6",
                "EMA Pattern": tech_res.get('EMA_Status', 'N/A'),
                "W-RSI": tech_res.get('Weekly_RSI', 'N/A'),
                "ROE (%)": fund_res.get('ROE (%)', 'N/A'),
                "D/E": fund_res.get('D/E', 'N/A'),
                "FA Growth": fund_res.get('FA_Increasing', 'N/A')
            }
            final_reports.append(row)

        except Exception as e:
            # Prevent crashes if yfinance fails for a specific ticker
            continue

    print("\n\n✅ Scanning Completed Successfully!\n")
    
    df_output = pd.DataFrame(final_reports)
    
    if df_output.empty:
        print("⚠️ No data was processed.")
        return

    # Filter High-Conviction Stocks for Terminal Display
    df_filtered = df_output[df_output['Signal'].str.contains("STRONG BUY|WATCHLIST")]

    print("=" * 95)
    print("📌 FILTERED HIGH-CONVICTION STOCKS")
    print("=" * 95)
    if not df_filtered.empty:
        print(df_filtered.to_string(index=False))
    else:
        print("No stocks matched the minimum threshold criteria today.")
    print("=" * 95)

    # Save Complete Report to CSV (Used by GitHub Actions)
    output_filename = "nifty200_screening_results.csv"
    df_output.to_csv(output_filename, index=False)
    print(f"\n📁 Full detailed report exported to: {output_filename}")

if __name__ == "__main__":
    run_screener()