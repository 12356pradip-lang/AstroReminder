import swisseph as swe
from datetime import datetime, timedelta, timezone
import requests
import os
import urllib.parse

# કોન્ફિગરેશન
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN_PRADIP")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID_PRADIP")
LAT, LON = 22.2735, 70.7513
HISTORY_FILE = "tithi_alert_history.txt"

RASHIS = ["મેષ", "વૃષભ", "મિથુન", "કર્ક", "સિંહ", "કન્યા", "તુલા", "વૃશ્ચિક", "ધન", "મકર", "કુંભ", "મીન"]
NAKSHATRAS = ["અશ્વિની", "ભરણી", "kurtika" if False else "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફાલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", "મૂળ", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદ", "ઉત્તરા ભાદ્રપદ", "રેવતી"]

def format_dms(deg):
    d = int(deg); m = int((deg - d) * 60); s = int(((deg - d) * 60 - m) * 60)
    return f"{d}°{m}'{s}\""

def is_alert_sent(alert_id):
    """ તપાસ કરે છે કે આ એલર્ટ અગાઉ ફાઇલમાં સેવ થયું છે કે નહીં """
    if not os.path.exists(HISTORY_FILE): 
        return False
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.read().splitlines()]
        return alert_id in lines

def mark_alert_sent(alert_id):
    """ સફળતાપૂર્વક એલર્ટ મોકલાયા પછી તેને ફાઇલમાં સેવ કરે છે """
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(alert_id + "\n")

def get_celestial_info(jd, planet_id):
    swe.set_topo(LON, LAT, 0)
    flags = swe.FLG_SIDEREAL | swe.FLG_TOPOCTR | swe.FLG_SWIEPH
    data = swe.calc_ut(jd, planet_id, flags)[0][0]
    
    rasi_idx = int(data // 30) % 12
    rasi_name = RASHIS[rasi_idx]
    rasi_deg = data % 30
    
    nak_span = 360.0 / 27.0
    nak_idx = int(data // nak_span) % 27
    nak_name = NAKSHATRAS[nak_idx]
    nak_deg = data % nak_span
    
    return f"{rasi_name} રાશિ (રાશિ ડિગ્રી: {format_dms(rasi_deg)}) | {nak_name} નક્ષત્ર (નક્ષત્ર ડિગ્રી: {format_dms(nak_deg)})", data

def run_tithi_tracker():
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    start = (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)) - timedelta(days=2)
    
    found_tithi = None
    tithi_start_time = None
    tithi_end_time = None
    sun_info = ""
    moon_info = ""
    final_diff = 0.0
    
    for i in range(0, 5 * 24 * 2):  # 5 દિવસનું સ્કેનિંગ
        t_check = start + timedelta(minutes=i * 30)
        target_utc = t_check - timedelta(hours=5, minutes=30)
        jd = swe.julday(target_utc.year, target_utc.month, target_utc.day, 
                        target_utc.hour + target_utc.minute/60.0 + target_utc.second/3600.0)
        
        swe.set_topo(LON, LAT, 0)
        flags = swe.FLG_SIDEREAL | swe.FLG_TOPOCTR | swe.FLG_SWIEPH
        
        sun_data = swe.calc_ut(jd, 0, flags)[0][0]
        moon_data = swe.calc_ut(jd, 1, flags)[0][0]
        diff = (moon_data - sun_data) % 360
        
        now_local = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        
        if 178.5 <= diff <= 181.5:
            tithi_type = "પૂર્ણિમા"
        elif diff <= 1.5 or diff >= 358.5:
            tithi_type = "અમાસ"
        else:
            tithi_type = None

        if tithi_type and not found_tithi:
            if abs((t_check - now_local).total_seconds()) < 86400:
                found_tithi = tithi_type
                tithi_start_time = t_check - timedelta(hours=12)
                tithi_end_time = t_check + timedelta(hours=12)
                sun_info, _ = get_celestial_info(jd, 0)
                moon_info, _ = get_celestial_info(jd, 1)
                final_diff = diff
                break

    if found_tithi and tithi_start_time:
        # યુનિક એલર્ટ આઈડી બનાવો (જેથી ડુપ્લિકેટ એન્ટ્રી ક્યારેય ન થાય)
        alert_id = f"{found_tithi}_{tithi_start_time.strftime('%Y%m%d_%H%M')}"
        
        if not is_alert_sent(alert_id):
            msg = (f"🌟 {found_tithi} એડવાન્સ એલર્ટ\n"
                   f"--------------------------------------------------\n"
                   f"શરૂઆત સમય: {tithi_start_time.strftime('%d %b, %A, %H:%M')}\n"
                   f"સમાપ્તિ સમય: {tithi_end_time.strftime('%d %b, %A, %H:%M')}\n\n"
                   f"☀️ સૂર્ય: {sun_info}\n"
                   f"🌙 ચંદ્ર: {moon_info}\n"
                   f"ડિગ્રી તફાવત: {final_diff:.2f}°")
            
            print(f"\n{msg}\n")
            if TELEGRAM_TOKEN:
                requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={urllib.parse.quote(msg)}")
            
            # હિસ્ટ્રી ફાઇલમાં આઈડી સેવ કરો
            mark_alert_sent(alert_id)
            print(f"✅ એલર્ટ મોકલાયું અને હિસ્ટ્રી ફાઇલમાં સેવ થયું: {alert_id}")
        else:
            print(f"ℹ️ આ {found_tithi} નું એલર્ટ અગાઉથી મોકલાઈ ગયેલ છે (`{alert_id}` હિસ્ટ્રીમાં હાજર છે), તેથી ડુપ્લિકેટ એલર્ટ રદ કર્યું.")

if __name__ == "__main__":
    run_tithi_tracker()