from datetime import datetime, timedelta, timezone
import swisseph as swe
import requests
import os
import urllib.parse
from googleapiclient.discovery import build
from google.oauth2 import service_account

# --- કોન્ફિગરેશન ---
TELEGRAM_TOKEN = "8731134888:AAGHEul75rh6HZBefn7WCrbXUCyBqJ_zeXU"
TELEGRAM_CHAT_ID = "478006282"
SERVICE_ACCOUNT_FILE = 'credentials.json'
CALENDAR_ID = '12356pradip@gmail.com'
SCOPES = ['https://www.googleapis.com/auth/calendar']
LAT, LON = 22.2735, 70.7513
HISTORY_FILE = "alert_history.txt"

NAVTARA_DATA = {
    "જન્મ તારા": ["ઉત્તરા ફાલ્ગુની", "ઉત્તરાષાઢા", "કૃતિકા"],
    "સંપત તારા": ["હસ્ત", "શ્રવણ", "રોહિણી"],
    "ક્ષેમ તારા": ["સ્વાતિ", "શતભિષા", "આર્દ્રા"],
    "સાધક તારા": ["અનુરાધા", "ઉત્તરા ભાદ્રપદ", "પુષ્ય"],
    "મૈત્રી તારા": ["મૂળ", "અશ્વિની", "મઘા"],
    "અતિ મૈત્રી તારા": ["પૂર્વાષાઢા", "ભરણી", "પૂર્વા ફાલ્ગુની"]
}

RASHIS = ["મેષ", "વૃષભ", "મિથુન", "કર્ક", "સિંહ", "કન્યા", "તુલા", "વૃશ્ચિક", "ધન", "મકર", "કુંભ", "મીન"]
NAKSHATRAS = ["અશ્વિની", "ભરણી", "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફાલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", "મૂળ", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદ", "ઉત્તરા ભાદ્રપદ", "રેવતી"]

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
    total_deg = res[0][0]
    
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

def get_fine_times(planet_id, target_nak):
    now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    
    if planet_id == 0:  # સૂર્ય માટે
        start_search = now - timedelta(days=15)
        entry = None
        entry_data = None
        for i in range(0, 15 * 24 + 48, 1):
            t_check = start_search + timedelta(hours=i)
            rasi, r_deg, nak, pada, n_deg, t_deg = get_astro_position(planet_id, t_check)
            if nak == target_nak:
                entry = t_check
                entry_data = (rasi, r_deg, pada, n_deg, t_deg)
                break
        
        if not entry:
            return None, None, None, None, None, None, None

        t_exit = entry + timedelta(days=1)
        for _ in range(30 * 24):
            rasi_e, r_deg_e, nak_e, pada_e, n_deg_e, t_deg_e = get_astro_position(planet_id, t_exit)
            if nak_e != target_nak:
                break
            t_exit += timedelta(hours=1)
        return entry, t_exit, entry_data[0], entry_data[1], entry_data[2], entry_data[3], entry_data[4]

    else:  # ચંદ્ર માટે (હાઈ-પ્રિસિઝન મિનિટ બેઝ્ડ સર્ચ અને ફાઈન ટ્યુનિંગ)
        start = now - timedelta(days=2)
        entry = None
        entry_data = None
        for i in range(0, 72 * 60, 5):  
            t_check = start + timedelta(minutes=i)
            rasi, r_deg, nak, pada, n_deg, t_deg = get_astro_position(planet_id, t_check)
            if nak == target_nak:
                entry = t_check
                entry_data = (rasi, r_deg, pada, n_deg, t_deg)
                break
                
        if entry:
            # ફાઈન મિનિટ ટ્યુનિંગ
            fine_start = entry - timedelta(minutes=10)
            for m in range(0, 20):
                t_f = fine_start + timedelta(minutes=m)
                rasi, r_deg, nak, pada, n_deg, t_deg = get_astro_position(planet_id, t_f)
                if nak == target_nak:
                    entry = t_f
                    entry_data = (rasi, r_deg, pada, n_deg, t_deg)
                    break

            t_exit = entry + timedelta(hours=1)
            for k in range(1, 30 * 60):
                t_ex_check = entry + timedelta(minutes=k)
                rasi_e, r_deg_e, nak_e, pada_e, n_deg_e, t_deg_e = get_astro_position(planet_id, t_ex_check)
                if nak_e != target_nak:
                    return entry, t_ex_check, entry_data[0], entry_data[1], entry_data[2], entry_data[3], entry_data[4]
                    
        return None, None, None, None, None, None, None

def create_calendar_event(summary, description):
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE): return False
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('calendar', 'v3', credentials=creds)
        now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        event = {
            'summary': summary,
            'description': description,
            'start': {'dateTime': now.isoformat()},
            'end': {'dateTime': (now + timedelta(hours=1)).isoformat()},
        }
        service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        return True
    except Exception as e:
        print(f"❌ કેલેન્ડર એરર: {e}")
        return False

