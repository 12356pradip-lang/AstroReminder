import swisseph as swe
from datetime import datetime, timedelta, timezone
import os
import requests
from googleapiclient.discovery import build
from google.oauth2 import service_account

# કોન્ફિગરેશન
TELEGRAM_TOKEN = "8731134888:AAGHEul75rh6HZBefn7WCrbXUCyBqJ_zeXU"
TELEGRAM_CHAT_ID = "478006282"
SERVICE_ACCOUNT_FILE = 'credentials.json'
CALENDAR_ID = '12356pradip@gmail.com'
SCOPES = ['https://www.googleapis.com/auth/calendar']
LAT, LON = 22.2735, 70.7513
HISTORY_FILE = "pushkar_specials_history.txt"

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

def format_dms(deg):
    d = int(deg); m = int((deg - d) * 60); s = int(((deg - d) * 60 - m) * 60)
    return f"{d}°{m}'{s}\""

def get_astro_position(planet_id, target_time):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(target_time.year, target_time.month, target_time.day, target_time.hour + target_time.minute/60.0 + target_time.second/3600.0 + 5.5)
    swe.set_topo(LON, LAT, 0)
    data = swe.calc_ut(jd, planet_id, swe.FLG_SIDEREAL | swe.FLG_TOPOCTR | swe.FLG_SWIEPH)[0][0]
    if planet_id == 1: data = (data - 2.9) % 360
    
    rasi_idx = int(data // 30)
    rasi_name = ["મેષ", "વૃષભ", "મિથુન", "કર્ક", "સિંહ", "કન્યા", "તુલા", "વૃશ્ચિક", "ધન", "મકર", "કુંભ", "મીન"][rasi_idx]
    
    nakshatras = ["અશ્વિની", "ભરણી", "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફાલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", "મૂળ", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદ", "ઉત્તરા ભાદ્રપદ", "રેવતી"]
    nak_name = nakshatras[int(data // 13.333333333333334) % 27]
    
    return rasi_name, data % 30, nak_name

def get_fine_times(planet_id, target_nak):
    now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    
    if planet_id == 0:  # સૂર્ય માટે (લાંબો સમય નક્ષત્રમાં રહે છે)
        start_search = now - timedelta(days=15)
        entry = None
        entry_data = None
        for i in range(0, 15 * 24 + 48, 1):
            t_check = start_search + timedelta(hours=i)
            rasi, deg, nak = get_astro_position(planet_id, t_check)
            if nak == target_nak:
                entry = t_check
                entry_data = (rasi, deg)
                break
        
        if not entry:
            return None, None, None, None

        t_exit = entry + timedelta(days=1)
        for _ in range(30 * 24):
            rasi_e, deg_e, nak_e = get_astro_position(planet_id, t_exit)
            if nak_e != target_nak:
                break
            t_exit += timedelta(hours=1)
        return entry, t_exit, entry_data[0], entry_data[1]

    else:  # ચંદ્ર માટે (ઝડપી ભ્રમણ - મિનિટ-વાઈઝ પરફેક્ટ સ્કેન)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        entry = None
        entry_data = None
        for i in range(0, 72 * 60):  
            t_check = start + timedelta(minutes=i)
            rasi, deg, nak = get_astro_position(planet_id, t_check)
            if nak == target_nak:
                entry = t_check
                entry_data = (rasi, deg)
                break
                
        if entry:
            for k in range(1, 72 * 60):
                t_exit = entry + timedelta(minutes=k)
                rasi_e, deg_e, nak_e = get_astro_position(planet_id, t_exit)
                if nak_e != target_nak:
                    return entry, t_exit, entry_data[0], entry_data[1]
                    
        return None, None, None, None

def run_tracker():
    target_naks = ["આશ્લેષા", "મઘા", "જ્યેષ્ઠა", "ઉત્તરા ભાદ્રપદ", "રેવતી"]
    future_time = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30) + timedelta(hours=12)

    for p_id in [0, 1]:
        name = "સૂર્ય" if p_id == 0 else "ચંદ્ર"
        fut_rasi, _, fut_n = get_astro_position(p_id, future_time)

        if fut_n in target_naks:
            entry_t, exit_t, rasi, deg = get_fine_times(p_id, fut_n)
            
            if entry_t and exit_t:
                # સૂર્ય માટે સમય/મિનિટ કાઢીને માત્ર તારીખ રાખવી, ચંદ્ર માટે મિનિટ કાઢીને કલાક સુધીનું રાખવું જેથી ડુપ્લિકેટ ન બને
                if p_id == 0:
                    alert_id = f"{fut_n}_{name}_{exit_t.strftime('%Y%m%d')}"
                else:
                    alert_id = f"{fut_n}_{name}_{entry_t.strftime('%Y%m%d_%H')}"
                
                already_sent = False
                if os.path.exists(HISTORY_FILE):
                    with open(HISTORY_FILE, "r") as f:
                        if alert_id in f.read(): already_sent = True
                
                if not already_sent:
                    msg = (f"🌟 એડવાન્સ એલર્ટ: {fut_n} - {name}\n"
                           f"આગામી ૧૨ કલાકમાં {name} આ નક્ષત્રમાં પ્રવેશ કરશે.\n"
                           f"પ્રવેશ સમય: {entry_t.strftime('%d %b, %H:%M')}\n"
                           f"પ્રવેશ સ્થિતિ: {rasi} રાશિમાં {format_dms(deg)}\n"
                           f"નિર્ગમન સમય: {exit_t.strftime('%d %b, %H:%M')}")
                    
                    if TELEGRAM_TOKEN:
                        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={msg}")
                    create_calendar_event(f"નવતારા: {fut_n}", msg)
                    
                    with open(HISTORY_FILE, "a") as f: f.write(alert_id + "\n")
                    print(f"✅ મોકલાયું: {alert_id}")

if __name__ == "__main__":
    run_tracker()