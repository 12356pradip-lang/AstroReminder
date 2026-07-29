import swisseph as swe
import requests
import os
import urllib.parse
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from google.oauth2 import service_account

# --- કોન્ફિગરેશન ---
SERVICE_ACCOUNT_FILE = 'credentials.json'
CALENDAR_ID = '12356pradip@gmail.com'
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN_PRADIP")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID_PRADIP")
HISTORY_FILE = "astro_alert_history.txt"
LAT, LON = 22.2735, 70.7513

PUSHKAR_DATA = [
    {"nakshatra": "કૃતિકા", "pada": 3, "navansh_rashi": "મીન", "mul_tatva": "અગ્નિ", "nav_tatva": "જળ", "pradhan": "જળ"},
    {"nakshatra": "ઉત્તરા ફાલ્ગુની", "pada": 4, "navansh_rashi": "મીન", "mul_tatva": "અગ્નિ", "nav_tatva": "જળ", "pradhan": "જળ"},
    {"nakshatra": "ઉત્તરાષાઢા", "pada": 4, "navansh_rashi": "મીન", "mul_tatva": "અગ્નિ", "nav_tatva": "જળ", "pradhan": "જળ"},
    {"nakshatra": "રોહિણી", "pada": 1, "navansh_rashi": "વૃષભ", "mul_tatva": "પૃથ્વી", "nav_tatva": "પૃથ્વી", "pradhan": "પૃથ્વી"},
    {"nakshatra": "હસ્ત", "pada": 2, "navansh_rashi": "વૃષભ", "mul_tatva": "પૃથ્વી", "nav_tatva": "પૃથ્વી", "pradhan": "પૃથ્વી"},
    {"nakshatra": "શ્રવણ", "pada": 2, "navansh_rashi": "વૃષભ", "mul_tatva": "પૃથ્વી", "nav_tatva": "પૃથ્વી", "pradhan": "પૃથ્વી"},
    {"nakshatra": "પુનર્વસુ", "pada": 4, "navansh_rashi": "કર્ક", "mul_tatva": "જળ/વાયુ", "nav_tatva": "જળ", "pradhan": "જળ (પ્રબળ)"},
    {"nakshatra": "વિશાખા", "pada": 1, "navansh_rashi": "કર્ક", "mul_tatva": "અગ્નિ", "nav_tatva": "જળ", "pradhan": "જળ-અગ્નિ મિશ્રિત"},
    {"nakshatra": "પૂર્વા ભાદ્રપદ", "pada": 1, "navansh_rashi": "કર્ક", "mul_tatva": "અગ્નિ", "nav_tatva": "જળ", "pradhan": "જળ-અગ્નિ મિશ્રિત"},
    {"nakshatra": "પુષ્ય", "pada": 2, "navansh_rashi": "કન્યા", "mul_tatva": "પૃથ્વી", "nav_tatva": "પૃથ્વી", "pradhan": "પૃથ્વી (પ્રબળ)"},
    {"nakshatra": "અનુરાધા", "pada": 3, "navansh_rashi": "કન્યા", "mul_tatva": "જળ", "nav_tatva": "પૃથ્વી", "pradhan": "પૃથ્વી-જળ મિશ્રિત"},
    {"nakshatra": "ઉત્તરા ભાદ્રપદ", "pada": 3, "navansh_rashi": "કન્યા", "mul_tatva": "જળ", "nav_tatva": "પૃથ્વી", "pradhan": "પૃથ્વી-જળ મિશ્રિત"},
    {"nakshatra": "આર્દ્રા", "pada": 4, "navansh_rashi": "મીન", "mul_tatva": "વાયુ", "nav_tatva": "જળ", "pradhan": "જળ-વાયુ મિશ્રિત"},
    {"nakshatra": "સ્વાતિ", "pada": 1, "navansh_rashi": "મીન", "mul_tatva": "વાયુ", "nav_tatva": "જળ", "pradhan": "જળ-વાયુ મિશ્રિત"},
    {"nakshatra": "શતભિષા", "pada": 1, "navansh_rashi": "મીન", "mul_tatva": "વાયુ", "nav_tatva": "જળ", "pradhan": "જળ-વાયુ મિશ્રિત"},
    {"nakshatra": "પુનર્વસુ", "pada": 2, "navansh_rashi": "વૃષભ", "mul_tatva": "જળ/વાયુ", "nav_tatva": "પૃથ્વી", "pradhan": "પૃથ્વી-વાયુ મિશ્રિત"},
    {"nakshatra": "વિશાખા", "pada": 3, "navansh_rashi": "વૃષભ", "mul_tatva": "અગ્નિ/વાયુ", "nav_tatva": "પૃથ્વી", "pradhan": "પૃથ્વી-વાયુ મિશ્રિત"},
    {"nakshatra": "પૂર્વા ભાદ્રપદ", "pada": 3, "navansh_rashi": "વૃષભ", "mul_tatva": "અગ્નિ/વાયુ", "nav_tatva": "પૃથ્વી", "pradhan": "પૃથ્વી-વાયુ મિશ્રિત"},
    {"nakshatra": "ભરણી", "pada": 3, "navansh_rashi": "તુલા", "mul_tatva": "પૃથ્વી", "nav_tatva": "વાયુ", "pradhan": "વાયુ-પૃથ્વી મિશ્રિત"},
    {"nakshatra": "પૂર્વા ફાલ્ગુની", "pada": 4, "navansh_rashi": "તુલા", "mul_tatva": "જળ", "nav_tatva": "વાયુ", "pradhan": "વાયુ-જળ મિશ્રિત"},
    {"nakshatra": "પૂર્વાષાઢા", "pada": 4, "navansh_rashi": "તુલા", "mul_tatva": "જળ", "nav_tatva": "વાયુ", "pradhan": "વાયુ-જળ મિશ્રિત"},
    {"nakshatra": "કૃતિકા", "pada": 1, "navansh_rashi": "ધનુ", "mul_tatva": "અગ્નિ", "nav_tatva": "અગ્નિ", "pradhan": "અગ્નિ (પ્રબળ)"},
    {"nakshatra": "ઉત્તરા ફાલ્ગુની", "pada": 2, "navansh_rashi": "ધનુ", "mul_tatva": "અગ્નિ", "nav_tatva": "અગ્નિ", "pradhan": "અગ્નિ (પ્રબળ)"},
    {"nakshatra": "ઉત્તરાષાઢા", "pada": 2, "navansh_rashi": "ધનુ", "mul_tatva": "અગ્નિ", "nav_tatva": "અગ્નિ", "pradhan": "અગ્નિ (પ્રબળ)"}
]

