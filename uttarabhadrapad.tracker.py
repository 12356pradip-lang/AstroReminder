import swisseph as swe
from datetime import datetime, timedelta
import os

# કોન્ફિગરેશન
LAT, LON = 22.2735, 70.7513
HISTORY_FILE = "pushkar_specials_history.txt"

def format_dms(deg):
    d = int(deg); m = int((deg - d) * 60); s = int(((deg - d) * 60 - m) * 60)
    return f"{d}°{m}'{s}\""

def get_astro_position(planet_id, target_time):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(target_time.year, target_time.month, target_time.day, target_time.hour + target_time.minute/60.0 + 5.5)
    swe.set_topo(LON, LAT, 0)
    data = swe.calc_ut(jd, planet_id, swe.FLG_SIDEREAL | swe.FLG_TOPOCTR)[0][0]
    if planet_id == 1: data = (data - 2.9) % 360 # ચંદ્ર માટે ઓફસેટ
    
    # રાશિ અને ડિગ્રીની ગણતરી
    rasi_idx = int(data // 30)
    rasi_name = ["મેષ", "વૃષભ", "મિથુન", "કર્ક", "સિંહ", "કન્યા", "તુલા", "વૃશ્ચિક", "ધન", "મકર", "કુંભ", "મીન"][rasi_idx]
    
    nakshatras = ["અશ્વિની", "ભરણી", "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફાલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", "મૂળ", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદ", "ઉત્તરા ભાદ્રપદ", "રેવતી"]
    nak_name = nakshatras[int(data // 13.333333333333334) % 27]
    
    return rasi_name, data % 30, nak_name

def get_transition_details(p_id, target_nak):
    start = datetime.utcnow()
    for i in range(0, 48 * 60, 15):
        t = start + timedelta(minutes=i)
        r_name, r_deg, n_name = get_astro_position(p_id, t)
        if n_name == target_nak:
            entry_time = t + timedelta(hours=5, minutes=30)
            # પ્રવેશ સમયની રાશિ અને ડિગ્રી
            entry_rasi, entry_deg, _ = r_name, r_deg, n_name
            
            # નિર્ગમન શોધવું
            for j in range(i, 48 * 60, 15):
                t_exit = start + timedelta(minutes=j)
                _, _, n_exit = get_astro_position(p_id, t_exit)
                if n_exit != target_nak:
                    exit_time = t_exit + timedelta(hours=5, minutes=30)
                    return entry_time, exit_time, entry_rasi, entry_deg
            break
    return None, None, None, None

def run_tracker():
    target_nak = "ઉત્તરા ભાદ્રપદ"
    for p_id in [0, 1]:
        name = "સૂર્ય" if p_id == 0 else "ચંદ્ર"
        entry_t, exit_t, rasi, deg = get_transition_details(p_id, target_nak)
        
        if entry_t and entry_t > datetime.utcnow() and entry_t < (datetime.utcnow() + timedelta(hours=24)):
            alert_id = f"{target_nak}_{name}_{entry_t.strftime('%Y%m%d_%H')}"
            if not os.path.exists(HISTORY_FILE) or alert_id not in open(HISTORY_FILE).read():
                msg = (f"🌟 એડવાન્સ એલર્ટ: {target_nak} - {name}\n"
                       f"આગામી ૨૪ કલાકમાં {name} આ નક્ષત્રમાં પ્રવેશ કરશે.\n"
                       f"પ્રવેશ સમય: {entry_t.strftime('%d %b, %H:%M')}\n"
                       f"પ્રવેશ સ્થિતિ: {rasi} રાશિમાં {format_dms(deg)}\n"
                       f"નિર્ગમન સમય: {exit_t.strftime('%d %b, %H:%M')}")
                
                print(msg)
                with open(HISTORY_FILE, "a") as f: f.write(alert_id + "\n")

if __name__ == "__main__":
    run_tracker()