# Project KORU

## Project Overview

KORU is an integrated, AI-driven system designed to combat the escalating frequency and intensity of wildfires in Türkiye, particularly focusing on the İzmir region. The system leverages historical fire data and detailed geospatial analysis to identify high-risk zones and determine the most efficient response strategies.

### Core Aim

The ultimate goal is to provide a powerful strategic planning tool for authorities (such as the Fire Brigade and Regional Directorate of Forestry) to optimize strategic intervention, strengthen coordination, and significantly minimize the loss of life, property, and biodiversity.

## Key Functionalities (High-Level Functionalities - HLF)

The KORU platform consists of five primary integrated modules:

1.  **Machine Learning-Based Risk Zone Modelling (HLF-1):** A validated ML model utilizes 10-year historical data to predict and classify potential wildfire risk zones.
2.  **Accessibility & Geospatial Analysis (HLF-2):** A module that assesses the accessibility (ground/air) of risk zones and maps their proximity to critical resources (water sources, fire stations).
    - **LLF-2.3: Air Accessibility Classification** - Advanced aircraft accessibility evaluation system for fire-prone areas without ground access (see [AIR_ACCESSIBILITY_README.md](AIR_ACCESSIBILITY_README.md))
3.  **Scenario-Based Route Optimization Engine (HLF-3):** Uses sophisticated algorithms (Simulated Annealing and Genetic Algorithm) to compute the fastest and safest intervention routes for user-defined fire scenarios. This aims for a ≥20% reduction in estimated response travel time compared to baseline routing.
4.  **Strategic Planning Dashboard (HLF-4):** A web-based, map-centric interface for visualizing multi-layer data (risk zones, accessibility, optimized routes) and building/saving strategic response scenarios.
5.  **Backend API, Security & Cloud Integration (HLF-5):** A secure, scalable cloud infrastructure (Azure-based) providing REST APIs, role-based access control (RBAC), and persistent data storage for all modules.

## Technical Stack

| Category | Component | Key Technologies / Requirement |
| :--- | :--- | :--- |
| **Backend & ML** | Backend Logic & Inference | Python 3.11+, FastAPI, Scikit-learn, TensorFlow/PyTorch |
| **Data Layer** | Geospatial Database | PostgreSQL + PostGIS |
| **GIS Processing** | Data Handling & Analysis | GDAL, GeoPandas, Shapely |
| **Optimization** | Algorithms | Simulated Annealing (SA), Genetic Algorithm (GA) |
| **Cloud Platform** | Infrastructure | Microsoft Azure (for scalable deployment) |
| **Security** | Authentication / Secrets | RBAC, Azure Key Vault, TLS 1.2+ encryption |

## Local Setup and Installation

### Prerequisites

To run the project locally, ensure you have the following installed:

* Git
* Docker and Docker Compose
* Python 3.11 or a compatible version

### Installation Steps

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/AliZ96/koru](https://github.com/AliZ96/koru)
    cd koru-project
    ```

2.  **Configure Environment:**
    * Create a `.env` file for local secrets and connection strings (e.g., database credentials).

3.  **Run Services via Docker Compose:**
    ```bash
    # This command builds and starts all containers (DB and Backend API)
    docker-compose up --build
    ```

4.  **Access Points:**
    * **Backend API:** `http://localhost:8000`
    * **API Documentation (Swagger):** `http://localhost:8000/docs`

## Contribution and Version Control Standards

We strictly adhere to the **GitHub Flow** integrated with JIRA for development and quality assurance.

### 1. Workflow Process

All contributions must follow a clear life cycle:

* **Pick Issue:** Select a JIRA issue and set its status to **In Progress**.
* **Fork Branch:** Create a dedicated feature branch from `main`.
* **Commit & Push:** Work locally and push changes to the remote branch.
* **Create PR:** Open a Pull Request targeting `main`.
* **Review & Merge:** The PR must undergo code review before being merged.
* **Close Issue:** Mark the JIRA issue as **Done** upon successful merge.

> **CRITICAL NOTE:** After the merge process is complete, please **DO NOT delete** the corresponding development branch. These branches must be retained as evidence for evaluation and grading purposes.

### 2. Branch Naming Convention
 
Branch names **must** be prefixed by the issue type and contain the JIRA Issue ID for automatic linking and traceability:

| Issue Type | Convention | Example |
| :--- | :--- | :--- |
| **Story / Feature** | `story/<JIRA ID>-descriptive-name` | `story/SCRUM-6-configure-readme` |
| **Task** | `task/<JIRA ID>-descriptive-name` | `task/SCRUM-7-initial-code-structure` |
| **Bug** | `bug/<JIRA ID>-descriptive-name` | `bug/SC-123-fix-login-error` |

### 3. Pull Request Requirements

* **Pull Request Title:** Must clearly state the JIRA Issue ID and summary (e.g., `[SCRUM-6] Update README.md file`).
* **Code Review:** All PRs require review by a designated reviewer (Team Leader or peer) before merging.

***
*This document serves as the single source of truth for the project's technical goals and operational standards.*
=======
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

