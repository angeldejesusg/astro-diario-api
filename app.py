from flask import Flask, request, jsonify
from flask_cors import CORS
import swisseph as swe
import math
from datetime import datetime, timezone
import os

app = Flask(__name__)
CORS(app)

# Configurar ruta de datos de Swiss Ephemeris
swe.set_ephe_path('/app/ephe')

PLANETS = {
    'Sol':      swe.SUN,
    'Luna':     swe.MOON,
    'Mercurio': swe.MERCURY,
    'Venus':    swe.VENUS,
    'Marte':    swe.MARS,
    'Júpiter':  swe.JUPITER,
    'Saturno':  swe.SATURN,
    'Urano':    swe.URANUS,
    'Neptuno':  swe.NEPTUNE,
    'Plutón':   swe.PLUTO,
}

SIGNS = [
    'Aries', 'Tauro', 'Géminis', 'Cáncer',
    'Leo', 'Virgo', 'Libra', 'Escorpio',
    'Sagitario', 'Capricornio', 'Acuario', 'Piscis'
]

SIGN_SYMBOLS = ['♈','♉','♊','♋','♌','♍','♎','♏','♐','♑','♒','♓']

def deg_to_sign(deg):
    deg = deg % 360
    sign_idx = int(deg / 30)
    deg_in_sign = deg % 30
    return {
        'sign': SIGNS[sign_idx],
        'symbol': SIGN_SYMBOLS[sign_idx],
        'degree': round(deg_in_sign, 2),
        'absolute': round(deg, 2)
    }

def get_julian_day(year, month, day, hour=12, minute=0, tz_offset=0):
    # Convert local time to UT
    ut_hour = hour + minute/60 - tz_offset
    jd = swe.julday(year, month, day, ut_hour)
    return jd

def calc_planets(jd):
    positions = {}
    for name, planet_id in PLANETS.items():
        result, _ = swe.calc_ut(jd, planet_id)
        positions[name] = deg_to_sign(result[0])
        positions[name]['speed'] = round(result[3], 4)
        positions[name]['retrograde'] = result[3] < 0
    return positions

def calc_houses(jd, lat, lon):
    houses, ascmc = swe.houses(jd, lat, lon, b'P')  # Placidus
    house_list = []
    for i, cusp in enumerate(houses):
        house_list.append({
            'house': i + 1,
            **deg_to_sign(cusp)
        })
    ascendant = deg_to_sign(ascmc[0])
    mc = deg_to_sign(ascmc[1])
    return house_list, ascendant, mc

def calc_aspects(positions):
    aspect_types = {
        0:   {'name': 'Conjunción',  'orb': 8,  'nature': 'neutral'},
        60:  {'name': 'Sextil',      'orb': 6,  'nature': 'armónico'},
        90:  {'name': 'Cuadratura',  'orb': 8,  'nature': 'tenso'},
        120: {'name': 'Trígono',     'orb': 8,  'nature': 'armónico'},
        150: {'name': 'Quincuncio',  'orb': 3,  'nature': 'tenso'},
        180: {'name': 'Oposición',   'orb': 8,  'nature': 'tenso'},
    }
    aspects = []
    planet_names = list(positions.keys())
    for i in range(len(planet_names)):
        for j in range(i+1, len(planet_names)):
            p1, p2 = planet_names[i], planet_names[j]
            deg1 = positions[p1]['absolute']
            deg2 = positions[p2]['absolute']
            diff = abs(deg1 - deg2)
            if diff > 180:
                diff = 360 - diff
            for angle, info in aspect_types.items():
                orb = abs(diff - angle)
                if orb <= info['orb']:
                    aspects.append({
                        'planet1': p1,
                        'planet2': p2,
                        'aspect': info['name'],
                        'angle': angle,
                        'orb': round(orb, 2),
                        'nature': info['nature']
                    })
    return aspects

def moon_phase(jd):
    sun, _ = swe.calc_ut(jd, swe.SUN)
    moon, _ = swe.calc_ut(jd, swe.MOON)
    angle = (moon[0] - sun[0]) % 360
    if angle < 45:    phase, emoji = 'Luna Nueva', '🌑'
    elif angle < 90:  phase, emoji = 'Creciente', '🌒'
    elif angle < 135: phase, emoji = 'Cuarto Creciente', '🌓'
    elif angle < 180: phase, emoji = 'Gibosa Creciente', '🌔'
    elif angle < 225: phase, emoji = 'Luna Llena', '🌕'
    elif angle < 270: phase, emoji = 'Gibosa Menguante', '🌖'
    elif angle < 315: phase, emoji = 'Cuarto Menguante', '🌗'
    else:             phase, emoji = 'Menguante', '🌘'
    illumination = round((1 - math.cos(math.radians(angle))) / 2 * 100, 1)
    return {'phase': phase, 'emoji': emoji, 'angle': round(angle, 2), 'illumination': illumination}

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'astro-diario-api'})

@app.route('/natal', methods=['POST'])
def natal_chart():
    """
    Calculates a full natal chart.
    Body: { year, month, day, hour, minute, lat, lon, tz_offset }
    """
    try:
        data = request.json
        year     = int(data['year'])
        month    = int(data['month'])
        day      = int(data['day'])
        hour     = int(data.get('hour', 12))
        minute   = int(data.get('minute', 0))
        lat      = float(data['lat'])
        lon      = float(data['lon'])
        tz_offset = float(data.get('tz_offset', -5))  # Colombia UTC-5

        jd = get_julian_day(year, month, day, hour, minute, tz_offset)
        planets = calc_planets(jd)
        houses, ascendant, mc = calc_houses(jd, lat, lon)
        aspects = calc_aspects(planets)

        return jsonify({
            'julian_day': jd,
            'planets': planets,
            'houses': houses,
            'ascendant': ascendant,
            'mc': mc,
            'aspects': aspects,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/transits', methods=['POST'])
def daily_transits():
    """
    Calculates today's planetary positions and aspects with natal chart.
    Body: { natal: { planets, ascendant }, date_str (optional) }
    """
    try:
        data = request.json
        natal = data.get('natal', {})

        # Today's positions
        now = datetime.now(timezone.utc)
        jd_today = swe.julday(now.year, now.month, now.day, now.hour + now.minute/60)
        today_planets = calc_planets(jd_today)
        today_moon = moon_phase(jd_today)

        # Aspects between transits and natal
        transit_aspects = []
        if natal.get('planets'):
            for t_name, t_pos in today_planets.items():
                for n_name, n_pos in natal['planets'].items():
                    diff = abs(t_pos['absolute'] - n_pos['absolute'])
                    if diff > 180:
                        diff = 360 - diff
                    for angle, info in {
                        0: ('Conjunción', 6, 'neutral'),
                        60: ('Sextil', 4, 'armónico'),
                        90: ('Cuadratura', 6, 'tenso'),
                        120: ('Trígono', 6, 'armónico'),
                        180: ('Oposición', 6, 'tenso'),
                    }.items():
                        orb = abs(diff - angle)
                        if orb <= info[1]:
                            transit_aspects.append({
                                'transit_planet': t_name,
                                'natal_planet': n_name,
                                'aspect': info[0],
                                'orb': round(orb, 2),
                                'nature': info[2]
                            })

        return jsonify({
            'date': now.strftime('%Y-%m-%d'),
            'planets': today_planets,
            'moon': today_moon,
            'transit_aspects': transit_aspects
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/moon', methods=['GET'])
def moon_today():
    now = datetime.now(timezone.utc)
    jd = swe.julday(now.year, now.month, now.day, now.hour + now.minute/60)
    return jsonify(moon_phase(jd))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
