import swisseph as swe
from datetime import datetime, timedelta, timezone

LAT, LON = 22.2735, 70.7513

def test_astro_position(planet_id, planet_name):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    jd = swe.julday(now.year, now.month, now.day, now.hour + (now.minute / 60.0) + (now.second / 3600.0) + 5.5)
    
    swe.set_topo(LON, LAT, 0)
    flags = swe.FLG_SIDEREAL | swe.FLG_TOPOCTR | swe.FLG_SWIEPH
    data = swe.calc_ut(jd, planet_id, flags)[0][0]
    
    rasi_idx = int(data // 30)
    rashis = ["મેષ", "વૃષભ", "મિથુન", "કર્ક", "સિંહ", "કન્યા", "તુલા", "વૃશ્ચિક", "ધન", "મકર", "કુંભ", "મીન"]
    
    nak_idx = int(data // 13.333333333333334)
    nakshatras = ["અશ્વિની", "ભરણી", "કૃતિકા", "રોહિણી", "મૃગશીર્ષ", "આર્દ્રા", "પુનર્વસુ", "પુષ્ય", "આશ્લેષા", "મઘા", "પૂર્વા ફાલ્ગુની", "ઉત્તરા ફાલ્ગુની", "હસ્ત", "ચિત્રા", "સ્વાતિ", "વિશાખા", "અનુરાધા", "જ્યેષ્ઠા", "મૂળ", "પૂર્વાષાઢા", "ઉત્તરાષાઢા", "શ્રવણ", "ધનિષ્ટા", "શતભિષા", "પૂર્વા ભાદ્રપદ", "ઉત્તરા ભાદ્રપદ", "રેવતી"]
    
    nak_deg = data % 13.333333333333334
    pada = int(nak_deg // 3.3333333333333335) + 1
    
    print(f"--- {planet_name} ટેસ્ટ રિઝલ્ટ ---")
    print(f"તારીખ/સમય: {now.strftime('%d %b %Y, %H:%M')}")
    print(f"રાશિ: {rashis[rasi_idx]}")
    print(f"નક્ષત્ર: {nakshatras[nak_idx % 27]}")
    print(f"ચરણ: {pada}")
    print(f"નક્ષત્ર ડિગ્રી: {nak_deg:.2f}°\n")

if __name__ == "__main__":
    test_astro_position(0, "સૂર્ય")
    test_astro_position(1, "ચંદ્ર")