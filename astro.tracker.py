from datetime import datetime, timedelta
import swisseph as swe
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Google Calendar Setup
SERVICE_ACCOUNT_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/calendar']

# અહી સેટિંગ છે - જો 4.0 થી કામ ન થાય તો આને બદલી શકાય
CHANDRA_OFFSET = -3.3 

PUSHKAR_DATA = [
    {"nakshatra": "કૃતિકા", "pada": 3, "navansh_rashi": "મીન"}, {"nakshatra": "રોહિણી", "pada": 1, "navansh_rashi": "વૃષભ"},
    {"nakshatra": "પુનર્વસુ", "pada": 4, "navansh_rashi": "કર્ક"}, {"nakshatra": "પુષ્ય", "pada": 2, "navansh_rashi": "કન્યા"},
    {"nakshatra": "આર્દ્રા", "pada": 4, "navansh_rashi": "મીન"}, {"nakshatra": "ઉત્તરા ફાલ્ગુની", "pada": 4, "navansh_rashi": "મીન"},
    {"nakshatra": "હસ્ત", "pada": 2, "navansh_rashi": "વૃષભ"}, {"nakshatra": "સ્વાતિ", "pada": 1, "navansh_rashi": "મીન"},
    {"nakshatra": "અનુરાધા", "pada": 3, "navansh_rashi": "કન્યા"}, {"nakshatra": "શ્રવણ", "pada": 2, "navansh_rashi": "વૃષભ"},
    {"nakshatra": "શતભિષા", "pada": 1, "navansh_rashi": "મીન"}, {"nakshatra": "ઉત્તરાષાઢા", "pada": 4, "navansh_rashi": "મીન"}
]

def create_calendar_event(summary, description):
    try:
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('calendar', 'v3', credentials=creds)
        event = {
            'summary': summary, 'description': description,
            'start': {'dateTime': datetime.utcnow().isoformat() + 'Z'},
            'end': {'dateTime': (datetime.utcnow() + timedelta(hours=1)).isoformat() + 'Z'},
        }
        service.events().insert(calendarId='primary', body=event).execute()
    except Exception as e:
        print(f"❌ કેલેન્ડર એરર: {e}")

def get_full_astro_details(planet_id):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    now = datetime.utcnow()
    jd = swe.julday(now.year, now.month, now.day, now.hour + (now.minute / 60.0) + (now.second / 3600.0) + 5.5)
    swe.set_topo(70.8022, 22.3039, 0)
    
    flags = swe.FLG_SIDEREAL | swe.FLG_TOPOCTR | swe.FLG_SWIEPH
    data = swe.calc_ut(jd, planet_id, flags)[0][0]
    
    # ચંદ્ર માટે કરેક્શન: ફાઇનલ પોઝિશન પર એપ્લાય કરવું
    if planet_id == 1:
        data = (data + CHANDRA_OFFSET) % 360
    
    rashi_idx = int(data // 30)
    rashi_rem = data % 30
    deg = int(rashi_rem)
    minutes = int((rashi_rem - deg) * 60)
    seconds = int((((rashi_rem - deg) * 60) - minutes) * 60)
    
    nak_pos = data % 13.333333333333334
    nak_idx = int(data // 13.333333333333334)
    pada = int(nak_pos // 3.3333333333333335) + 1
    
    rashis = ["મેષ", "વૃષભ", "મિથુન", "કર્ક", "સિંહ", "કન્યા", "તુલા", "વૃશ્ચિક", "ધન", "મકર", "કુંભ", "મીન"]
    nakshatras = ["અશ્વિની", "ભરણી", "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફાલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", "મૂલા", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદા", "ઉત્તરા ભાદ્રપદા", "રેવતી"]
    
    info = f"{rashis[rashi_idx]} રાશિ ({deg}° {minutes}' {seconds}\")"
    return info, nakshatras[nak_idx], pada

def run_pre_alert():
    planets = [("સૂર્ય", 0), ("ચંદ્ર", 1)]
    print("--- દ્રિક પંચાંગ સચોટ ગણતરી ---")
    for name, p_id in planets:
        info, nak, pada = get_full_astro_details(p_id)
        print(f"{name}: {info} | નક્ષત્ર: {nak} (પદ {pada})")
        
        for entry in PUSHKAR_DATA:
            if entry["nakshatra"] == nak and entry["pada"] == pada:
                print(f"✅ મેચ મળ્યું: {name} | {nak} | પદ {pada}")
                desc = f"{name} સ્થિતિ: {info}\nનક્ષત્ર: {nak} (પદ {pada})"
                create_calendar_event(f"પુષ્કર નવમાંશ: {name}", desc)

if __name__ == "__main__":
    run_pre_alert()