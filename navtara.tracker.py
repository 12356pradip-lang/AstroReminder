from datetime import datetime, timedelta
import swisseph as swe
from googleapiclient.discovery import build
from google.oauth2 import service_account

# કોન્ફિગરેશન
SERVICE_ACCOUNT_FILE = 'credentials.json'
CALENDAR_ID = '12356pradip@gmail.com'
SCOPES = ['https://www.googleapis.com/auth/calendar']
LAT, LON = 22.2735, 70.7513  # રાજકોટનું લોકેશન
MOON_OFFSET = -4.7 # તમારા અવલોકન મુજબનો તફાવત

NAVTARA_DATA = {
    "જન્મ તારા": {"naks": ["ઉત્તરા ફાલ્ગુની", "ઉત્તરાષાઢા", "કૃતિકા"], "swami": "સૂર્ય"},
    "સંપત તારા": {"naks": ["હસ્ત", "શ્રવણ", "રોહિણી"], "swami": "ચંદ્ર"},
    "ક્ષેમ તારા": {"naks": ["સ્વાતિ", "શતભિષા", "આર્દ્રા"], "swami": "રાહુ"},
    "સાધક તારા": {"naks": ["અનુરાધા", "ઉત્તરાભાદ્રપદ", "પુષ્ય"], "swami": "શનિ"},
    "મૈત્રી તારા": {"naks": ["મૂળ", "અશ્વિની", "મઘા"], "swami": "કેતુ"},
    "અતિ મૈત્રી તારા": {"naks": ["પૂર્વાષાઢા", "ભરણી", "પૂર્વા ફાલ્ગુની"], "swami": "શુક્ર"}
}

def get_dms(deg):
    d = int(deg)
    m = int((deg - d) * 60)
    s = int(((deg - d) * 60 - m) * 60)
    return f"{d}°{m}'{s}\""

def get_astro_data(planet_id, time):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(time.year, time.month, time.day, time.hour + time.minute/60.0 + 5.5)
    swe.set_topo(LON, LAT, 0)
    data = swe.calc_ut(jd, planet_id, swe.FLG_SIDEREAL | swe.FLG_TOPOCTR)[0][0]
    
    if planet_id == 1: # ચંદ્ર ઓફસેટ
        data = (data + MOON_OFFSET) % 360
        
    rashi_idx = int(data // 30)
    rashi_deg = data % 30
    nak_idx = int(data // 13.333333333333334)
    nak_deg = data % 13.333333333333334
    
    rashis = ["મેષ", "વૃષભ", "મિથુન", "કર્ક", "સિંહ", "કન્યા", "તુલા", "વૃશ્ચિક", "ધન", "મકર", "કુંભ", "મીન"]
    nakshatras = ["અશ્વિની", "ભરણી", "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફાલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", "મૂળ", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદા", "ઉત્તરા ભાદ્રપદા", "રેવતી"]
    
    return rashis[rashi_idx], rashi_deg, nakshatras[nak_idx % 27], nak_deg

def create_event(summary, description, start_time):
    print(f"Creating Event: {summary}")
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=creds)
    event = {
        'summary': summary,
        'description': description,
        'start': {'dateTime': start_time.isoformat()},
        'end': {'dateTime': (start_time + timedelta(hours=1)).isoformat()},
    }
    service.events().insert(calendarId=CALENDAR_ID, body=event).execute()

def run_tracker():
    print(f"--- ટ્રેકર રન શરૂ થયો: {datetime.now()} ---")
    
    for p_id, name in [(0, "સૂર્ય"), (1, "ચંદ્ર")]:
        rashi, r_deg, nak, n_deg = get_astro_data(p_id, datetime.now())
        print(f"{name}: રાશિ={rashi} ({get_dms(r_deg)}), નક્ષત્ર={nak} ({get_dms(n_deg)})")
        
        future_time = datetime.now() + timedelta(hours=3)
        _, _, fut_nak, _ = get_astro_data(p_id, future_time)
        
        if nak != fut_nak:
            for tara, info in NAVTARA_DATA.items():
                if fut_nak in info["naks"]:
                    desc = f"નવતારા: {tara}\nસ્વામી: {info['swami']}\nપ્રવેશ: {future_time.strftime('%H:%M')}"
                    create_event(f"નવતારા {name}: {tara}", desc, future_time)

    print("--- ટ્રેકર રન પૂર્ણ થયો ---")

if __name__ == "__main__":
    run_tracker()