RASHIS = ["મેષ", "વૃષભ", "મિથુન", "કર્ક", "સિંહ", "કન્યા", "તુલા", "વૃશ્ચિક", "ધન", "મકર", "કુંભ", "મીન"]
NAKSHATRAS = [
    "અશ્વિની", "ભરણી", "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", 
    "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફಾલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", 
    "મૂળ", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદ", "ઉત્તરા ભાદ્રપદ", "રેવતી"
]

def format_dms(deg):
    try:
        deg = float(deg)
        d = int(deg)
        m = int((deg - d) * 60)
        s = round(((deg - d) * 60 - m) * 60, 1)
        return f"{d}° {m:02d}' {s:04.1f}\""
    except Exception as e:
        return f"{deg:.2f}°"

def get_astro_position(planet_id, target_time):
    """ sunmoon.tracker.py વાળું 100% સચોટ નિરયણ ડિગ્રી અને પદ લોજિક """
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    target_utc = target_time - timedelta(hours=5, minutes=30)
    jd = swe.julday(target_utc.year, target_utc.month, target_utc.day, 
                    target_utc.hour + target_utc.minute/60.0 + target_utc.second/3600.0)
    
    swe.set_topo(LON, LAT, 0)
    flags = swe.FLG_SIDEREAL | swe.FLG_TOPOCTR | swe.FLG_SWIEPH
    
    res = swe.calc_ut(jd, planet_id, flags)
    total_deg = res[0][0]  # કુલ નિરયણ ડિગ્રી (0 થી 360)
    
    rasi_idx = int(total_deg // 30) % 12
    rasi_name = RASHIS[rasi_idx]
    rasi_deg = total_deg % 30
    
    nak_span = 360.0 / 27.0  
    nak_idx = int(total_deg // nak_span) % 27
    nak_name = NAKSHATRAS[nak_idx]
    
    nak_deg = total_deg % nak_span
    pada_span = nak_span / 4.0
    pada = int(nak_deg // pada_span) + 1
    
    return rasi_name, rasi_deg, nak_name, pada, nak_deg, total_deg, jd

def get_fine_transition(p_id, target_entry):
    """ sunmoon.tracker.py જેવું પરફેક્ટ ફાઇન ટ્રાન્ઝિશન સર્ચ લોજિક """
    now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    search_start = now - timedelta(days=15 if p_id == 0 else 2)
    entry_time = None
    entry_data = None
    
    step_minutes = 60 if p_id == 0 else 5
    t_check = search_start
    end_limit = now + timedelta(days=15 if p_id == 0 else 2)
    
    while t_check <= end_limit:
        rasi, r_deg, nak, pada, n_deg, t_deg, _ = get_astro_position(p_id, t_check)
        if nak == target_entry["nakshatra"] and pada == target_entry["pada"]:
            entry_time = t_check
            entry_data = (rasi, r_deg, pada, n_deg, t_deg)
            break
        t_check += timedelta(minutes=step_minutes)

    if entry_time:
        fine_check = entry_time - timedelta(minutes=step_minutes)
        for m in range(0, step_minutes * 2 + 1):
            t_f = fine_check + timedelta(minutes=m)
            rasi, r_deg, nak, pada, n_deg, t_deg, _ = get_astro_position(p_id, t_f)
            if nak == target_entry["nakshatra"] and pada == target_entry["pada"]:
                entry_time = t_f
                entry_data = (rasi, r_deg, pada, n_deg, t_deg)
                break

    exit_time = entry_time
    if entry_time:
        t_exit = entry_time + timedelta(hours=1)
        while True:
            rasi_e, r_deg_e, nak_e, pada_e, n_deg_e, t_deg_e, _ = get_astro_position(p_id, t_exit)
            if nak_e != target_entry["nakshatra"] or pada_e != target_entry["pada"]:
                exit_time = t_exit
                break
            t_exit += timedelta(hours=1 if p_id == 0 else 0.5)

    if entry_time and exit_time:
        return entry_time, exit_time, entry_data[0], entry_data[1], entry_data[2], entry_data[3], entry_data[4]
    
    return None, None, None, None, None, None, None

def is_alert_sent(alert_id):
    if not os.path.exists(HISTORY_FILE): return False
    with open(HISTORY_FILE, "r") as f: return alert_id in f.read().splitlines()

def mark_alert_sent(alert_id):
    with open(HISTORY_FILE, "a") as f: f.write(alert_id + "\n")

def create_calendar_event(summary, description):
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE): return False
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/calendar'])
        service = build('calendar', 'v3', credentials=creds)
        now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        event = {'summary': summary, 'description': description, 'start': {'dateTime': now.isoformat()}, 'end': {'dateTime': (now + timedelta(hours=1)).isoformat()}}
        service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    except Exception as e: print(f"Calendar Error: {e}")

def run_tracker():
    for p_id in [0, 1]:
        name = "સૂર્ય (Sun)" if p_id == 0 else "ચંદ્ર (Moon)"
        now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        
        for entry in PUSHKAR_DATA:
            entry_time, exit_time, rasi, r_deg, pada, n_deg, total_deg = get_fine_transition(p_id, entry)
            if entry_time and exit_time:
                if p_id == 0:
                    alert_id = f"{name}_{entry['nakshatra']}_{entry['pada']}_{exit_time.strftime('%Y%m%d')}"
                else:
                    alert_id = f"{name}_{entry['nakshatra']}_{entry['pada']}_{entry_time.strftime('%Y%m%d_%H')}"
                
                if not is_alert_sent(alert_id):
                    if entry_time > now and entry_time < (now + timedelta(hours=24)):
                        # ૧. અત્યારની રિયલ-ટાઇમ (Current) સ્થિતિ મેળવવા માટે
                        curr_time = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                        curr_rasi, curr_rd, curr_nak, curr_pada, curr_nd, curr_td, _ = get_astro_position(p_id, curr_time)

                        # ફાઇનल પ્રિન્ટ આઉટપુટ અને મેસેજ ફોર્મેટ (અપડેટ કરેલ)
                        curr_rd_formatted = format_dms(curr_rd)
                        curr_nd_formatted = format_dms(curr_nd)
                        curr_td_formatted = format_dms(curr_td)

                        msg = (f"<b>🌟 પુષ્કર નવાંશ એલર્ટ : {name}</b>\n\n"
                               f"• <b>કુલ નિરયણ ડિગ્રી:</b> {curr_td:.2f}° ({curr_td_formatted})\n"
                               f"• <b>વર્તમાન સ્થિતિ:</b> {curr_rasi} રાશિ (રાશિ ડિગ્રી: {curr_rd_formatted})\n"
                               f"• <b>વર્તમાન નક્ષત્ર સ્થિતિ:</b> {curr_nak} - {curr_pada} (નક્ષત્ર ડિગ્રી: {curr_nd_formatted})\n"
                               f"• <b>ભવિષ્યનું નક્ષત્ર:</b> <b>{entry['nakshatra']}</b>\n"
                               f"• <b>પુષ્કર નક્ષત્ર ભાગ:</b> {entry['nakshatra']} - {entry['pada']} (ચરણ પ્રવેશ)\n"
                               f"• <b>નક્ષત્ર પદ પ્રવેશ:</b> {entry_time.strftime('%d %b, %H:%M')}\n"
                               f"• <b>નિર્ગમન સમય:</b> {exit_time.strftime('%d %b, %H:%M')}\n"
                               f"• <b>નક્ષત્ર નવાંશ રાશિ:</b> {entry['navansh_rashi']}  |  <b>નક્ષત્ર મૂળ તત્વ:</b> {entry['mul_tatva']}\n"
                               f"• <b>નવાંશ તત્વ:</b> {entry['nav_tatva']}  |  <b>પ્રધાન તત્વ:</b> {entry['pradhan']}")
                        
                        print(f"\n{msg}\n")
                        if TELEGRAM_TOKEN:
                            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={urllib.parse.quote(msg)}&parse_mode=HTML"
                            requests.get(url)
                            
                        create_calendar_event(f"પુષ્કર: {name}", msg)
                        mark_alert_sent(alert_id)
                        break

if __name__ == "__main__":
    run_tracker()