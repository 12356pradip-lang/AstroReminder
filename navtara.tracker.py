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

def format_dms(deg):
    d = int(deg); m = int((deg - d) * 60); s = int(((deg - d) * 60 - m) * 60)
    return f"{d}°{m}'{s}\""

def get_current_data(planet_id):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    jd = swe.julday(now.year, now.month, now.day, now.hour + (now.minute / 60.0) + (now.second / 3600.0) + 5.5)
    swe.set_topo(LON, LAT, 0)
    data = swe.calc_ut(jd, planet_id, swe.FLG_SIDEREAL | swe.FLG_TOPOCTR | swe.FLG_SWIEPH)[0][0]
    
    rasi_idx = int(data // 30)
    rashis = ["મેષ", "વૃષભ", "મિથુન", "કર્ક", "સિંહ", "કન્યા", "તુલા", "વૃશ્ચિક", "ધન", "મકર", "કુંભ", "મીન"]
    nak_idx = int(data // 13.333333333333334)
    nakshatras = ["અશ્વિની", "ભરણી", "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફાલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", "મૂળ", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદ", "ઉત્તરા ભાદ્રપદ", "રેવતી"]
    
    return rashis[rasi_idx], nakshatras[nak_idx % 27], data % 13.333333333333334

def get_nakshatra(planet_id, target_time):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(target_time.year, target_time.month, target_time.day, target_time.hour + (target_time.minute / 60.0) + 5.5)
    swe.set_topo(LON, LAT, 0)
    data = swe.calc_ut(jd, planet_id, swe.FLG_SIDEREAL | swe.FLG_TOPOCTR)[0][0]
    nak_idx = int(data // 13.333333333333334)
    nakshatras = ["અશ્વિની", "ભરણી", "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફાલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", "મૂળ", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદ", "ઉત્તરા ભાદ્રપદ", "રેવતી"]
    return nakshatras[nak_idx % 27]

def get_fine_times(planet_id, target_nak):
    now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    
    if planet_id == 0:  # સૂર્ય માટે (જે લાંબો સમય નક્ષત્રમાં રહે છે)
        # ભૂતકાળમાં 15 દિવસ પાછળથી શરૂ કરીને એન્ટ્રી શોધો
        start_search = now - timedelta(days=15)
        entry = None
        # 1 કલાકના સ્ટેપથી એન્ટ્રી શોધો (સૂર્ય માટે સ્પીડ સારી રહે)
        for i in range(0, 15 * 24 + 48, 1):
            t_check = start_search + timedelta(hours=i)
            if get_nakshatra(planet_id, t_check) == target_nak:
                entry = t_check
                break
        
        if not entry:
            entry = now

        # એન્ટ્રી મળ્યા પછી નિર્ગમન (Exit) શોધવા આગળ વધવું
        t_exit = entry + timedelta(days=1)
        for _ in range(30 * 24):  # વધુમાં વધુ 30 દિવસ સુધી તપાસો
            if get_nakshatra(planet_id, t_exit) != target_nak:
                break
            t_exit += timedelta(hours=1)
        return entry.strftime("%d %b %H:%M"), t_exit.strftime("%d %b %H:%M")

    else:  # ચંદ્ર માટે (ઝડપી ભ્રમણ - મિનિટ-વાઈઝ પરફેક્ટ સ્કેન)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        entry = None
        for i in range(0, 72 * 60):  # 72 કલાક મિનિટવાળી લૂપ
            t_check = start + timedelta(minutes=i)
            if get_nakshatra(planet_id, t_check) == target_nak:
                entry = t_check
                break
                
        if entry:
            for k in range(1, 72 * 60):
                t_exit = entry + timedelta(minutes=k)
                if get_nakshatra(planet_id, t_exit) != target_nak:
                    return entry.strftime("%d %b %H:%M"), t_exit.strftime("%d %b %H:%M")
                    
        return "N/A", "N/A"

def create_calendar_event(summary, description):
    try:
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('calendar', 'v3', credentials=creds)
        now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        event = {'summary': summary, 'description': description, 'start': {'dateTime': now.isoformat()}, 'end': {'dateTime': (now + timedelta(hours=1)).isoformat()}}
        service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    except Exception as e: print(f"❌ કેલેન્ડર એરર: {e}")

def is_alert_sent(alert_id):
    if not os.path.exists(HISTORY_FILE): return False
    with open(HISTORY_FILE, "r") as f: return alert_id in f.read().splitlines()

def mark_alert_sent(alert_id):
    with open(HISTORY_FILE, "a") as f: f.write(alert_id + "\n")

def run_tracker():
    planets = {0: "સૂર્ય", 1: "ચંદ્ર"}
    future_time = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30) + timedelta(hours=12)
    current_date_id = (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)).strftime('%Y%m%d')

    for p_id, p_name in planets.items():
        fut_n = get_nakshatra(p_id, future_time)
        curr_rashi, curr_nak, curr_deg = get_current_data(p_id)

        for tara, naks in NAVTARA_DATA.items():
            if fut_n in naks:
                # સૂર્ય માટે નિર્ગમન તારીખ સુધી એલર્ટ લોક રાખવું જેથી રિપીટ ન થાય, ચંદ્ર માટે ડેઈલી/એન્ટ્રી બેઝ્ડ આઈડી
                if p_id == 0:
                    _, exit_str = get_fine_times(p_id, fut_n)
                    # સૂર્ય માટે સમય કે મિનિટ કાઢીને માત્ર તારીખ રાખવી જેથી ડુપ્લિકેટ ન બને
                    alert_id = f"{p_name}_{fut_n}_{exit_str[:6]}"
                else:
                    entry_str, _ = get_fine_times(p_id, fut_n)
                    # ચંદ્ર માટે મિનિટ કાઢીને માત્ર કલાક સુધીનું રાખવું
                    alert_id = f"{p_name}_{fut_n}_{entry_str[:10]}"

                if is_alert_sent(alert_id): continue
                
                entry, exit_t = get_fine_times(p_id, fut_n)
                
                # નવું ફોર્મેટ કરેલું આઉટપુટ (બિલકુલ મૂળ મુજબ જ)
                msg = (f"🌟 {p_name} 12 કલાક એડવાન્સ એલર્ટ: {tara}\n"
                       f"---------------------------\n"
                       f"વર્તમાન સ્થિતિ: {curr_rashi}, {curr_nak} ({format_dms(curr_deg)})\n"
                       f"ભવિષ્યનું નક્ષત્ર: {fut_n}\n"
                       f"પ્રવેશ: {entry}\n"
                       f"નિર્ગમન: {exit_t}")
                
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={urllib.parse.quote(msg)}"
                requests.get(url)
                create_calendar_event(f"નવતારા: {tara}", msg)
                mark_alert_sent(alert_id)
                print(f"✅ એલર્ટ મોકલાયું:\n{msg}")
                break

if __name__ == "__main__":
    run_tracker()