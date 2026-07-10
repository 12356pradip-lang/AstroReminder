from datetime import datetime, timedelta
import swisseph as swe
import requests  # નવું ઈમ્પોર્ટ
from googleapiclient.discovery import build
from google.oauth2 import service_account

SERVICE_ACCOUNT_FILE = 'credentials.json'
CALENDAR_ID = '12356pradip@gmail.com'
SCOPES = ['https://www.googleapis.com/auth/calendar']
TELEGRAM_TOKEN = "8731134888:AAGHEul75rh6HZBefn7WCrbXUCyBqJ_zeXU"
TELEGRAM_CHAT_ID = "478006282"
LAT, LON = 22.2735, 70.7513
CHANDRA_OFFSET = -2.9

# (PUSHKAR_DATA અને અન્ય ફંક્શન્સ યથાવત છે...)
PUSHKAR_DATA = [
    {"nakshatra": "કૃતિકા", "pada": 3, "navamsha": "મીન", "mul_tatva": "અગ્નિ", "nav_tatva": "જળ", "pradhan_tatva": "જળ"},
    {"nakshatra": "ઉત્તરાફાલ્ગુની", "pada": 4, "navamsha": "મીન", "mul_tatva": "અગ્નિ", "nav_tatva": "જળ", "pradhan_tatva": "જળ"},
    {"nakshatra": "ઉત્તરાષાઢા", "pada": 4, "navamsha": "મીન", "mul_tatva": "અગ્નિ", "nav_tatva": "જળ", "pradhan_tatva": "જળ"},
    {"nakshatra": "રોહિણી", "pada": 1, "navamsha": "વૃષભ", "mul_tatva": "પૃથ્વી", "nav_tatva": "પૃથ્વી", "pradhan_tatva": "પૃથ્વી"},
    {"nakshatra": "હસ્ત", "pada": 2, "navamsha": "વૃષભ", "mul_tatva": "પૃથ્વી", "nav_tatva": "પૃથ્વી", "pradhan_tatva": "પૃથ્વી"},
    {"nakshatra": "શ્રવણ", "pada": 2, "navamsha": "વૃષભ", "mul_tatva": "પૃથ્વી", "nav_tatva": "પૃથ્વી", "pradhan_tatva": "પૃથ્વી"},
    {"nakshatra": "પુનર્વસુ", "pada": 4, "navamsha": "કર્ક", "mul_tatva": "જળ/વાયુ", "nav_tatva": "જળ", "pradhan_tatva": "જળ"},
    {"nakshatra": "વિશાખા", "pada": 1, "navamsha": "કર્ક", "mul_tatva": "અગ્નિ", "nav_tatva": "જળ", "pradhan_tatva": "જળ-અગ્નિ મિશ્રિત"},
    {"nakshatra": "પૂર્વાભાદ્રપદ", "pada": 1, "navamsha": "કર્ક", "mul_tatva": "અગ્નિ", "nav_tatva": "જળ", "pradhan_tatva": "જળ-અગ્નિ મિશ્રિત"},
    {"nakshatra": "પુષ્ય", "pada": 2, "navamsha": "કન્યા", "mul_tatva": "પૃથ્વી", "nav_tatva": "પૃથ્વી", "pradhan_tatva": "પૃથ્વી"},
    {"nakshatra": "અનુરાધા", "pada": 3, "navamsha": "કન્યા", "mul_tatva": "જળ", "nav_tatva": "પૃથ્વી", "pradhan_tatva": "પૃથ્વી-જળ મિશ્રિત"},
    {"nakshatra": "ઉત્તરાભાદ્રપદ", "pada": 3, "navamsha": "કન્યા", "mul_tatva": "જળ", "nav_tatva": "પૃથ્વી", "pradhan_tatva": "પૃથ્વી-જળ મિશ્રિત"},
    {"nakshatra": "સાર્દ", "pada": 4, "navamsha": "મીન", "mul_tatva": "વાયુ", "nav_tatva": "જળ", "pradhan_tatva": "જળ-વાયુ મિશ્રિત"},
    {"nakshatra": "સ્વાતિ", "pada": 1, "navamsha": "મીન", "mul_tatva": "વાયુ", "nav_tatva": "જળ", "pradhan_tatva": "જળ-વાયુ મિશ્રિત"},
    {"nakshatra": "શતભિષા", "pada": 1, "navamsha": "મીન", "mul_tatva": "વાયુ", "nav_tatva": "જળ", "pradhan_tatva": "જળ-વાયુ મિશ્રિત"},
    {"nakshatra": "પુનર્વસુ", "pada": 2, "navamsha": "વૃષભ", "mul_tatva": "જળ/વાયુ", "nav_tatva": "પૃથ્વી", "pradhan_tatva": "પૃથ્વી-વાયુ મિશ્રિત"},
    {"nakshatra": "વિશાખા", "pada": 3, "navamsha": "વૃષભ", "mul_tatva": "અગ્નિ/વાયુ", "nav_tatva": "પૃથ્વી", "pradhan_tatva": "પૃથ્વી-વાયુ મિશ્રિત"},
    {"nakshatra": "પૂર્વાભાદ્રપદ", "pada": 3, "navamsha": "વૃષભ", "mul_tatva": "અગ્નિ/વાયુ", "nav_tatva": "પૃથ્વી", "pradhan_tatva": "પૃથ્વી-વાયુ મિશ્રિત"},
    {"nakshatra": "ભરણી", "pada": 3, "navamsha": "તુલા", "mul_tatva": "પૃથ્વી", "nav_tatva": "વાયુ", "pradhan_tatva": "વાયુ-પૃથ્વી મિશ્રિત"},
    {"nakshatra": "પૂર્વાફાલ્ગુની", "pada": 4, "navamsha": "તુલા", "mul_tatva": "જળ", "nav_tatva": "વાયુ", "pradhan_tatva": "વાયુ-જળ મિશ્રિત"},
    {"nakshatra": "પૂર્વાષાઢા", "pada": 4, "navamsha": "તુલા", "mul_tatva": "જળ", "nav_tatva": "વાયુ", "pradhan_tatva": "વાયુ-જળ મિશ્રિત"},
    {"nakshatra": "કૃતિકા", "pada": 1, "navamsha": "ધનુ", "mul_tatva": "અગ્નિ", "nav_tatva": "અગ્નિ", "pradhan_tatva": "અગ્નિ"},
    {"nakshatra": "ઉત્તરાફાલ્ગુની", "pada": 2, "navamsha": "ધનુ", "mul_tatva": "અગ્નિ", "nav_tatva": "અગ્નિ", "pradhan_tatva": "અગ્નિ"},
    {"nakshatra": "ઉત્તરાષાઢા", "pada": 2, "navamsha": "ધનુ", "mul_tatva": "અગ્નિ", "nav_tatva": "અગ્નિ", "pradhan_tatva": "અગ્નિ"}
]

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={text}"
    requests.get(url)

