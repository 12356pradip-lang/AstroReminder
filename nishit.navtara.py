from datetime import datetime, timedelta, timezone
import swisseph as swe
import requests
import os
import urllib.parse

# --- કોન્ફિગરેશન ---
TELEGRAM_TOKEN = "8795156986:AAGoUEF_izKhD91Nhv6UbkshUBS3YQcT8"
TELEGRAM_CHAT_ID = "8713489324"
LAT, LON = 22.2735, 70.7513
HISTORY_FILE = "nishit_history.txt"

NAVTARA_DATA = {
    "જન્મ તારા": ["જ્યેષ્ઠા", "આશ્લેષા", "રેવતી"],
    "સંપત તારા": ["મઘા", "અશ્વિની", "મૂલા"],
    "ક્ષેમ તારા": ["ઉત્તરા ફાલ્ગુની", "કૃતિકા", "ઉત્તરાષાઢા"],
    "સાધક તારા": ["ચિત્રા", "મૃગશીર્ષ", "ધનિષ્ટા"],
    "મિત્ર તારા": ["વિશાખા", "પુનર્વસુ", "પૂર્વા ભાદ્રપદા"],
    "પરમ મિત્ર તારા": ["અનુરાધા", "પુષ્ય", "ઉત્તરા ભાદ્રપદા"],
}

def format_dms(deg):
    d = int(deg); m = int((deg - d) * 60); s = int(((deg - d) * 60 - m) * 60)
    return f"{d}°{m}'{s}\""
    
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
    nakshatras = ["અશ્વિની", "ભરણી", "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફાલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", "મૂલા", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદા", "ઉત્તરા ભાદ્રપદ", "રેવતી"]
    return nakshatras[nak_idx % 27]

def get_fine_times(planet_id, target_nak):
    now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    
    if planet_id == 0:  # સૂર્ય માટે (લાંબો સમય નક્ષત્રમાં રહે છે)
        start_search = now - timedelta(days=15)
        entry = None
        for i in range(0, 15 * 24 + 48, 1):
            t_check = start_search + timedelta(hours=i)
            if get_nakshatra(planet_id, t_check) == target_nak:
                entry = t_check
                break
        
        if not entry:
            entry = now

        t_exit = entry + timedelta(days=1)
        for _ in range(30 * 24):
            if get_nakshatra(planet_id, t_exit) != target_nak:
                break
            t_exit += timedelta(hours=1)
        return entry.strftime("%d %b %H:%M"), t_exit.strftime("%d %b %H:%M")

    else:  # ચંદ્ર માટે (ઝડપી ભ્રમણ - મિનિટ-વાઈઝ પરફેક્ટ સ્કેન)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        entry = None
        for i in range(0, 72 * 60):  
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

def run_tracker():
    planets = {0: "સૂર્ય", 1: "ચંદ્ર"}
    future_time = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30) + timedelta(hours=12)

    for p_id, p_name in planets.items():
        fut_n = get_nakshatra(p_id, future_time)
        
        for tara, naks in NAVTARA_DATA.items():
            if fut_n in naks:
                # સૂર્ય માટે નિર્ગમન તારીખ સુધી એલર્ટ લોક રાખવું જેથી રિપીટ ન થાય, ચંદ્ર માટે એન્ટ્રી ટાઇમ બેઝ્ડ આઈડી
                if p_id == 0:
                    _, exit_str = get_fine_times(p_id, fut_n)
                    # સૂર્ય માટે મિનિટ/સમય કાઢીને માત્ર તારીખ રાખવી જેથી ડુપ્લિકેટ ન બને
                    alert_id = f"{p_name}_{fut_n}_{exit_str[:6]}"
                else:
                    entry_str, _ = get_fine_times(p_id, fut_n)
                    # ચંદ્ર માટે મિનિટ કાઢીને માત્ર કલાક સુધીનું રાખવું જેથી મિનિટ બદલાવાથી ડુપ્લિકેટ ન બને
                    alert_id = f"{p_name}_{fut_n}_{entry_str[:10]}"

                if is_alert_sent(alert_id): continue
                
                entry, exit_t = get_fine_times(p_id, fut_n)
                msg = (f"🌟 {p_name} 12 કલાક એડવાન્સ એલર્ટ: {tara}\n"
                       f"નક્ષત્ર: {fut_n}\n"
                       f"પ્રવેશ: {entry}\n"
                       f"નિર્ગમન: {exit_t}")
                
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={urllib.parse.quote(msg)}"
                requests.get(url)
                mark_alert_sent(alert_id)
                print(f"✅ એલર્ટ મોકલાયું: {alert_id}")
                break

if __name__ == "__main__":
    run_tracker()