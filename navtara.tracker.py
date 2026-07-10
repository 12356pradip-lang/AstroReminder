from datetime import datetime, timedelta, timezone
import swisseph as swe
import requests
from googleapiclient.discovery import build
from google.oauth2 import service_account

# કોન્ફિગરેશન
SERVICE_ACCOUNT_FILE = 'credentials.json'
CALENDAR_ID = '12356pradip@gmail.com'
SCOPES = ['https://www.googleapis.com/auth/calendar']
LAT, LON = 22.2735, 70.7513
TELEGRAM_TOKEN = "8731134888:AAGHEul75rh6HZBefn7WCrbXUCyBqJ_zeXU"
TELEGRAM_CHAT_ID = "478006282"

NAVTARA_DATA = {
    "જન્મ તારા": ["ઉત્તરા ફાલ્ગુની", "ઉત્તરાષાઢા", "કૃતિકા"],
    "સંપત તારા": ["હસ્ત", "શ્રવણ", "રોહિણી"],
    "ક્ષેમ તારા": ["સ્વાતિ", "શતભિષા", "આર્દ્રા"],
    "સાધક તારા": ["અનુરાધા", "ઉત્તરાભાદ્રપદ", "પુષ્ય"],
    "મૈત્રી તારા": ["મૂળ", "અશ્વિની", "મઘા"],
    "અતિ મૈત્રી તારા": ["પૂર્વાષાઢા", "ભરણી", "પૂર્વા ફાલ્ગુની"]
}

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={text}"
    requests.get(url)

def create_calendar_event(summary, description):
    try:
        ist = timezone(timedelta(hours=5, minutes=30))
        start_time = datetime.now(ist)
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('calendar', 'v3', credentials=creds)
        event = {
            'summary': summary, 'description': description,
            'start': {'dateTime': start_time.isoformat()},
            'end': {'dateTime': (start_time + timedelta(hours=1)).isoformat()},
        }
        service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    except Exception as e:
        print(f"❌ કેલેન્ડર એરર: {e}")

def get_nakshatra(planet_id, time):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(time.year, time.month, time.day, time.hour + time.minute/60.0 + 5.5)
    swe.set_topo(LON, LAT, 0)
    data = swe.calc_ut(jd, planet_id, swe.FLG_SIDEREAL | swe.FLG_TOPOCTR)[0][0]
    if planet_id == 1: data = (data - 2.9) % 360 # ચંદ્ર ઓફસેટ
    
    naks = ["અશ્વિની", "ભરણી", "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફાલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", "મૂળ", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદ", "ઉત્તરા ભાદ્રપદ", "રેવતી"]
    return naks[int(data // 13.333333333333334) % 27]

def get_transition_times(planet_id):
    start = datetime.utcnow()
    current_n = get_nakshatra(planet_id, start)
    entry, exit_time = None, None
    
    # પ્રવેશ સમય શોધવો
    for i in range(0, 24 * 60, 10):
        t = start + timedelta(minutes=i)
        if get_nakshatra(planet_id, t) != current_n:
            exit_time = t + timedelta(hours=5, minutes=30)
            break
    
    # નિર્ગમન સમય માટે પાછળ તપાસવું
    for i in range(0, -24 * 60, -10):
        t = start + timedelta(minutes=i)
        if get_nakshatra(planet_id, t) != current_n:
            entry = t + timedelta(hours=5, minutes=30)
            break
    return entry, exit_time

def run_tracker():
    def run_tracker():
    planets = {0: "સૂર્ય", 1: "ચંદ્ર"}
    
    # 12 કલાક પછીનો સમય નક્કી કરો
    future_time = datetime.utcnow() + timedelta(hours=12)
    
    for p_id, p_name in planets.items():
        # અહીં 'future_time' નો ઉપયોગ કરો જેથી 12 કલાક પછીનું નક્ષત્ર ચેક થાય
        fut_n = get_nakshatra(p_id, future_time)
        
        # ચેક કરવું કે શું આ ભવિષ્યનું નક્ષત્ર નવતારા લિસ્ટમાં છે
        for tara, naks in NAVTARA_DATA.items():
            if fut_n in naks:
                # પ્રવેશ અને નિર્ગમન સમય તે જ રીતે મળશે
                entry, exit_t = get_transition_times(p_id) 
                
                msg = f"🌟 {p_name} 12 કલાક એડવાન્સ એલર્ટ: {tara}\nનક્ષત્ર: {fut_n}\nપ્રવેશ: {entry.strftime('%H:%M, %d %b') if entry else 'N/A'}\nનિર્ગમન: {exit_t.strftime('%H:%M, %d %b') if exit_t else 'N/A'}"
                
                create_calendar_event(f"નવતારા: {tara}", msg)
                send_telegram_msg(msg)
                print(f"✅ 12 કલાક એડવાન્સ એલર્ટ મોકલાયું: {msg}")

if __name__ == "__main__":
    run_tracker()