import swisseph as swe
from datetime import datetime, timedelta, timezone
import requests
import os

# કોન્ફિગરેશન
TELEGRAM_TOKEN = "8731134888:AAGHEul75rh6HZBefn7WCrbXUCyBqJ_zeXU"
TELEGRAM_CHAT_ID = "478006282"
LAT, LON = 22.2735, 70.7513

def format_dms(deg):
    d = int(deg); m = int((deg - d) * 60); s = int(((deg - d) * 60 - m) * 60)
    return f"{d}°{m}'{s}\""

def get_celestial_info(jd, planet_id):
    # planet_id: 0 for Sun, 1 for Moon
    data = swe.calc_ut(jd, planet_id, swe.FLG_SIDEREAL)[0][0]
    rasi_idx = int(data // 30)
    rasi_name = ["મેષ", "વૃષભ", "મિથુન", "કર્ક", "સિંહ", "કન્યા", "તુલા", "વૃશ્ચિક", "ધન", "મકર", "કુંભ", "મીન"][rasi_idx]
    
    nakshatras = ["અશ્વિની", "ભરણી", "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફાલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", "મૂળ", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદ", "ઉત્તરા ભાદ્રપદ", "રેવતી"]
    nak_name = nakshatras[int(data // 13.333333333333334) % 27]
    nak_deg = data % 13.333333333333334
    
    return f"{rasi_name} રાશિ, {format_dms(data % 30)} | {nak_name} નક્ષત્ર, {format_dms(nak_deg)}"

def run_tithi_tracker():
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    start = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    
    found_tithi = None
    tithi_start_time = None
    
    for i in range(0, 12 * 60):
        t_check = start + timedelta(minutes=i)
        jd = swe.julday(t_check.year, t_check.month, t_check.day, t_check.hour + t_check.minute/60.0)
        
        sun = swe.calc_ut(jd, 0, swe.FLG_SIDEREAL)[0][0]
        moon = swe.calc_ut(jd, 1, swe.FLG_SIDEREAL)[0][0]
        diff = (moon - sun) % 360
        
        tithi_type = None
        if 179.5 < diff < 180.5: tithi_type = "પૂર્ણિમા"
        elif diff < 0.5 or diff > 359.5: tithi_type = "અમાસ"
        
        if tithi_type and not found_tithi:
            found_tithi = tithi_type
            tithi_start_time = t_check
            # વિગતો એકત્રિત કરો
            sun_info = get_celestial_info(jd, 0)
            moon_info = get_celestial_info(jd, 1)
        
        # સમાપ્તિ સમય શોધવા માટે
        if found_tithi and tithi_type != found_tithi:
            end_time = t_check
            msg = (f"🌟 {found_tithi} એલર્ટ\n"
                   f"શરૂઆત: {tithi_start_time.strftime('%d %b, %A, %H:%M')}\n"
                   f"સમાપ્તિ: {end_time.strftime('%d %b, %A, %H:%M')}\n\n"
                   f"☀️ સૂર્ય: {sun_info}\n"
                   f"🌙 ચંદ્ર: {moon_info}\n"
                   f"તફાવત: {diff:.2f}°")
            
            requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={msg}")
            print(f"✅ એલર્ટ મોકલાયું: {found_tithi}")
            break

if __name__ == "__main__":
    run_tithi_tracker()