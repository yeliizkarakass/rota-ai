İmport streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import json
import os
import google.generativeai as genai
import time
import uuid

# --- 0. AYARLAR ---
st.set_page_config(page_title="ROTA AI", page_icon="🚀", layout="wide")

# --- 1. VERİ YÖNETİMİ ---
DB_FILE = "rota_database.json"

LAKAPLAR = {
    1: {"TR": "Meraklı Yolcu 🚶", "EN": "Curious Traveler 🚶"},
    4: {"TR": "Disiplin Kurucu 🏗️", "EN": "Discipline Builder 🏗️"},
    8: {"TR": "Odak Ustası 🎯", "EN": "Focus Master 🎯"},
    13: {"TR": "Strateji Dehası 🧠", "EN": "Strategy Genius 🧠"},
    20: {"TR": "Vizyoner Lider 👑", "EN": "Visionary Leader 👑"},
    36: {"TR": "Zirve Mimarı 🏔️", "EN": "Summit Architect 🏔️"},
    50: {"TR": "Efsane 🌟", "EN": "Legend 🌟"}
}

DIL_PAKETI = {
    "TR": {
        "menu": ["🏠 Panel", "📅 Sınavlar", "⏱️ Odak", "🎓 Akademik", "🏆 Başarılar", "🤖 AI Mentor", "⚙️ Ayarlar"],
        "butonlar": {"baslat": "🚀 BAŞLAT", "durdur": "⏸️ DURDUR", "sifirla": "🔄 SIFIRLA", "ekle": "Ekle", "kaydet": "Kaydet", "cikis": "🚪 ÇIKIŞ"},
        "basliklar": {"takip": "📝 GÜNLÜK TAKİP", "onizleme": "🗓️ Haftalık Önizleme", "sinavlar": "📅 SINAV TAKVİMİ", "pomo": "⏱️ ODAK", "akademik": "🎓 AKADEMİK YÖNETİM", "aliskanlik": "📊 ALIŞKANLIK TAKİPÇİSİ", "basari": "🏆 BAŞARI KÜRSÜSÜ"},
        "labels": {"hedef": "Hedef", "yapilan": "Yapılan", "birim": "Birim", "gorev": "Görev", "rutbe": "Rütbe", "tema": "Hızlı Tema"}
    },
    "EN": {
        "menu": ["🏠 Dashboard", "📅 Exams", "⏱️ Focus", "🎓 Academic", "🏆 Achievements", "🤖 AI Mentor", "⚙️ Settings"],
        "butonlar": {"baslat": "🚀 START", "durdur": "⏸️ PAUSE", "sifirla": "🔄 RESET", "ekle": "Add", "kaydet": "Save", "cikis": "🚪 LOGOUT"},
        "basliklar": {"takip": "📝 DAILY TRACKING", "onizleme": "🗓️ Weekly Preview", "sinavlar": "📅 EXAM SCHEDULE", "pomo": "⏱️ FOCUS", "akademik": "🎓 ACADEMIC MANAGEMENT", "aliskanlik": "📊 HABIT TRACKER", "basari": "🏆 HALL OF FAME"},
        "labels": {"hedef": "Target", "yapilan": "Done", "birim": "Unit", "gorev": "Task", "rutbe": "Rank", "tema": "Quick Theme"}
    }
}

def veritabanini_yukle():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for u in data:
                    defaults = {'xp': 0, 'level': 1, 'ana_hedef': 'Öğrenci', 'sinavlar': [], 'notes': [], 'pomo_count': 0, 'dil': 'TR', 'habits': [], 'attendance': [], 'gpa_list': [], 'tema_rengi': '#4FACFE', 'egitim_duzeyi': 'Lisans', 'mevcut_gno': 0.0, 'toplam_kredi': 0}
                    for k, v in defaults.items():
                        if k not in data[u]: data[u][k] = v
                    data[u]['data'] = pd.DataFrame(data[u]['data'])
                return data
        except: return {}
    return {}

def veritabanini_kaydet(db):
    to_save = {}
    for u in db:
        current_xp = db[u].get('xp', 0)
        db[u]['level'] = (current_xp // 500) + 1
        user_copy = db[u].copy()
        if isinstance(user_copy['data'], pd.DataFrame):
            user_copy['data'] = user_copy['data'].to_dict(orient='records')
        to_save[u] = user_copy
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=4)

if 'db' not in st.session_state: st.session_state.db = veritabanini_yukle()
if 'pomo_kalan_saniye' not in st.session_state: st.session_state.pomo_kalan_saniye = 25 * 60
if 'pomo_calisiyor' not in st.session_state: st.session_state.pomo_calisiyor = False
if 'son_guncelleme' not in st.session_state: st.session_state.son_guncelleme = time.time()

if 'aktif_kullanici' not in st.session_state: st.session_state.aktif_kullanici = None

# --- GİRİŞ & KAYIT ---
if st.session_state.aktif_kullanici is None:
    st.title("🚀 ROTA AI")
    t1, t2 = st.tabs(["🔑 GİRİŞ", "📝 KAYIT"])
    with t1:
        u = st.text_input("Kullanıcı")
        p = st.text_input("Şifre", type="password")
        if st.button("GİRİŞ YAP"):
            if u in st.session_state.db and st.session_state.db[u]['password'] == p:
                st.session_state.aktif_kullanici = u
                st.rerun()
            else: st.error("Hatalı Giriş!")
    with t2:
        nu = st.text_input("Yeni Kullanıcı Adı")
        np = st.text_input("Şifre Belirle", type="password")
        if st.button("HESAP OLUŞTUR"):
            if nu and np and nu not in st.session_state.db:
                st.session_state.db[nu] = {'password': np, 'xp': 0, 'level': 1, 'ana_hedef': 'Öğrenci', 'data': pd.DataFrame(columns=['Gün', 'Görev', 'Hedef', 'Birim', 'Yapılan']), 'dil': 'TR', 'tema_rengi': '#4FACFE', 'habits': [], 'notes': [], 'mevcut_gno': 0.0, 'toplam_kredi': 0, 'pomo_count': 0}
                veritabanini_kaydet(st.session_state.db)
                st.success("Kayıt Başarılı!")
    st.stop() bu kismin tamamini duxelt at kullanici verilerini kaydetsin surekli kayit olmami istemesin beni hatirla tusu olsun kayit kisminda Kullanıcı adi sifre meslek seviye sorsun kullanici da veri değiştirdiginde sitede tekrar baska bi ghn girdiginde veriler kaydedilmis olsun