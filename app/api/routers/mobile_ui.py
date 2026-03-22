from pathlib import Path
from html import unescape
import re

from fastapi import APIRouter

router = APIRouter(prefix="/api/mobile-ui", tags=["mobile-ui"])

LOGIN_TEXT = "Giriş Yap"
SIGNUP_TEXT = "Kayıt Ol"


def _read_static_file(filename: str) -> str:
    static_path = Path(__file__).parent.parent.parent.parent / "static" / filename
    if not static_path.exists():
        return ""
    return static_path.read_text(encoding="utf-8", errors="ignore")


def _extract(pattern: str, text: str, default: str = "") -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return default
    value = re.sub(r"<[^>]+>", "", match.group(1))
    value = unescape(value)
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) > 180:
        return default
    return value or default


@router.get("/login")
def login_copy():
    html = _read_static_file("login.html")

    return {
        "landing_button": _extract(r'id="btnOpenModal"[^>]*>(.*?)</button>', html, LOGIN_TEXT),
        "tab_login": _extract(r'id="btnLoginTab"[^>]*>(.*?)</button>', html, LOGIN_TEXT),
        "tab_signup": _extract(r'id="btnSignupTab"[^>]*>(.*?)</button>', html, SIGNUP_TEXT),
        "user_type_user": _extract(r'id="btnUser"[^>]*>(.*?)</button>', html, "👤 Kullanıcı"),
        "user_type_secondary": _extract(r'id="btnAdmin"[^>]*>(.*?)</button>', html, "🔐 Admin"),
        "label_username": _extract(r'<label for="username">(.*?)</label>', html, "Kullanıcı Adı"),
        "label_password": _extract(r'<label for="password">(.*?)</label>', html, "Şifre"),
        "placeholder_username": _extract(r'id="username"[^>]*placeholder="(.*?)"', html, "Kullanıcı adınızı girin"),
        "placeholder_password": _extract(r'id="password"[^>]*placeholder="(.*?)"', html, "Şifrenizi girin"),
        "button_submit_login": _extract(r'id="btnLoginSubmit"[^>]*>(.*?)</button>', html, LOGIN_TEXT),
        "demo_note": _extract(r'<p class="demo-note">(.*?)</p>', html, "Demo hesaplarla giriş yapabilirsiniz"),
        "test_accounts_title": _extract(r'font-weight:\s*700;[^>]*>(.*?)</p>', html, "📋 Test Hesapları:"),
        "test_user": "Kullanıcı: " + _extract(r'<strong>Kullanıcı:</strong>\s*([^<]+)', html, "user1 / password123"),
        "test_secondary": "Admin: " + _extract(r'<strong>Admin:</strong>\s*([^<]+)', html, "admin / admin123"),
        "test_fire": "İtfaiye: " + _extract(r'<strong>İtfaiye:</strong>\s*([^<]+)', html, "firefighter1 / password123"),
        "signup_submit": _extract(r'id="btnSignupSubmit"[^>]*>(.*?)</button>', html, SIGNUP_TEXT),
    }


@router.get("/welcome")
def welcome_copy():
    html = _read_static_file("welcome.html")
    welcome_buttons = re.findall(r'btn-welcome[^>]*>(.*?)</a>', html, flags=re.IGNORECASE | re.DOTALL)
    first_button = _extract(r'btn-welcome[^>]*>(.*?)</a>', html, "Canlı Yangın ve Risk Haritası")
    second_button = "İtfaiye Nerede?"
    if len(welcome_buttons) > 1:
        cleaned_second = re.sub(r"<[^>]+>", "", welcome_buttons[1])
        cleaned_second = unescape(re.sub(r"\s+", " ", cleaned_second)).strip()
        if cleaned_second:
            second_button = cleaned_second

    return {
        "button_map": first_button,
        "button_station": second_button,
    }


@router.get("/map")
def map_copy():
    html = _read_static_file("index.html")

    return {
        "header_title": _extract(r'<span class="title">(.*?)</span>', html, "KORU Yangın Önleme Platformu"),
        "menu_fires": _extract(r'id="mFires"[^>]*>(.*?)</a>', html, "İzmir Yangınları"),
        "menu_volunteer": _extract(r'id="mVolunteer"[^>]*>(.*?)</a>', html, "AFAD Gönüllüsü olun"),
        "menu_contact": _extract(r'id="mContact"[^>]*>(.*?)</a>', html, "Bize Ulaşın"),
        "section_fires": _extract(r'<div class="section-title">(İzmir Yangınları)</div>', html, "İzmir Yangınları"),
        "label_fire_range": _extract(r'<label for="dr">(.*?)</label>', html, "Yangın Aralığı"),
        "day_range_1": _extract(r'<option value="1">(.*?)</option>', html, "Son 24 saat"),
        "day_range_7": _extract(r'<option value="7">(.*?)</option>', html, "Son 1 hafta"),
        "btn_show": _extract(r'id="btnFires"[^>]*>(.*?)</button>', html, "Göster"),
        "btn_live": _extract(r'id="btnLiveTracking"[^>]*>(.*?)</button>', html, "🔴 Canlı Takip"),
        "btn_live_active": "🟢 Canlı Takip",
        "section_layers": _extract(r'<div class="section-title">(Risk ve Katmanlar)</div>', html, "Risk ve Katmanlar"),
        "btn_fire_risk": _extract(r'id="btnFireRisk"[^>]*>(.*?)</button>', html, "Riskli Bölgeler"),
        "btn_heatmap": _extract(r'id="btnHeatmap"[^>]*>(.*?)</button>', html, "Isıl Harita"),
        "btn_reservoirs": _extract(r'id="btnReservoirs"[^>]*>(.*?)</button>', html, "Su Rezervuarları"),
        "btn_water_sources": _extract(r'id="btnWaterSources"[^>]*>(.*?)</button>', html, "Su Kaynakları"),
        "btn_water_tanks": _extract(r'id="btnWaterTanks"[^>]*>(.*?)</button>', html, "Su Tankları"),
        "btn_lakes": _extract(r'id="btnLakes"[^>]*>(.*?)</button>', html, "Göl ve Göletler"),
        "btn_reset": _extract(r'id="btnReset"[^>]*>(.*?)</button>', html, "Sıfırla"),
        "profile_label": _extract(r'id="profileLink"[^>]*>(.*?)</a>', html, "👤 Profil").replace("👤", "").strip(),
        "logout_label": _extract(r'id="logoutLink"[^>]*>(.*?)</a>', html, "🚪 Oturum Kapat").replace("🚪", "").strip(),
        "contact_tel_label": _extract(r'<strong>(Telefon:)</strong>', html, "Telefon:"),
        "contact_tel_value": _extract(r'data-copy="([^"]+)"', html, "153"),
        "contact_fax_label": _extract(r'<strong>(Faks:)</strong>', html, "Faks:"),
        "contact_fax_value": _extract(r'data-copy="\(0232\) 293 39 95"[^>]*><span class="copy-val">(.*?)</span>', html, "(0232) 293 39 95"),
        "contact_email_label": _extract(r'<strong>(E-Posta:)</strong>', html, "E-Posta:"),
        "contact_email_value": _extract(r'href="mailto:[^"]+">(.*?)</a>', html, "him@izmir.bel.tr"),
    }
