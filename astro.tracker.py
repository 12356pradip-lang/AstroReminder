from datetime import datetime, timedelta
import swisseph as swe
from googleapiclient.discovery import build
from google.oauth2 import service_account

SERVICE_ACCOUNT_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/calendar']

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
        calendar_list = service.calendarList().list().execute()
        for cal in calendar_list.get('items', []):
            print(f"કેલેન્ડર મળ્યું: {cal['summary']} - ID: {cal['id']}")
        event = {
            'summary': summary, 'description': description,
            'start': {'dateTime': datetime.utcnow().isoformat() + 'Z'},
            'end': {'dateTime': (datetime.utcnow() + timedelta(hours=1)).isoformat() + 'Z'},
        }
        service.events().insert(calendarId='12356pradip@gmail.com', body=event).execute()
        print(f"DEBUG: ઇવેન્ટ '{summary}' આ કેલેન્ડરમાં મોકલાઈ છે: primary")
        print(f"✅ ઇવેન્ટ બની: {summary}")
    except Exception as e:
        print(f"❌ કેલેન્ડર એરર: {e}")

def get_astro_position(planet_id, target_time):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(target_time.year, target_time.month, target_time.day, 
                    target_time.hour + (target_time.minute / 60.0) + (target_time.second / 3600.0) + 5.5)
    swe.set_topo(70.8022, 22.3039, 0)
    
    flags = swe.FLG_SIDEREAL | swe.FLG_TOPOCTR | swe.FLG_SWIEPH
    data = swe.calc_ut(jd, planet_id, flags)[0][0]
    
    if planet_id == 1:
        data = (data + CHANDRA_OFFSET) % 360
    
    nak_idx = int(data // 13.333333333333334)
    nak_pos = data % 13.333333333333334
    pada = int(nak_pos // 3.3333333333333335) + 1
    
    nakshatras = ["અશ્વિની", "ભરણી", "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફાલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", "મૂલા", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદા", "ઉત્તરા ભાદ્રપદા", "રેવતી"]
    return nakshatras[nak_idx], pada

def run_pre_alert():
    # સેટિંગ: સૂર્ય(0) માટે 7 કલાક, ચંદ્ર(1) માટે 2 કલાક
    look_ahead = {0: 7, 1: 2}
    print("--- એડવાન્સ પુષ્કર એલર્ટ ચેક શરૂ ---")
    
    for p_id, hours in look_ahead.items():
        name = "સૂર્ય" if p_id == 0 else "ચંદ્ર"
        future_time = datetime.utcnow() + timedelta(hours=hours)
        nak, pada = get_astro_position(p_id, future_time)
        
        for entry in PUSHKAR_DATA:
            if entry["nakshatra"] == nak and entry["pada"] == pada:
                msg = f"એલર્ટ: {name} આગામી {hours} કલાકમાં પુષ્કર નવમાંશમાં આવશે.\nનક્ષત્ર: {nak} (પદ {pada})"
                print(f"✅ {msg}")
                create_calendar_event(f"પુષ્કર એડવાન્સ એલર્ટ: {name}", msg)

if __name__ == "__main__":
    run_pre_alert()