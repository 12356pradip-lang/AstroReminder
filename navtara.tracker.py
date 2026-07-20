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
    "સાધક તારા": ["અનુરાધા", "ઉત્તરાભાદ્રપદ", "પુષ્ય"],
    "મૈત્રી તારા": ["મૂળ", "અશ્વિની", "મઘા"],
    "અતિ મૈત્રી તારા": ["પૂર્વાષાઢા", "ભરણી", "પૂર્વા ફાલ્ગુની"]
}

def create_calendar_event(summary, description):
    print(f"DEBUG: '{summary}' માટે કેલેન્ડર ઇવેન્ટ બનાવવાનું શરૂ થયું છે...")
    
    # જો ફાઈલ ન મળે તો પ્રોગ્રામ બંધ ન કરો, ફક્ત એરર પ્રિન્ટ કરો જેથી ખબર પડે
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"❌ ERROR: '{SERVICE_ACCOUNT_FILE}' ફાઈલ મળી નથી.")
        return False
    
    try:
        # ક્રેડેન્શિયલ લોડિંગ
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('calendar', 'v3', credentials=creds)
        
        # સમયની ગણતરી
        now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        event = {
            'summary': summary,
            'description': description,
            'start': {'dateTime': now.isoformat()},
            'end': {'dateTime': (now + timedelta(hours=1)).isoformat()},
        }
        
        # API કોલ
        print("DEBUG: API રિક્વેસ્ટ મોકલી રહ્યા છીએ...")
        result = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        
        print(f"✅ સફળ: કેલેન્ડર ઇવેન્ટ બની ગઈ! ID: {result.get('id')}")
        return True
        
    except Exception as e:
        # આ લાઇન સૌથી મહત્વની છે, તે એરરનું કારણ બતાવશે
        print(f"❌ કેલેન્ડર એરરની વિગત: {str(e)}")
        return False

def is_alert_sent(alert_id):
    if not os.path.exists(HISTORY_FILE): return False
    with open(HISTORY_FILE, "r") as f: return alert_id in f.read().splitlines()

def mark_alert_sent(alert_id):
    with open(HISTORY_FILE, "a") as f: f.write(alert_id + "\n")

def get_nakshatra(planet_id, target_time):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(target_time.year, target_time.month, target_time.day, 
                    target_time.hour + (target_time.minute / 60.0) + (target_time.second / 3600.0) + 5.5)
    swe.set_topo(LON, LAT, 0)
    data = swe.calc_ut(jd, planet_id, swe.FLG_SIDEREAL | swe.FLG_TOPOCTR | swe.FLG_SWIEPH)[0][0]
    nak_idx = int(data // 13.333333333333334)
    nakshatras = ["અશ્વિની", "ભરણી", "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફાલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", "મૂળ", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદ", "ઉત્તરા ભાદ્રપદ", "રેવતી"]
    return nakshatras[nak_idx % 27]

def get_fine_times(planet_id, target_nak):
    search_hours = 360 if planet_id == 0 else 72
    # ગણતરી માટે આજના દિવસની શરૂઆતનો સમય (IST)
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=5, minutes=30)
    
    for i in range(0, search_hours * 60, 60):
        t_check = start + timedelta(minutes=i)
        if get_nakshatra(planet_id, t_check) == target_nak:
            for j in range(max(0, i-60), i + 120):
                t_fine = start + timedelta(minutes=j)
                if get_nakshatra(planet_id, t_fine) == target_nak:
                    entry = t_fine
                    # નિર્ગમન શોધવા માટે લૂપ
                    for k in range(j, j + search_hours * 60):
                        t_exit = start + timedelta(minutes=k)
                        if get_nakshatra(planet_id, t_exit) != target_nak:
                            return entry.strftime("%d %b %H:%M"), t_exit.strftime("%d %b %H:%M")
    
    return "N/A", "N/A"

def run_tracker():
    planets = {0: "સૂર્ય", 1: "ચંદ્ર"}
    future_time = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30) + timedelta(hours=12)
    # ડુપ્લીકેશન રોકવા માટે કલાકને બદલે માત્ર તારીખનો ઉપયોગ
    current_date_id = (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)).strftime('%Y%m%d')

    for p_id, p_name in planets.items():
        fut_n = get_nakshatra(p_id, future_time)
        print(f"DEBUG: અત્યારે {p_name} નું નક્ષત્ર {fut_n} છે.") # આ લાઈન ઉમેરો
        
        for tara, naks in NAVTARA_DATA.items():
            if fut_n in naks:
                # યુનિક આઈડીમાં તારીખનો ઉપયોગ
                alert_id = f"{p_name}_{fut_n}_{current_date_id}"
                if is_alert_sent(alert_id): continue
                
                entry, exit_t = get_fine_times(p_id, fut_n)
                msg = (f"🌟 {p_name} 12 કલાક એડવાન્સ એલર્ટ: {tara}\n"
                       f"નક્ષત્ર: {fut_n}\n"
                       f"પ્રવેશ: {entry}\n"
                       f"નિર્ગમન: {exit_t}")
                
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={urllib.parse.quote(msg)}"
                requests.get(url)
                create_calendar_event(f"નવતારા: {tara}", msg)
                mark_alert_sent(alert_id)
                print(f"✅ એલર્ટ મોકલાયું: {alert_id}")
                break

if __name__ == "__main__":
    run_tracker()