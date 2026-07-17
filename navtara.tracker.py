from datetime import datetime, timedelta
import swisseph as swe
import requests
import os
from googleapiclient.discovery import build
from google.oauth2 import service_account

# કોન્ફિગરેશન
SERVICE_ACCOUNT_FILE = 'credentials.json'
CALENDAR_ID = '12356pradip@gmail.com'
SCOPES = ['https://www.googleapis.com/auth/calendar']
LAT, LON = 22.2735, 70.7513
TELEGRAM_TOKEN = "8731134888:AAGHEul75rh6HZBefn7WCrbXUCyBqJ_zeXU"
TELEGRAM_CHAT_ID = "478006282"
HISTORY_FILE = "alert_history.txt"

NAVTARA_DATA = {
    "જન્મ તારા": ["ઉત્તરા ફાલ્ગુની", "ઉત્તરાષાઢા", "કૃતિકા"],
    "સંપત તારા": ["હસ્ત", "શ્રવણ", "રોહિણી"],
    "ક્ષેમ તારા": ["સ્વાતિ", "શતભિષા", "આર્દ્રા"],
    "સાધક તારા": ["અનુરાધા", "ઉત્તરાભાદ્રપદ", "પુષ્ય"],
    "મૈત્રી તારા": ["મૂળ", "અશ્વિની", "મઘા"],
    "અતિ મૈત્રી તારા": ["પૂર્વાષાઢા", "ભરણી", "પૂર્વા ફાલ્ગુની"]
}

def create_calendar_event(summary, description):
    try:
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('calendar', 'v3', credentials=creds)
        event = {
            'summary': summary,
            'description': description,
            'start': {'dateTime': datetime.utcnow().isoformat() + 'Z'},
            'end': {'dateTime': (datetime.utcnow() + timedelta(hours=1)).isoformat() + 'Z'},
        }
        service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        return True
    except Exception as e:
        print(f"❌ કેલેન્ડર એરર: {e}")
        return False

def get_dms(deg):
    d = int(deg); m = int((deg - d) * 60); s = int((((deg - d) * 60) - m) * 60)
    return f"{d}°{m}'{s}\""

def get_planet_data(planet_id, time):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(time.year, time.month, time.day, time.hour + time.minute/60.0 + 5.5)
    swe.set_topo(LON, LAT, 0)
    data = swe.calc_ut(jd, planet_id, swe.FLG_SIDEREAL | swe.FLG_TOPOCTR)[0][0]
    if planet_id == 1: data = (data - 2.9) % 360
    rashis = ["મેષ", "વૃષભ", "મિથુન", "કર્ક", "સિંહ", "કન્યા", "તુલા", "વૃશ્ચિક", "ધન", "મકર", "કુંભ", "મીન"]
    rashi = rashis[int(data // 30)]
    degree_in_rashi = data % 30
    naks = ["અશ્વિની", "ભરણી", "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફાલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", "મૂળ", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદ", "ઉત્તરા ભાદ્રપદ", "રેવતી"]
    nak = naks[int(data // 13.333333333333334) % 27]
    return rashi, nak, get_dms(degree_in_rashi)

def get_transition_times(planet_id):
    start = datetime.utcnow()
    current_n = get_planet_data(planet_id, start)[1]
    entry, exit_time = None, None
    for i in range(0, 48 * 60, 1):
        t = start + timedelta(minutes=i)
        if get_planet_data(planet_id, t)[1] != current_n:
            exit_time = t + timedelta(hours=5, minutes=30)
            break
    for i in range(0, -48 * 60, -1):
        t = start + timedelta(minutes=i)
        if get_planet_data(planet_id, t)[1] != current_n:
            entry = t + timedelta(hours=5, minutes=30)
            break
    return entry, exit_time

def is_alert_sent(alert_id):
    if not os.path.exists(HISTORY_FILE): return False
    with open(HISTORY_FILE, "r") as f: return alert_id in f.read().splitlines()

def mark_alert_sent(alert_id):
    with open(HISTORY_FILE, "a") as f: f.write(alert_id + "\n")

def run_tracker():
    planets = {0: "સૂર્ય", 1: "ચંદ્ર"}
    now = datetime.utcnow()
    future_time = now + timedelta(hours=12)
    for p_id, p_name in planets.items():
        cur_rashi, cur_nak, cur_deg = get_planet_data(p_id, now)
        fut_rashi, fut_nak, fut_deg = get_planet_data(p_id, future_time)
        for tara, naks in NAVTARA_DATA.items():
            if fut_nak in naks:
                alert_id = f"{p_name}_{fut_nak}_{datetime.now().strftime('%Y%m%d_%H')}"
                if is_alert_sent(alert_id): continue
                entry, exit_t = get_transition_times(p_id)
                msg = (f"🌟 {p_name} 12 કલાક એડવાન્સ એલર્ટ: {tara}\n"
                       f"---------------------------\n"
                       f"વર્તમાન સ્થિતિ: {cur_rashi}, {cur_nak} ({cur_deg})\n"
                       f"ભવિષ્યનું નક્ષત્ર: {fut_nak}\n"
                       f"પ્રવેશ: {entry.strftime('%H:%M, %d %b') if entry else 'N/A'}\n"
                       f"નિર્ગમન: {exit_t.strftime('%H:%M, %d %b') if exit_t else 'N/A'}")
                requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={msg}")
                create_calendar_event(f"નવતારા: {tara}", msg)
                mark_alert_sent(alert_id)
                print(msg)
                print(f"✅ એલર્ટ અને કેલેન્ડર ઇવેન્ટ મોકલાઈ: {alert_id}")
                break

if __name__ == "__main__":
    run_tracker()
