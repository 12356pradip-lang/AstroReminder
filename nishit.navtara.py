from datetime import datetime, timedelta, timezone
import swisseph as swe
import requests

# --- કોન્ફિગરેશન ---
TELEGRAM_TOKEN = "8795156986:AAGoUEF_izKhD91Nhv6UbkshUBS3YQcT8"
TELEGRAM_CHAT_ID = "8713489324"
LAT, LON = 22.2735, 70.7513

NAVTARA_DATA = {
    "જન્મ તારા": ["અશ્વિની", "મઘા", "મૂલા"],
    "સંપત તારા": ["ભરણી", "પૂર્વા ફાલ્ગુની", "પૂર્વાષાઢા"],
    "ક્ષેમ તારા": ["કૃતિકા", "ઉત્તરા ફાલ્ગુની", "ઉત્તરાષાઢા"],
    "સાધક તારા": ["રોહિણી", "હસ્ત", "શ્રવણ"],
    "મિત્ર તારા": ["મૃગશીર્ષ", "ચિત્રા", "ધનિષ્ટા"],
    "નૈધન તારા": ["આર્દ્રા", "સ્વાતિ", "શતભિષા"],
    "સાધક તારા": ["પુનર્વસુ", "વિશાખા", "પૂર્વા ભાદ્રપદા"],
    "પરમ મિત્ર તારા": ["પુષ્ય", "અનુરાધા", "ઉત્તરા ભાદ્રપદા"],
    "પરમ મિત્ર તારા": ["આશ્લેષા", "જ્યેષ્ઠા", "રેવતી"]
}

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={text}"
    requests.get(url)

def get_nakshatra(planet_id, target_time):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(target_time.year, target_time.month, target_time.day, 
                    target_time.hour + (target_time.minute / 60.0) + (target_time.second / 3600.0) + 5.5)
    swe.set_topo(LON, LAT, 0)
    data = swe.calc_ut(jd, planet_id, swe.FLG_SIDEREAL | swe.FLG_TOPOCTR | swe.FLG_SWIEPH)[0][0]
    nak_idx = int(data // 13.333333333333334)
    nakshatras = ["અશ્વિની", "ભરણી", "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફાલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", "મૂલા", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદા", "ઉત્તરા ભાદ્રપદા", "રેવતી"]
    return nakshatras[nak_idx]

def get_times(planet_id, current_n):
    current_time = datetime.now(timezone.utc)
    entry_time = None
    exit_time = None
    
    # પાછળના 24 કલાક અને આગળના 24 કલાક ચેક કરો
    for i in range(-24 * 60, 24 * 60, 10):
        check_time = current_time + timedelta(minutes=i)
        nak = get_nakshatra(planet_id, check_time)
        
        if nak == current_n:
            if entry_time is None: entry_time = check_time
        elif entry_time is not None and exit_time is None:
            exit_time = check_time
            break
            
    # None ની એરર ન આવે તે માટે ચેક
    entry_str = entry_time.strftime("%d %b %H:%M") if entry_time else "N/A"
    exit_str = exit_time.strftime("%d %b %H:%M") if exit_time else "N/A"
            
    return entry_str, exit_str

def run_tracker():
    planets = {0: "સૂર્ય", 1: "ચંદ્ર"}
    current_time = datetime.now(timezone.utc)
    future_time = current_time + timedelta(hours=12)

    for p_id, p_name in planets.items():
        # 12 કલાક પછીનું નક્ષત્ર ચેક કરો
        fut_n = get_nakshatra(p_id, future_time)
        
        # આ નક્ષત્ર માટે એન્ટ્રી અને એક્ઝિટ મેળવો
        entry, exit_t = get_times(p_id, fut_n)
        
        for tara, naks in NAVTARA_DATA.items():
            if fut_n in naks:
                msg = (f"🌟 {p_name} 12 કલાક એડવાન્સ એલર્ટ: {tara}\n"
                       f"નક્ષત્ર: {fut_n}\n"
                       f"પ્રવેશ: {entry}\n"
                       f"નિર્ગમન: {exit_t}")
                send_telegram_msg(msg)
                print(f"✅ એલર્ટ મોકલાયું:\n{msg}")

if __name__ == "__main__":
    run_tracker()