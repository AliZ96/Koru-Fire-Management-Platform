# KORU Yangın Önleme Platformu

İzmir ilinde yangın riskinin izlenmesi ve yönetilmesi için geliştirilmiş gerçek zamanlı, harita tabanlı bir karar destek sistemidir.

Bu proje, bitirme projesi kapsamında geliştirilmiş olup yangın risk analizi, kullanıcı yönetimi ve rol bazlı erişim kontrolü içermektedir.

---

## Özellikler

- 🗺️ İzmir Haritası: Leaflet.js tabanlı interaktif harita
- 🔥 Yangın Algılama: NASA FIRMS uydu verileri ile gerçek zamanlı yangın tespiti
- 💧 Barajlar: OpenStreetMap Overpass API ile baraj ve su kaynaklarını gösterme
- 🏢 Toplanma Alanları: İzmir ilindeki toplanma alanlarının haritalanması
- 🌪️ Rüzgâr Analizi: Gerçek zamanlı rüzgâr verisi ve yangın yayılım tahmini
- ⚠️ Risk Haritası: Wind-aligned risk grid ile yangın risk analizi
- 🛡️ Uydu Haritası: Esri ArcGIS uydu görüntüleri desteği
- 👤 Kullanıcı Yönetimi: Kullanıcı, İtfaiyeci ve Admin rolleri
- 🔐 Kimlik Doğrulama: JWT tabanlı authentication sistemi

---

## Teknoloji Stack

- Backend: FastAPI (Python)
- Frontend: Leaflet.js, D3.js, XLSX.js
- Harita Servisleri: OpenStreetMap, Esri ArcGIS
- Uydu Verisi: NASA FIRMS API, Overpass API
- Hava Durumu: Open-Meteo API
- Veritabanı: PostgreSQL
- ORM: SQLAlchemy
- Kimlik Doğrulama: JWT (JSON Web Token)
- API Testleri: Postman

---

## Kurulum

### Gereksinimler

- Python 3.11+
- pip
- Virtual Environment
- PostgreSQL
- pgAdmin (önerilir)

---

### Kurulum Adımları

1. Repository’yi klonlayın  
git clone https://github.com/bbgmfun/koru_bitirme.git  
cd koru_bitirme  

2. Virtual environment oluşturun ve aktif edin  
python -m venv venv  
venv\Scripts\activate  

3. Bağımlılıkları yükleyin  
pip install -r requirements.txt  

4. PostgreSQL üzerinde veritabanını oluşturun  
CREATE DATABASE koru_db;  

5. Veritabanı tablolarını oluşturun  
Windows için (psql yolu PATH’te değilse):

"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d koru_db -f database/schema.sql  

Alternatif olarak pgAdmin üzerinden:  
- koru_db → Query Tool  
- database/schema.sql içeriğini yapıştır  
- Execute (F5)

6. Ortam değişkenlerini ayarlayın (.env)  
DATABASE_URL=postgresql+psycopg2://postgres:SIFRE@localhost:5432/koru_db  
JWT_SECRET_KEY=degistirilecek_secret  

7. Uygulamayı çalıştırın  
uvicorn app.main:app --reload  

8. Tarayıcıdan erişin  
http://localhost:8000  

---

## Proje Yapısı

KORU_BITIRME/
├── app/
│   ├── main.py
│   ├── auth/
│   ├── models/
│   ├── repositories/
│   ├── services/
│   └── db/                (SQLAlchemy bağlantı ve session kodları)
├── static/
│   ├── index.html
│   ├── login.html
│   └── data/
├── data/
│   └── firms.json
├── database/
│   └── schema.sql         (manuel veritabanı kurulum dosyası)
├── .env.example
├── requirements.txt
└── README.md

---

## Veritabanı Yapısı

Veritabanı şeması manuel olarak `database/schema.sql` dosyasında tanımlıdır.

Bu dosya sadece tablo ve index tanımlarını içerir.  
Gerçek veriler, kullanıcı bilgileri veya şifreler repository içerisinde yer almaz.

Tablolar `IF NOT EXISTS` kullanılarak tanımlandığı için dosya tekrar tekrar güvenle çalıştırılabilir.

---

## Kimlik Doğrulama ve Roller

Sistem JWT tabanlı kimlik doğrulama kullanır.

Roller:
- USER: Standart kullanıcı
- FIREFIGHTER: İtfaiyeci
- ADMIN: Yönetici

Tüm kullanıcılar API üzerinden register edilerek oluşturulur.  
Repository içerisinde sabit kullanıcı adı veya şifre bulunmaz.

---

## API Endpoints (Özet)

- GET /health/db
- POST /auth/user/register
- POST /auth/user/login
- POST /auth/firefighter/register
- POST /auth/firefighter/login
- GET /auth/me
- GET /api/fires
- GET /api/wind
- GET /api/spread
- GET /api/risk

---

## Postman API Testleri

Base URL:  
http://127.0.0.1:8000

Test edilen senaryolar:
- Kullanıcı kayıt ve giriş
- İtfaiyeci kayıt ve giriş
- JWT token üretimi
- Token doğrulama (/auth/me)
- Rol bazlı erişim kontrolü
- Veritabanı bağlantı kontrolü

Örnek test akışı:
- POST /auth/firefighter/register
- POST /auth/firefighter/login
- GET /auth/me (Authorization: Bearer token)

Tüm testler Postman kullanılarak başarıyla gerçekleştirilmiştir.

---

## Veri Kaynakları

- NASA FIRMS – Yangın algılama verileri
- OpenStreetMap – Coğrafi veriler
- Open-Meteo – Rüzgâr ve hava durumu
- İzmir Büyükşehir Belediyesi – Toplanma alanları

---

## Lisans

Bu proje eğitim amaçlı geliştirilmiştir.
