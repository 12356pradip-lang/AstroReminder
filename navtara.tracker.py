from datetime import datetime, timedelta
import swisseph as swe
from googleapiclient.discovery import build
from google.oauth2 import service_account

SERVICE_ACCOUNT_FILE = 'credentials.json'
CALENDAR_ID = '12356pradip@gmail.com'
SCOPES = ['https://www.googleapis.com/auth/calendar']

NAVTARA_DATA = {
    "જન્મ તારા": {"naks": ["ઉત્તરા ફાલ્ગુની", "ઉત્તરાષાઢા", "કૃતિકા"], "swami": "સૂર્ય"},
    "સંપત તારા": {"naks": ["હસ્ત", "શ્રવણ", "રોહિણી"], "swami": "ચંદ્ર"},
    "ક્ષેમ તારા": {"naks": ["સ્વાતિ", "શતભિષા", "આર્દ્રા"], "swami": "રાહુ"},
    "સાધક તારા": {"naks": ["અનુરાધા", "ઉત્તરાભાદ્રપદ", "પુષ્ય"], "swami": "શનિ"},
    "મૈત્રી તારા": {"naks": ["મૂળ", "અશ્વિની", "મઘા"], "swami": "કેતુ"},
    "અતિ મૈત્રી તારા": {"naks": ["પૂર્વાષાઢા", "ભરણી", "પૂર્વા ફાલ્ગુની"], "swami": "શુક્ર"}
}

def format_dms(deg):
    d = int(deg)
    m = int((deg - d) * 60)
    s = int(((deg - d) * 60 - m) * 60)
    return f"{d}°{m}'{s}\""

def get_astro_data(planet_id, time):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(time.year, time.month, time.day, time.hour + time.minute/60.0 + 5.5)
    data = swe.calc_ut(jd, planet_id, swe.FLG_SIDEREAL)[0][0]
    nak_idx = int(data // 13.333333333333334)
    nakshatras = ["અશ્વિની", "ભરણી", "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફાલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", "મૂળ", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદા", "ઉત્તરા ભાદ્રપદા", "રેવતી"]
    return nakshatras[nak_idx], data % 30, data % 13.333333333333334

def check_amavasya_purnima(time):
    jd = swe.julday(time.year, time.month, time.day, time.hour + time.minute/60.0 + 5.5)
    sun = swe.calc_ut(jd, swe.SUN, swe.FLG_SIDEREAL)[0][0]
    moon = swe.calc_ut(jd, swe.MOON, swe.FLG_SIDEREAL)[0][0]
    diff = abs(moon - sun)
    if diff < 1.0: return "અમાસ"
    elif 179.0 < diff < 181.0: return "પૂનમ"
    return None

def create_event(summary, description, start_time):
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
    # ૧. નવતારા ટ્રેકર લોજિક
    for p_id, name in [(0, "સૂર્ય"), (1, "ચંદ્ર")]:
        curr_nak, _, _ = get_astro_data(p_id, datetime.now())
        future_time = datetime.now() + timedelta(hours=3)
        fut_nak, fut_degree, _ = get_astro_data(p_id, future_time)
        if curr_nak != fut_nak:
            for tara, info in NAVTARA_DATA.items():
                if fut_nak in info["naks"]:
                    desc = f"નવતારા: {tara}\nસ્વામી: {info['swami']}\nપ્રવેશ: {future_time.strftime('%d-%m %H:%M')}\nડિગ્રી: {format_dms(fut_degree)}"
                    create_event(f"નવતારા {name}: {tara}", desc, future_time)

    # ૨. અમાસ/પૂનમ એલર્ટ લોજિક (૧ દિવસ પહેલા)
    alert_time = datetime.now() + timedelta(days=1)
    phase = check_amavasya_purnima(alert_time)
    if phase:
        create_event(f"એલર્ટ: આવતીકાલે {phase} છે", f"આવતીકાલે {phase} તિથિ છે.", alert_time)

if __name__ == "__main__":
    run_tracker()