import swisseph as swe
from datetime import datetime, timedelta, timezone
import os
import requests
import urllib.parse
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
    target_utc = target_time - timedelta(hours=5, minutes=30)
    jd = swe.julday(target_utc.year, target_utc.month, target_utc.day, 
                    target_utc.hour + target_utc.minute/60.0 + target_utc.second/3600.0)
    
    swe.set_topo(LON, LAT, 0)
    flags = swe.FLG_SIDEREAL | swe.FLG_TOPOCTR | swe.FLG_SWIEPH
    
    res = swe.calc_ut(jd, planet_id, flags)
    total_deg = res[0][0]  
    
    rasi_idx = int(total_deg // 30) % 12
    rashis = ["મેષ", "વૃષભ", "મિથુન", "કર્ક", "સિંહ", "કન્યા", "તુલા", "વૃશ્ચિક", "ધન", "મકર", "કુંભ", "મીન"]
    rasi_name = rashis[rasi_idx]
    rasi_deg = total_deg % 30
    
    nak_span = 360.0 / 27.0  
    nak_idx = int(total_deg // nak_span) % 27
    nakshatras = ["અશ્વિની", "ભરણી", "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફાલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", "મૂળ", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદ", "ઉત્તરા ભાદ્રપદ", "રેવતી"]
    nak_name = nakshatras[nak_idx]
    
    nak_deg = total_deg % nak_span
    pada_span = nak_span / 4.0
    pada = int(nak_deg // pada_span) + 1
    
    return rasi_name, rasi_deg, nak_name, pada, nak_deg, total_deg

def get_fine_times(planet_id, target_nak):
    now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    
    if planet_id == 0:  # સૂર્ય માટે
        start_search = now - timedelta(days=15)
        entry = None
        entry_data = None
        for i in range(0, 15 * 24 + 48, 1):
            t_check = start_search + timedelta(hours=i)
            rasi, r_deg, nak, pada, n_deg, t_deg = get_astro_position(planet_id, t_check)
            if nak == target_nak:
                entry = t_check
                entry_data = (rasi, r_deg, pada, n_deg, t_deg)
                break
        
        if not entry:
            return None, None, None, None, None, None, None

        t_exit = entry + timedelta(days=1)
        for _ in range(30 * 24):
            rasi_e, r_deg_e, nak_e, pada_e, n_deg_e, t_deg_e = get_astro_position(planet_id, t_exit)
            if nak_e != target_nak:
                break
            t_exit += timedelta(hours=1)
        return entry, t_exit, entry_data[0], entry_data[1], entry_data[2], entry_data[3], entry_data[4]

    else:  # ચંદ્ર માટે
        start = now - timedelta(days=2)
        entry = None
        entry_data = None
        for i in range(0, 72 * 60):  
            t_check = start + timedelta(minutes=i)
            rasi, r_deg, nak, pada, n_deg, t_deg = get_astro_position(planet_id, t_check)
            if nak == target_nak:
                entry = t_check
                entry_data = (rasi, r_deg, pada, n_deg, t_deg)
                break
                
        if entry:
            for k in range(1, 30 * 60):
                t_exit = entry + timedelta(minutes=k)
                rasi_e, r_deg_e, nak_e, pada_e, n_deg_e, t_deg_e = get_astro_position(planet_id, t_exit)
                if nak_e != target_nak:
                    return entry, t_exit, entry_data[0], entry_data[1], entry_data[2], entry_data[3], entry_data[4]
                    
        return None, None, None, None, None, None, None

def run_tracker():
    target_naks = ["આશ્લેષા", "મઘા", "જ્યેષ્ઠა", "ઉત્તરા ભાદ્રપદ", "રેવતી"]
    now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)

    for p_id in [0, 1]:
        name = "સૂર્ય (Sun)" if p_id == 0 else "ચંદ્ર (Moon)"
        
        # દરેક ટાર્ગેટ નક્ષત્ર માટે લૂપ ચલાવીને પરફેક્ટ એન્ટ્રી ટાઇમ ચેક કરીએ
        for target_nak in target_naks:
            entry_t, exit_t, rasi, r_deg, pada, n_deg, total_deg = get_fine_times(p_id, target_nak)
            
            if entry_t and exit_t:
                # જો નક્ષત્ર પ્રવેશ સમય અત્યારથી લઈને આગામી ૧૨-૨૪ કલાકની અંદરનો હોય તો જ એલર્ટ મોકલો
                if now <= entry_t <= (now + timedelta(hours=24)):
                    if p_id == 0:
                        alert_id = f"{target_nak}_{name}_{exit_t.strftime('%Y%m%d')}"
                    else:
                        alert_id = f"{target_nak}_{name}_{entry_t.strftime('%Y%m%d_%H')}"
                    
                    already_sent = False
                    if os.path.exists(HISTORY_FILE):
                        with open(HISTORY_FILE, "r") as f:
                            if alert_id in f.read(): already_sent = True
                    
                    if not already_sent:
                        # અત્યારની રિયલ-ટાઇમ (Current) સ્થિતિ મેળવવા માટે
                        now_time = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                        curr_rasi, curr_rd, curr_nak, curr_pada, curr_nd, curr_td = get_astro_position(p_id, now_time)

                        msg = (f"<b>🌟 કુંડલિની સાધના નક્ષત્ર - એડવાન્સ એલર્ટ : {name}</b>\n\n"
                               f"આગામી સમયમાં {name} <b>{target_nak}</b> નક્ષત્રમાં પ્રવેશ કરશે.\n"
                               f"• <b>કુલ નિરયણ ડિગ્રી:</b> {curr_td:.2f}° ({format_dms(curr_td)})\n"
                               f"• <b>વર્તમાન સ્થિતિ:</b> {curr_rasi} રાશિ (રાશિ ડિગ્રી: {format_dms(curr_rd)})\n"
                               f"• <b>વર્તમાન નક્ષત્ર સ્થિતિ:</b> {curr_nak} (નક્ષત્ર ડિગ્રી: {format_dms(curr_nd)})\n"
                               f"• <b>ભવિષ્યનું નક્ષત્ર:</b> <b>{target_nak}</b>\n"
                               f"• <b>નક્ષત્ર પ્રવેશ:</b> {entry_t.strftime('%d %b, %H:%M')}\n"
                               f"• <b>નક્ષત્ર નિર્ગમન સમય:</b> {exit_t.strftime('%d %b, %H:%M')}")
                    
                        if TELEGRAM_TOKEN:
                            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={urllib.parse.quote(msg)}&parse_mode=HTML"
                            requests.get(url)
                            
                        create_calendar_event(f"નવતારા: {target_nak}", msg)
                        
                        with open(HISTORY_FILE, "a") as f: f.write(alert_id + "\n")
                        print(f"✅ મોકલાયું: {alert_id}")
                        break

if __name__ == "__main__":
    run_tracker()