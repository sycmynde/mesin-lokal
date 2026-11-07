#!/usr/bin/env bash
# aqi_om.sh — fallback Open-Meteo: update per jam + multi-polutan
LAT=-6.24; LON=106.99
curl -s "https://air-quality-api.open-meteo.com/v1/air-quality?latitude=$LAT&longitude=$LON&current=pm2_5,pm10,ozone,us_aqi" | jq -r '
  .current as $c
  | def sub25: ($c.pm2_5//0) | if .<=12 then 4.17*. elif .<=35.4 then 50+2.14*(.-12) elif .<=55.4 then 100+2.5*(.-35.4) else 150+0.53*(.-55.4) end;
    def sub10: ($c.pm10//0)  | if .<=54 then 0.93*. elif .<=154 then 50+0.5*(.-54) elif .<=254 then 100+0.5*(.-154) else 150+0.5*(.-254) end;
    "Waktu  : $$c.time) UTC (WIB = +7)",
    "PM2.5  : $$c.pm2_5) µg/m³  sub-AQI ≈ $sub25|round)",
    "PM10   : $$c.pm10) µg/m³  sub-AQI ≈ $sub10|round)",
    "US AQI : $$c.us_aqi)",
    if sub10 > sub25 then "Dominan: PM10 — debu kasar, tanda tangan abu vulkanik 🌋"
    else "Dominan: PM2.5 — polusi halus biasa" end'
