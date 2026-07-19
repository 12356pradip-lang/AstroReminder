import swisseph as swe
import requests
import os
import urllib.parse
from datetime import datetime, timedelta
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
    {"nakshatra": "ઉત્તરાફાલ્ગુની", "pada": 4, "navansh_rashi": "મીન", "mul_tatva": "અગ્નિ", "nav_tatva": "જળ", "pradhan": "જળ"},
    {"nakshatra": "ઉત્તરાષાઢા", "pada": 4, "navansh_rashi": "મીન", "mul_tatva": "અગ્નિ", "nav_tatva": "જળ", "pradhan": "જળ"},
    {"nakshatra": "રોહિણી", "pada": 1, "navansh_rashi": "વૃષભ", "mul_tatva": "પૃથ્વી", "nav_tatva": "પૃથ્વી", "pradhan": "પૃથ્વી"},
    {"nakshatra": "હસ્ત", "pada": 2, "navansh_rashi": "વૃષભ", "mul_tatva": "પૃથ્વી", "nav_tatva": "પૃથ્વી", "pradhan": "પૃથ્વી"},
    {"nakshatra": "શ્રવણ", "pada": 2, "navansh_rashi": "વૃષભ", "mul_tatva": "પૃથ્વી", "nav_tatva": "પૃથ્વી", "pradhan": "પૃથ્વી"},
    {"nakshatra": "પુનર્વસુ", "pada": 4, "navansh_rashi": "કર્ક", "mul_tatva": "જળ/વાયુ", "nav_tatva": "જળ", "pradhan": "જળ (પ્રબળ)"},
    {"nakshatra": "વિશાખા", "pada": 1, "navansh_rashi": "કર્ક", "mul_tatva": "અગ્નિ", "nav_tatva": "જળ", "pradhan": "જળ-અગ્નિ મિશ્રિત"},
    {"nakshatra": "પૂર્વાભાદ્રપદ", "pada": 1, "navansh_rashi": "કર્ક", "mul_tatva": "અગ્નિ", "nav_tatva": "જળ", "pradhan": "જળ-અગ્નિ મિશ્રિત"},
    {"nakshatra": "પુષ્ય", "pada": 2, "navansh_rashi": "કન્યા", "mul_tatva": "પૃથ્વી", "nav_tatva": "પૃથ્વી", "pradhan": "પૃથ્વી (પ્રબળ)"},
    {"nakshatra": "અનુરાધા", "pada": 3, "navansh_rashi": "કન્યા", "mul_tatva": "જળ", "nav_tatva": "પૃથ્વી", "pradhan": "પૃથ્વી-જળ મિશ્રિત"},
    {"nakshatra": "ઉત્તરાભાદ્રપદ", "pada": 3, "navansh_rashi": "કન્યા", "mul_tatva": "જળ", "nav_tatva": "પૃથ્વી", "pradhan": "પૃથ્વી-જળ મિશ્રિત"},
    {"nakshatra": "આર્દ્રા", "pada": 4, "navansh_rashi": "મીન", "mul_tatva": "વાયુ", "nav_tatva": "જળ", "pradhan": "જળ-વાયુ મિશ્રિત"},
    {"nakshatra": "સ્વાતિ", "pada": 1, "navansh_rashi": "મીન", "mul_tatva": "વાયુ", "nav_tatva": "જળ", "pradhan": "જળ-વાયુ મિશ્રિત"},
    {"nakshatra": "શતભિષા", "pada": 1, "navansh_rashi": "મીન", "mul_tatva": "વાયુ", "nav_tatva": "જળ", "pradhan": "જળ-વાયુ મિશ્રિત"},
    {"nakshatra": "પુનર્વસુ", "pada": 2, "navansh_rashi": "વૃષભ", "mul_tatva": "જળ/વાયુ", "nav_tatva": "પૃથ્વી", "pradhan": "પૃથ્વી-વાયુ મિશ્રિત"},
    {"nakshatra": "વિશાખા", "pada": 3, "navansh_rashi": "વૃષભ", "mul_tatva": "અગ્નિ/વાયુ", "nav_tatva": "પૃથ્વી", "pradhan": "પૃથ્વી-વાયુ મિશ્રિત"},
    {"nakshatra": "પૂર્વાભાદ્રપદ", "pada": 3, "navansh_rashi": "વૃષભ", "mul_tatva": "અગ્નિ/વાયુ", "nav_tatva": "પૃથ્વી", "pradhan": "પૃથ્વી-વાયુ મિશ્રિત"},
    {"nakshatra": "ભરણી", "pada": 3, "navansh_rashi": "તુલા", "mul_tatva": "પૃથ્વી", "nav_tatva": "વાયુ", "pradhan": "વાયુ-પૃથ્વી મિશ્રિત"},
    {"nakshatra": "પૂર્વાફાલ્ગુની", "pada": 4, "navansh_rashi": "તુલા", "mul_tatva": "જળ", "nav_tatva": "વાયુ", "pradhan": "વાયુ-જળ મિશ્રિત"},
    {"nakshatra": "પૂર્વાષાઢા", "pada": 4, "navansh_rashi": "તુલા", "mul_tatva": "જળ", "nav_tatva": "વાયુ", "pradhan": "વાયુ-જળ મિશ્રિત"},
    {"nakshatra": "કૃતિકા", "pada": 1, "navansh_rashi": "ધનુ", "mul_tatva": "અગ્નિ", "nav_tatva": "અગ્નિ", "pradhan": "અગ્નિ (પ્રબળ)"},
    {"nakshatra": "ઉત્તરાફાલ્ગુની", "pada": 2, "navansh_rashi": "ધનુ", "mul_tatva": "અગ્નિ", "nav_tatva": "અગ્નિ", "pradhan": "અગ્નિ (પ્રબળ)"},
    {"nakshatra": "ઉત્તરાષાઢા", "pada": 2, "navansh_rashi": "ધનુ", "mul_tatva": "અગ્નિ", "nav_tatva": "અગ્નિ", "pradhan": "અગ્નિ (પ્રબળ)"}
]

