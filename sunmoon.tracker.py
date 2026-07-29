from datetime import datetime, timedelta, timezone
import swisseph as swe
import requests
import os
import urllib.parse

# --- કોન્ફિગરેશન ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN_PRADIP")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID_PRADIP")
LAT, LON = 22.2735, 70.7513
HISTORY_FILE = "sun_moon_detail_history.txt"

RASHIS = ["મેષ", "વૃષભ", "મિથુન", "કર્ક", "સિંહ", "કન્યા", "તુલા", "વૃશ્ચિક", "ધન", "મકર", "કુંભ", "મીન"]
NAKSHATRAS = [
    "અશ્વિની", "ભરણી", "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", 
    "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફાલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", 
    "મૂળ", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદ", "ઉત્તરા ભાદ્રપદ", "રેવતી"
]

def format_dms(deg):
    d = int(deg)
    m = int((deg - d) * 60)
    s = int(((deg - d) * 60 - m) * 60)
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
    rasi_name = RASHIS[rasi_idx]
    rasi_deg = total_deg % 30
    
    nak_span = 360.0 / 27.0
    nak_idx = int(total_deg // nak_span) % 27
    nak_name = NAKSHATRAS[nak_idx]
    
    nak_deg = total_deg % nak_span
    pada_span = nak_span / 4.0
    pada = int(nak_deg // pada_span) + 1
    
    return rasi_name, rasi_deg, nak_name, pada, nak_deg, total_deg, jd

def get_nakshatra_pada_times(planet_id, current_time, current_nak):
    """
    વર્તમાન નક્ષત્રના ચારેય પદ ક્યારે શરૂ થાય છે અને પૂરા થાય છે તેની સચોટ ગણતરી કરે છે.
    """
    search_start = current_time - timedelta(days=15 if planet_id == 0 else 2)
    entry_time = None
    
    step_minutes = 60 if planet_id == 0 else 5
    t_check = search_start
    end_limit = current_time + timedelta(days=15 if planet_id == 0 else 2)
    
    while t_check <= end_limit:
        _, _, nak, _, _, _, _ = get_astro_position(planet_id, t_check)
        if nak == current_nak:
            entry_time = t_check
            break
        t_check += timedelta(minutes=step_minutes)

    if entry_time:
        fine_check = entry_time - timedelta(minutes=step_minutes)
        for m in range(0, step_minutes * 2 + 1):
            t_f = fine_check + timedelta(minutes=m)
            _, _, nak, _, _, _, _ = get_astro_position(planet_id, t_f)
            if nak == current_nak:
                entry_time = t_f
                break

    exit_time = entry_time
    if entry_time:
        t_exit = entry_time + timedelta(hours=1)
        while True:
            _, _, nak, _, _, _, _ = get_astro_position(planet_id, t_exit)
            if nak != current_nak:
                exit_time = t_exit
                break
            t_exit += timedelta(hours=1 if planet_id == 0 else 0.5)

    pada_schedule = []
    if entry_time and exit_time:
        total_duration = exit_time - entry_time
        single_pada_duration = total_duration / 4.0
        
        for i in range(4):
            p_start = entry_time + (single_pada_duration * i)
            p_end = entry_time + (single_pada_duration * (i + 1))
            pada_schedule.append((i + 1, p_start, p_end))
            
    return pada_schedule

def is_already_sent_today(today_str):
    """
    હિસ્ટ્રી ફાઇલમાં ચેક કરે છે કે આજની તારીખ પહેલેથી નોંધાયેલી છે કે નહીં.
    """
    if not os.path.exists(HISTORY_FILE):
        return False
    
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        if today_str in content:
            return True
    return False

def save_to_history(today_str):
    """
    આજની તારીખને હિસ્ટ્રી ફાઇલમાં સેવ કરે છે.
    """
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"Report sent on: {today_str}\n")

def run_tracker():
    now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    today_str = now.strftime("%Y-%m-%d")  # ઉદાહરણ તરીકે: '2026-07-29'

    # 1. ચેક કરો કે આજની તારીખનો રિપોર્ટ અગાઉ મોકલાયો છે કે નહીં
    if is_already_sent_today(today_str):
        print(f"[{today_str}] આજનો રિપોર્ટ ઓલરેડી સેન્ડ થઈ ગયો છે, તેથી ડુપ્લિકેટ એલર્ટ રદ કરવામાં આવી છે.")
        return

    planets = {0: "સૂર્ય (Sun)", 1: "ચંદ્ર (Moon)"}
    full_msg = ""

    for p_id, p_name in planets.items():
        rasi_name, rasi_deg, nak_name, current_pada, nak_deg, total_deg, jd = get_astro_position(p_id, now)
        
        padas = get_nakshatra_pada_times(p_id, now, nak_name)
        
        padas_text = ""
        for p_num, p_start, p_end in padas:
            active_mark = " ◄ (ચાલુ)" if p_num == current_pada else ""
            padas_text += f"  • પદ {p_num}: {p_start.strftime('%d %b, %H:%M')} થી {p_end.strftime('%d %b, %H:%M')}{active_mark}\n"

        msg = (f"<b>🌟 લાઈવ રિપોર્ટ : {p_name}</b>\n\n"
               f"• <b>કુલ નિરયણ ડિગ્રી:</b> {total_deg:.2f}° ({format_dms(total_deg)})\n"
               f"• <b>વર્તમાન સ્થિતિ:</b> {rasi_name} રાશિ (ડિગ્રી: {format_dms(rasi_deg)})\n"
               f"• <b>નક્ષત્ર સ્થિતિ:</b> {nak_name} (પદ {current_pada} | ડિગ્રી: {format_dms(nak_deg)})\n\n"
               f"<b>📅 નક્ષત્રના ચારેય પદની વિગત:</b>\n{padas_text}\n\n")
        
        full_msg += msg
        print(f"\n{msg.replace('<b>','').replace('</b>','')}")

    # 2. ટેલિગ્રામ પર મેસેજ મોકલો (જો ટોકન ઉપલબ્ધ હોય તો)
    if TELEGRAM_TOKEN and full_msg:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={urllib.parse.quote(full_msg)}&parse_mode=HTML"
        response = requests.get(url)
        
        # જો મેસેજ સફળતાપૂર્વક સેન્ડ થઈ જાય, તો જ તારીખ હિસ્ટ્રી ફાઇલમાં રેકોર્ડ કરો
        if response.status_code == 200:
            save_to_history(today_str)
            print(f"[{today_str}] ટેલિગ્રામ એલર્ટ સફળતાપૂર્વક મોકલાઈ ગઈ છે અને હિસ્ટ્રી ફાઇલમાં સેવ થઈ ગઈ છે.")
        else:
            print(f"ટેલિગ્રામ એપીઆઈ એરર: {response.text}")

if __name__ == "__main__":
    run_tracker()