# (format_dms, get_rasi_name, get_astro_position... બધું એમ જ રાખ્યું છે)
def format_dms(deg):
    d = int(deg); m = int((deg - d) * 60); s = int(((deg - d) * 60 - m) * 60)
    return f"{d}°{m}'{s}\""

def get_rasi_name(longitude):
    rasis = ["મેષ", "વૃષભ", "મિથુન", "કર્ક", "સિંહ", "કન્યા", "તુલા", "વૃશ્ચિક", "ધન", "મકર", "કુંભ", "મીન"]
    return rasis[int(longitude // 30)]

def get_astro_position(planet_id, target_time):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(target_time.year, target_time.month, target_time.day, 
                    target_time.hour + (target_time.minute / 60.0) + (target_time.second / 3600.0) + 5.5)
    swe.set_topo(70.8022, 22.3039, 0)
    data = swe.calc_ut(jd, planet_id, swe.FLG_SIDEREAL | swe.FLG_TOPOCTR | swe.FLG_SWIEPH)[0][0]
    if planet_id == 1: data = (data + CHANDRA_OFFSET) % 360
    
    nakshatras = ["અશ્વિની", "ભરણી", "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફાલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", "મૂલા", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદા", "ઉત્તરા ભાદ્રપદા", "રેવતી"]
    nak_idx = int(data // 13.333333333333334)
    pada = int((data % 13.333333333333334) // 3.3333333333333335) + 1
    return nakshatras[nak_idx % 27], pada, data, data % 30, data % 13.333333333333334

def create_calendar_event(summary, description):
    try:
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('calendar', 'v3', credentials=creds)
        event = {
            'summary': summary, 'description': description,
            'start': {'dateTime': datetime.utcnow().isoformat() + 'Z'},
            'end': {'dateTime': (datetime.utcnow() + timedelta(hours=1)).isoformat() + 'Z'},
        }
        service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        print(f"✅ ઇવેન્ટ બની: {summary}")
    except Exception as e:
        print(f"❌ કેલેન્ડર એરર: {e}")

def run_pre_alert():
    look_ahead = {0: 6, 1: 6}
    for p_id, hours in look_ahead.items():
        name = "સૂર્ય" if p_id == 0 else "ચંદ્ર"
        curr_nak, curr_pada, curr_long, curr_rasi_deg, curr_nak_deg = get_astro_position(p_id, datetime.utcnow())
        future_time = datetime.utcnow() + timedelta(hours=hours)
        fut_nak, fut_pada, _, _, _ = get_astro_position(p_id, future_time)
        entry = next((item for item in PUSHKAR_DATA if item["nakshatra"] == fut_nak and item["pada"] == fut_pada), None)
        
        if entry:
            msg = f"એલર્ટ: {name} આગામી {hours} કલાકમાં પુષ્કર નવમાંશમાં આવશે.\nનક્ષત્ર: {fut_nak} ({fut_pada} પદ)\nનવમાંશ: {entry['navamsha']}\nપ્રધાન તત્વ: {entry['pradhan_tatva']}"
            create_calendar_event(f"પુષ્કર એડવાન્સ: {name}", msg)
            send_telegram_msg(msg) # અહીં ટેલિગ્રામ મેસેજ મોકલવામાં આવશે
            print(f"✅ {name} એલર્ટ મોકલાયું!")

if __name__ == "__main__":
    run_pre_alert()