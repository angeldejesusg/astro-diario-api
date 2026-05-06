# Astro Diario API

Backend de cálculos astrológicos precisos usando Swiss Ephemeris.

## Endpoints

### GET /health
Verifica que el servicio está funcionando.

### POST /natal
Calcula la carta natal completa.

**Body:**
```json
{
  "year": 1997,
  "month": 1,
  "day": 3,
  "hour": 16,
  "minute": 30,
  "lat": 11.5444,
  "lon": -72.9072,
  "tz_offset": -5
}
```

**Retorna:** posiciones de 10 planetas, casas (Placidus), ascendente, MC y aspectos.

### POST /transits
Calcula las posiciones planetarias de hoy y sus aspectos con la carta natal.

**Body:**
```json
{
  "natal": { "planets": { ... } }
}
```

### GET /moon
Retorna la fase lunar actual con precisión astronómica.

## Deploy en Railway

1. Conecta este repo en Railway
2. Railway detecta automáticamente el `Procfile`
3. Los archivos de efemérides se descargan durante el build

## Coordenadas de ciudades colombianas

| Ciudad | Lat | Lon |
|--------|-----|-----|
| Bogotá | 4.7110 | -74.0721 |
| Medellín | 6.2442 | -75.5812 |
| Cali | 3.4516 | -76.5320 |
| Barranquilla | 10.9685 | -74.7813 |
| Riohacha | 11.5444 | -72.9072 |
| Cartagena | 10.3910 | -75.4794 |