def format_dms(deg):
    d = int(deg); m = int((deg - d) * 60); s = int(((deg - d) * 60 - m) * 60)
    return f"{d}°{m}'{s}\""

def get_astro_position(planet_id, target_time):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(target_time.year, target_time.month, target_time.day, target_time.hour + target_time.minute/60.0 + 5.5)
    swe.set_topo(LON, LAT, 0)
    data = swe.calc_ut(jd, planet_id, swe.FLG_SIDEREAL | swe.FLG_TOPOCTR)[0][0]
    if planet_id == 1: data = (data - 2.9) % 360
    rasi_idx = int(data // 30)
    rasi_name = ["મેષ", "વૃષભ", "મિથુન", "કર્ક", "સિંહ", "કન્યા", "તુલા", "વૃશ્ચિક", "ધન", "મકર", "કુંભ", "મીન"][rasi_idx]
    nakshatras = ["અશ્વિની", "ભરણી", "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફાલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", "મૂળ", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદ", "ઉત્તરા ભાદ્રપદ", "રેવતી"]
    nak_idx = int(data // 13.333333333333334)
    pada = int((data % 13.333333333333334) // 3.3333333333333335) + 1
    return rasi_name, data % 30, nakshatras[nak_idx % 27], data % 13.333333333333334, pada

def get_fine_transition(p_id, target_entry):
    start = datetime.utcnow()
    # 1 કલાકના ગાળે શોધો
    for i in range(0, 24 * 60, 60):
        t_check = start + timedelta(minutes=i)
        _, _, n, _, p = get_astro_position(p_id, t_check)
        if n == target_entry["nakshatra"] and p == target_entry["pada"]:
            # પ્રવેશ મળી ગયો, હવે 1-મિનિટની ચોકસાઈથી પાછળનું સ્ટેપ શોધો
            for j in range(max(0, i-60), i):
                t_fine = start + timedelta(minutes=j)
                _, _, n_f, _, p_f = get_astro_position(p_id, t_fine)
                if n_f == target_entry["nakshatra"] and p_f == target_entry["pada"]:
                    entry_t = t_fine + timedelta(hours=5, minutes=30)
                    # હવે નિર્ગમન શોધો
                    for k in range(j, j + 48 * 60):
                        t_exit = start + timedelta(minutes=k)
                        _, _, n_e, _, p_e = get_astro_position(p_id, t_exit)
                        if n_e != target_entry["nakshatra"] or p_e != target_entry["pada"]:
                            return entry_t, t_exit + timedelta(hours=5, minutes=30)
            break
    return None, None

def is_alert_sent(alert_id):
    if not os.path.exists(HISTORY_FILE): return False
    with open(HISTORY_FILE, "r") as f: return alert_id in f.read().splitlines()

def mark_alert_sent(alert_id):
    with open(HISTORY_FILE, "a") as f: f.write(alert_id + "\n")

def create_calendar_event(summary, description):
    try:
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/calendar'])
        service = build('calendar', 'v3', credentials=creds)
        event = {'summary': summary, 'description': description, 'start': {'dateTime': datetime.utcnow().isoformat() + 'Z'}, 'end': {'dateTime': (datetime.utcnow() + timedelta(hours=1)).isoformat() + 'Z'}}
        service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    except Exception as e: print(f"Calendar Error: {e}")

def run_tracker():
    for p_id in [0, 1]:
        name = "સૂર્ય" if p_id == 0 else "ચંદ્ર"
        now = datetime.utcnow()
        c_rasi, c_rd, c_nak, c_nd, c_pada = get_astro_position(p_id, now)
        
        for entry in PUSHKAR_DATA:
            entry_time, exit_time = get_fine_transition(p_id, entry)
            if entry_time and exit_time:
                alert_id = f"{name}_{entry['nakshatra']}_{entry['pada']}_{entry_time.strftime('%Y%m%d_%H')}"
                if not is_alert_sent(alert_id):
                    msg = (f"એડવાન્સ એલર્ટ: {name}\nહાલ {c_rasi} રાશિમાં {format_dms(c_rd)} પર {c_nak} નક્ષત્રમાં {format_dms(c_nd)} પર છે.\n"
                           f"જે આગામી {entry_time.strftime('%H:%M, %d %b')} ના રોજ પુષ્કર નાવંશ {entry['nakshatra']} નક્ષત્રના {entry['pada']} પદમાં પ્રવેશ કરશે.\n"
                           f"અને {exit_time.strftime('%H:%M, %d %b')} ના રોજ આ પદમાંથી નિર્ગમન કરશે.\n"
                           f"આ પદની નાવંશ રાશિ {entry['navansh_rashi']} છે. મૂળ નક્ષત્ર તત્વ {entry['mul_tatva']} છે.\n"
                           f"નાવંશ તત્વ {entry['nav_tatva']} છે અને પ્રધાન તત્વ {entry['pradhan']} છે.")
                    print(msg)
                    msg_encoded = urllib.parse.quote(msg)
                    requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={msg_encoded}")
                    create_calendar_event(f"પુષ્કર: {name}", msg)
                    mark_alert_sent(alert_id)
                    break

if __name__ == "__main__":
    run_tracker()