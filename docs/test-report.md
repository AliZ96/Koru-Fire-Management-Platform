# Test Report

## Health Check
- Endpoint: `GET /health/db`
- Result: **200 OK**
- Response: `{"ok": true, "db": "connected"}`
- Environment: Local (PostgreSQL `koru_db`, uvicorn on http://127.0.0.1:8001)
- Date: (02.01.2025 - 18:34)

## Auth API
- Register: `POST /auth/user/register`
  - Request body: `{"username":"e2e-user1","password":"secret123"}`
  - Result: **200 OK**
  - Response: access_token (JWT), `token_type: bearer`
  - Environment: Local (PostgreSQL `koru_db`, uvicorn on http://127.0.0.1:8001)
  - Date: (02.01.2025 - 18:34)

- Login: `POST /auth/user/login`
  - Request body: `{"username":"e2e-user1","password":"secret123"}`
  - Result: **200 OK**
  - Response: access_token (JWT), `token_type: bearer`
  - Environment: Local (PostgreSQL `koru_db`, uvicorn on http://127.0.0.1:8001)
  - Date: (02.01.2025 - 18:34)

- Login (invalid creds): `POST /auth/user/login`
  - Request body: `{"username":"e2e-user1","password":"wrongpass"}`
  - Result: **401 Unauthorized**
  - Response: `{"detail":"Invalid credentials"}`
  - Environment: Local (PostgreSQL `koru_db`, uvicorn on http://127.0.0.1:8001)
  - Date: (02.01.2025 - 18:34)

## Static Data Endpoints
- Dams: `GET /api/dams` → **200 OK**, `FeatureCollection`, features > 0
- Water Sources: `GET /api/water_sources` → **200 OK**, `FeatureCollection`, features > 0
- Water Tanks: `GET /api/water_tanks` → **200 OK**, `FeatureCollection`, features > 0
- Environment: Local (PostgreSQL `koru_db`, uvicorn on http://127.0.0.1:8001)
- Date: (02.01.2025 - 18:34)

## Wind
- `GET /api/wind?lat=38.5&lon=27.1` → **200 OK**, response includes `speed_ms` and `deg`
- Environment: Local (PostgreSQL `koru_db`, uvicorn on http://127.0.0.1:8001)
- Date: (02.01.2025 - 18:34)

## FIRMS (fires)
- `GET /api/fires?day_range=1` → **200 OK**, FeatureCollection returned (MAP_KEY present)
- Sample feature: `{"coordinates":[26.92892, 38.73064],"props":{"acq_date":"2026-01-02","frp":"0.93","confidence":"n","satellite":"N","instrument":"VIIRS"}}`
- Environment: Local (PostgreSQL `koru_db`, uvicorn on http://127.0.0.1:8001)
- Date: (02.01.2025 - 18:50)

## Frontend (manual)
- Signup (browser, `/login` → Signup tab): yeni kullanıcı ile kayıt → `/welcome` sayfasına yönlendirildi, oturum bilgisi sessionStorage’da.
- Login (browser, `/login` → Login tab): doğru kullanıcı/parola ile `/welcome`’a geçti; hatalı parola ile hata mesajı gösterildi, yönlendirme olmadı.
- Environment: Browser (local), backend http://127.0.0.1:8001, DB koru_db (PostgreSQL)
- Date: (02.01.2025 - 18:52)

## Water Sources Layer
- API: `GET /api/water_sources` → **200 OK**, FeatureCollection, features > 0 (kaynak: `static/data/water-sources.geojson`)
- UI: Haritada “Su Kaynakları” katmanı açıldığında marker’lar/popuplar göründü, hata yok.
- Environment: Local (PostgreSQL `koru_db`, uvicorn on http://127.0.0.1:8001), Browser
- Date: (02.01.2025 - 18:54)

## Dams Layer
- API: `GET /api/dams` → **200 OK**, FeatureCollection, features > 0 (kaynak: `static/data/barajlar.geojson`)
- UI: “Su Rezervuarları” katmanı açıldığında poligon/marker ve popup’lar göründü, hata yok.
- Environment: Local (PostgreSQL `koru_db`, uvicorn on http://127.0.0.1:8001), Browser
- Date: (02.01.2025 - 18:56)

## Water Tanks Layer
- API: `GET /api/water_tanks` → **200 OK**, FeatureCollection, features > 0 (kaynak: `static/data/water-tank.geojson`)
- UI: “Su tankları” katmanı açıldığında marker/popup göründü, hata yok.
- Environment: Local (PostgreSQL `koru_db`, uvicorn on http://127.0.0.1:8001), Browser
- Date: (02.01.2025 - 20:00)

## Risk & Heatmap (Not Integrated)
- Riskli bölgeler ve ısıl harita özellikleri şu anda sistemde entegre/aktif değil. Bu kısım demo kapsamı dışında ve test edilmedi.
