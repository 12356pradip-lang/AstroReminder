import swisseph as swe
from datetime import datetime, timedelta, timezone

LAT, LON = 22.2735, 70.7513

def get_accurate_astro_data(planet_id):
    # ૧. લાહિરી અયનાંશ સેટ કરો
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    
    # ૨. કરંટ ટાઈમ (IST -> UTC)
    now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    jd = swe.julday(now.year, now.month, now.day, now.hour + (now.minute / 60.0) + (now.second / 3600.0))
    
    # ૩. લોકેશન સેટ કરો
    swe.set_topo(LON, LAT, 0)
    
    # ૪. ફ્લેગ્સ (ખાસ ધ્યાન રાખો: FLG_SIDEREAL હોવો જ જોઈએ જેથી નિરયણ ડિગ્રી મળે)
    flags = swe.FLG_SIDEREAL | swe.FLG_TOPOCTR | swe.FLG_SWIEPH
    
    res = swe.calc_ut(jd, planet_id, flags)
    data = res[0][0]  # આ સિડેરિયલ (નિરયણ) ડિગ્રી છે (0 થી 360)
    
    # ૫. રાશિની ગણતરી (દર 30 ડિગ્રીએ રાશિ બદલાય)
    rasi_idx = int(data // 30) % 12
    rashis = ["મેષ", "વૃષભ", "મિથુન", "કર્ક", "સિંહ", "કન્યા", "તુલા", "વૃશ્ચિક", "ધન", "મકર", "કુંભ", "મીન"]
    
    # ૬. નક્ષત્રની ગણતરી (દર 13°20' એટલે કે 13.333333 ડિગ્રીએ નક્ષત્ર બદલાય)
    nak_span = 360.0 / 27.0  # 13.333333333333334
    nak_idx = int(data // nak_span) % 27
    nakshatras = ["અશ્વિની", "ભરણી", "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફાલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", "મૂળ", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદ", "ઉત્તરા ભાદ્રપદ", "રેવતી"]
    
    nak_deg = data % nak_span
    pada_span = nak_span / 4.0  # 3.3333333333333335
    pada = int(nak_deg // pada_span) + 1
    
    return rashis[rasi_idx], nakshatras[nak_idx], data, nak_deg, pada

if __name__ == "__main__":
    for p_id, p_name in [(0, "સૂર્ય (Sun)"), (1, "ચંદ્ર (Moon)")]:
        rasi, nak, total_deg, n_deg, pada = get_accurate_astro_data(p_id)
        print(f"--- {p_name} ---")
        print(f"કુલ નિરયણ ડિગ્રી: {total_deg:.2f}°")
        print(f"રાશિ: {rasi}")
        print(f"નક્ષત્ર: {nak} (ચરણ: {pada})")
        print(f"નક્ષત્ર ડિગ્રી: {n_deg:.2f}°\n")