def is_alert_sent(alert_id):
    if not os.path.exists(HISTORY_FILE): return False
    with open(HISTORY_FILE, "r") as f: return alert_id in f.read().splitlines()

def mark_alert_sent(alert_id):
    with open(HISTORY_FILE, "a") as f: f.write(alert_id + "\n")

def run_tracker():
    planets = {0: "સૂર્ય (Sun)", 1: "ચંદ્ર (Moon)"}
    future_time = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30) + timedelta(hours=12)

    for p_id, p_name in planets.items():
        fut_rasi, fut_r_deg, fut_n, fut_pada, fut_n_deg, fut_t_deg = get_astro_position(p_id, future_time)
        
        for tara, naks in NAVTARA_DATA.items():
            if fut_n in naks:
                if p_id == 0:
                    _, exit_t, _, _, _, _, _ = get_fine_times(p_id, fut_n)
                    if exit_t:
                        alert_id = f"{p_name}_{fut_n}_{exit_t.strftime('%Y%m%d')}"
                    else:
                        continue
                else:
                    entry_t, _, _, _, _, _, _ = get_fine_times(p_id, fut_n)
                    if entry_t:
                        alert_id = f"{p_name}_{fut_n}_{entry_t.strftime('%Y%m%d_%H')}"
                    else:
                        continue

                if is_alert_sent(alert_id): continue
                
                entry_t, exit_t, rasi, r_deg, pada, n_deg, total_deg = get_fine_times(p_id, fut_n)
                
                if entry_t and exit_t:
                    # અત્યારની રિયલ-ટાઇમ (Current) સ્થિતિ મેળવવા માટે
                    now_time = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                    curr_rasi, curr_r_deg, curr_nak, curr_pada, curr_n_deg, curr_total_deg = get_astro_position(p_id, now_time)

                    # ક્લીન અને પરફેક્ટ પ્રિન્ટ આઉટપુટ ફોર્મેટ (લાઈવ ડિગ્રીઓ સાથે)
                    msg = (f"<b>🌟 નવતારા એડવાન્સ એલર્ટ : {p_name}</b>\n\n"
                           f"આગામી ૧૨ કલાકમાં {p_name} <b>{fut_n}</b> નક્ષત્રમાં પ્રવેશ કરશે.\n\n"
                           f"• <b>કુલ નિરયણ ડિગ્રી:</b> {curr_total_deg:.2f}° ({format_dms(curr_total_deg)})\n"
                           f"• <b>વર્તમાન સ્થિતિ:</b> {curr_rasi} રાશિ (રાશિ ડિગ્રી: {format_dms(curr_r_deg)})\n"
                           f"• <b>વર્તમાન નક્ષત્ર સ્થિતિ:</b> {curr_nak} (નક્ષત્ર ડિગ્રી: {format_dms(curr_n_deg)})\n"
                           f"• <b>ભવિષ્યનું નવતારા નક્ષત્ર:</b> <b>{tara} ({fut_n})</b>\n"
                           f"• <b>નક્ષત્ર પ્રવેશ સમય:</b> {entry_t.strftime('%d %b, %H:%M')}\n"
                           f"• <b>નક્ષત્ર નિર્ગમન સમય:</b> {exit_t.strftime('%d %b, %H:%M')}")
                    
                    if TELEGRAM_TOKEN:
                        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={urllib.parse.quote(msg)}&parse_mode=HTML"
                        requests.get(url)
                    
                    create_calendar_event(f"નવતારા: {tara}", msg)
                    mark_alert_sent(alert_id)
                    print(f"✅ મોકલાયું: {alert_id}")
                    break

if __name__ == "__main__":
    run_tracker()