import swisseph as swe
from datetime import datetime, timezone, timedelta

LAT, LON = 22.2735, 70.7513  # રાજકોટનું લોકેશન

def get_detailed_astro_data(planet_id, planet_name):
    # ૧. લાહિરી અયનાંશ સેટ કરો
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    
    # ૨. વર્તમાન સમય (IST -> UTC કન્વર્ઝન)
    now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    now_utc = now_ist - timedelta(hours=5, minutes=30)
    
    jd = swe.julday(now_utc.year, now_utc.month, now_utc.day, 
                    now_utc.hour + now_utc.minute / 60.0 + now_utc.second / 3600.0)
    
    # ૩. ટોપોસેન્ટ્રિક લોકેશન સેટ કરો
    swe.set_topo(LON, LAT, 0)
    
    # ૪. ફ્લેગ્સ (સિડેરિયલ + ટોપોસેન્ટ્રિક)
    flags = swe.FLG_SIDEREAL | swe.FLG_TOPOCTR | swe.FLG_SWIEPH
    
    res = swe.calc_ut(jd, planet_id, flags)
    total_deg = res[0][0]  # કુલ નિરયણ ડિગ્રી (0 થી 360)
    
    # ૫. રાશિ અને રાશિની ડિગ્રી ગણતરી
    rasi_idx = int(total_deg // 30) % 12
    rashis = ["મેષ", "વૃષભ", "મિથુન", "કર્ક", "સિંહ", "કન્યા", "તુલા", "વૃશ્ચિક", "ધન", "મકર", "કુંભ", "મીન"]
    rasi_deg = total_deg % 30  # રાશિની અંદરની ડિગ્રી (0° થી 30°)
    
    # ૬. નક્ષત્ર અને નક્ષત્રની ડિગ્રી ગણતરી
    nak_span = 360.0 / 27.0  # 13.333333333333334
    nak_idx = int(total_deg // nak_span) % 27
    nakshatras = ["અશ્વિની", "ભરણી", "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફાલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", "મૂળ", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદ", "ઉત્તરા ભાદ્રપદ", "રેવતી"]
    
    nak_deg = total_deg % nak_span  # નક્ષત્રની અંદરની ડિગ્રી
    pada_span = nak_span / 4.0      # 3.3333333333333335
    pada = int(nak_deg // pada_span) + 1
    
    # ૭. ફાઇનલ પ્રિન્ટ આઉટપુટ (તમે માંગ્યા મુજબ એક જ લાઈનમાં નક્ષત્ર અને ચરણ સાથે)
    print(f"--- {planet_name} ---")
    print(f"કુલ નિરયણ ડિગ્રી        : {total_deg:.2f}°")
    print(f"રાશિ                   : {rashis[rasi_idx]} (રાશિ ડિગ્રી: {rasi_deg:.2f}°)")
    print(f"નક્ષત્ર                 : {nakshatras[nak_idx]} - {pada} (નક્ષત્ર ડિગ્રી: {nak_deg:.2f}°)\n")

if __name__ == "__main__":
    get_detailed_astro_data(0, "સૂર્ય (Sun)")
    get_detailed_astro_data(1, "ચંદ્ર (Moon)")