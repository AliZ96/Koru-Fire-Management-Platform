# Lokal OSRM Kurulumu

GA 2.0 karayolu mesafesi ve yol geometrisi icin lokal OSRM kullanir. Bu ucretsizdir; rota istekleri kendi bilgisayarindaki Docker servisine gider.

## 1. Klasor

Repo kokunde:

```powershell
cd C:\Users\admin\Desktop\yenikoruProject\koru
mkdir osrm-data
```

## 2. OSM verisi

Izmir veya Turkiye `.osm.pbf` dosyasini `osrm-data` klasorune koy. Dosya adini kolaylik icin soyle yap:

```text
osrm-data\izmir-latest.osm.pbf
```

## 3. OSRM dosyalarini hazirla

```powershell
docker run --rm -t -v ${PWD}\osrm-data:/data osrm/osrm-backend osrm-extract -p /opt/car.lua /data/izmir-latest.osm.pbf
docker run --rm -t -v ${PWD}\osrm-data:/data osrm/osrm-backend osrm-partition /data/izmir-latest.osrm
docker run --rm -t -v ${PWD}\osrm-data:/data osrm/osrm-backend osrm-customize /data/izmir-latest.osrm
```

## 4. OSRM server'i baslat

```powershell
docker compose -f docker-compose.osrm.yml up
```

Backend `.env` icinde sunlar olmali:

```env
OSRM_BASE_URL=http://127.0.0.1:5000
OSRM_PROFILE=driving
```

## 5. Test

Tarayicida veya PowerShell'de:

```text
http://127.0.0.1:5000/nearest/v1/driving/27.14,38.42
```

`code: Ok` donuyorsa GA 2.0 hazir.
