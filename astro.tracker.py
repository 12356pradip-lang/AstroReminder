import swisseph as swe
import requests
import os
import urllib.parse
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from google.oauth2 import service_account

# કોન્ફિગરેશન
SERVICE_ACCOUNT_FILE = 'credentials.json'
CALENDAR_ID = '12356pradip@gmail.com'
TELEGRAM_TOKEN = "8731134888:AAGHEul75rh6HZBefn7WCrbXUCyBqJ_zeXU"
TELEGRAM_CHAT_ID = "478006282"
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

def format_dms(deg):
    d = int(deg); m = int((deg - d) * 60); s = int(((deg - d) * 60 - m) * 60)
    return f"{d}°{m}'{s}\""

def get_astro_position(planet_id, target_time):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    target_utc = target_time - timedelta(hours=5, minutes=30)
    jd = swe.julday(target_utc.year, target_utc.month, target_utc.day, 
                    target_utc.hour + target_utc.minute/60.0 + target_utc.second/3600.0)
    
    swe.set_topo(LON, LAT, 0)
    flags = swe.FLG_SIDEREAL | swe.FLG_TOPOCTR | swe.FLG_SWIEPH
    res = swe.calc_ut(jd, planet_id, flags)
    total_deg = res[0][0]  # કુલ નિરયણ ડિગ્રી (0 થી 360)
    
    if planet_id == 1: total_deg = (total_deg - 2.9) % 360
    
    rasi_idx = int(total_deg // 30) % 12
    rashis = ["મેષ", "વૃષભ", "મિથુન", "કર્ક", "સિંહ", "કન્યા", "તુલા", "વૃશ્ચિક", "ધન", "મકર", "કુંભ", "મીન"]
    rasi_name = rashis[rasi_idx]
    rasi_deg = total_deg % 30
    
    nak_span = 360.0 / 27.0  # 13.333333333333334
    nak_idx = int(total_deg // nak_span) % 27
    nakshatras = ["અશ્વિની", "ભરણી", "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફાલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", "મૂળ", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદ", "ઉત્તરા ભાદ્રપદ", "રેવતી"]
    nak_name = nakshatras[nak_idx]
    
    nak_deg = total_deg % nak_span
    pada_span = nak_span / 4.0
    pada = int(nak_deg // pada_span) + 1
    
    return rasi_name, rasi_deg, nak_name, pada, nak_deg, total_deg

def get_fine_transition(p_id, target_entry):
    now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    
    if p_id == 0:  # સૂર્ય માટે
        start_search = now - timedelta(days=15)
        entry_t = None
        entry_data = None
        for i in range(0, 15 * 24 + 48, 1):
            t_check = start_search + timedelta(hours=i)
            rasi, r_deg, n, p, n_deg, t_deg = get_astro_position(p_id, t_check)
            if n == target_entry["nakshatra"] and p == target_entry["pada"]:
                entry_t = t_check
                entry_data = (rasi, r_deg, p, n_deg, t_deg)
                break
        
        if not entry_t:
            return None, None, None, None, None, None, None

        t_exit = entry_t + timedelta(days=1)
        for _ in range(30 * 24):
            rasi_e, r_deg_e, n_e, p_e, n_deg_e, t_deg_e = get_astro_position(p_id, t_exit)
            if n_e != target_entry["nakshatra"] or p_e != target_entry["pada"]:
                break
            t_exit += timedelta(hours=1)
        return entry_t, t_exit, entry_data[0], entry_data[1], entry_data[2], entry_data[3], entry_data[4]

    else:  # ચંદ્ર માટે (30 કલાકની પરફેક્ટ લિમિટ)
        start = now - timedelta(days=2)
        entry_t = None
        entry_data = None
        for i in range(0, 72 * 60):  
            t_check = start + timedelta(minutes=i)
            rasi, r_deg, n, p, n_deg, t_deg = get_astro_position(p_id, t_check)
            if n == target_entry["nakshatra"] and p == target_entry["pada"]:
                entry_t = t_check
                entry_data = (rasi, r_deg, p, n_deg, t_deg)
                break
                
        if entry_t:
            for k in range(1, 30 * 60):
                t_exit = entry_t + timedelta(minutes=k)
                rasi_e, r_deg_e, n_e, p_e, n_deg_e, t_deg_e = get_astro_position(p_id, t_exit)
                if n_e != target_entry["nakshatra"] or p_e != target_entry["pada"]:
                    return entry_t, t_exit, entry_data[0], entry_data[1], entry_data[2], entry_data[3], entry_data[4]
                    
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
                        # એન્ટ્રી ટાઇમની એકદમ લાઈવ અને સચોટ ડિગ્રીઓ મેળવવા માટે
                        live_rasi, live_rd, live_nak, live_pada, live_nd, live_td = get_astro_position(p_id, entry_time)

                        # ફાઇનલ પ્રિન્ટ આઉટપુટ અને મેસેજ ફોર્મેટ (લાઈવ ડિગ્રીઓ અને parse_mode=HTML સાથે)
                        msg = (f"<b>🌟 પુષ્કર નવાંશ એલર્ટ : {name}</b>\n\n"
                               f"• <b>કુલ નિરયણ ડિગ્રી:</b> {live_td:.2f}° ({format_dms(live_td)})\n"
                               f"• <b>વર્તમાન સ્થિતિ:</b> {live_rasi} રાશિ (રાશિ ડિગ્રી: {format_dms(live_rd)})\n"
                               f"• <b>વર્તમાન નક્ષત્ર સ્થિતિ:</b> {entry['nakshatra']} - {entry['pada']} (નક્ષત્ર ડિગ્રી: {format_dms(live_nd)})\n"
                               f"• <b>ભવિષ્યનું નક્ષત્ર:</b> <b>{entry['nakshatra']}</b>\n"
                               f"• <b>પુષ્કર નક્ષત્ર ભાગ:</b> {entry['nakshatra']} - {entry['pada']}\n"
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