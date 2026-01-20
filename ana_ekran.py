import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import json
import os
import google.generativeai as genai
import time
import uuid

# PDF motorunu güvenli yükle
try:
    import PyPDF2
except ImportError:
    os.system('pip install PyPDF2')
    import PyPDF2

# --- 0. AYARLAR VE KALICILIK ---
st.set_page_config(page_title="ROTA AI PRO", page_icon="🚀", layout="wide")
DB_FILE = "rota_database.json"
CONFIG_FILE = "user_config.json"

# API Ayarı
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

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
        "menu": ["🏠 Panel", "📊 Alışkanlıklar", "📅 Sınavlar", "⏱️ Odak", "🎓 Akademik", "🤖 AI Mentor", "🏆 Başarılar", "⚙️ Ayarlar"],
        "butonlar": {"baslat": "🚀 BAŞLAT", "durdur": "⏸️ DURDUR", "sifirla": "🔄 SIFIRLA", "analiz": "📊 ANALİZ ET ✨", "cikis": "🚪 ÇIKIŞ", "ekle": "Ekle"},
        "labels": {"rutbe": "Rütbe"}
    },
    "EN": {
        "menu": ["🏠 Dashboard", "📊 Habits", "📅 Exams", "⏱️ Focus", "🎓 Academic", "🤖 AI Mentor", "🏆 Achievements", "⚙️ Settings"],
        "butonlar": {"baslat": "🚀 START", "durdur": "⏸️ PAUSE", "sifirla": "🔄 RESET", "analiz": "📊 ANALYZE ✨", "cikis": "🚪 LOGOUT", "ekle": "Add"},
        "labels": {"rutbe": "Rank"}
    }
}

# --- 1. FONKSİYONLAR ---

def veritabanini_yukle():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for u in data:
                    defaults = {'xp': 0, 'level': 1, 'ana_hedef': 'Öğrenci', 'sinavlar': [], 'chat_history': [], 'notes': [], 'pomo_count': 0, 'dil': 'TR', 'habits': [], 'attendance': [], 'gpa_list': [], 'mevcut_gano': 0.0, 'tamamlanan_kredi': 0, 'tema_rengi': '#4FACFE'}
                    for k, v in defaults.items():
                        if k not in data[u]: data[u][k] = v
                    if not isinstance(data[u].get('data'), pd.DataFrame):
                        data[u]['data'] = pd.DataFrame(data[u].get('data', []))
                return data
        except: return {}
    return {}

def veritabanini_kaydet(db):
    to_save = {}
    for u in db:
        u_dict = db[u].copy()
        if isinstance(u_dict['data'], pd.DataFrame):
            u_dict['data'] = u_dict['data'].to_dict(orient='records')
        to_save[u] = u_dict
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=4)
        f.flush()
        os.fsync(f.fileno())

def mevcut_lakap_getir(lvl, dil):
    secili_lakap = LAKAPLAR[1].get(dil, "TR")
    for l in sorted(LAKAPLAR.keys()):
        if lvl >= l: secili_lakap = LAKAPLAR[l].get(dil, "TR")
    return secili_lakap

# --- 2. SESSION & AUTH ---
if 'db' not in st.session_state: st.session_state.db = veritabanini_yukle()
if 'pomo_kalan' not in st.session_state: st.session_state.pomo_kalan = 25 * 60
if 'pomo_aktif' not in st.session_state: st.session_state.pomo_aktif = False

# Otomatik Giriş Kontrolü
if 'user' not in st.session_state:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            st.session_state.user = json.load(f).get('user')
    else: st.session_state.user = None

if st.session_state.user is None:
    st.title("🚀 ROTA AI")
    t1, t2 = st.tabs(["🔑 GİRİŞ", "📝 KAYIT"])
    with t1:
        u_l = st.text_input("Kullanıcı")
        p_l = st.text_input("Şifre", type="password")
        rem = st.checkbox("Beni Hatırla")
        if st.button("SİSTEME GİR"):
            if u_l in st.session_state.db and st.session_state.db[u_l]['password'] == p_l:
                st.session_state.user = u_l
                if rem:
                    with open(CONFIG_FILE, "w") as f: json.dump({'user': u_l}, f)
                st.rerun()
            else: st.error("Hatalı!")
    with t2:
        nu = st.text_input("Yeni Ad")
        np = st.text_input("Yeni Şifre", type="password")
        if st.button("HESAP OLUŞTUR"):
            if nu and np and nu not in st.session_state.db:
                st.session_state.db[nu] = {'password': np, 'xp': 0, 'level': 1, 'data': pd.DataFrame(columns=['Gün','Görev','Hedef','Yapılan'])}
                veritabanini_kaydet(st.session_state.db); st.success("Tamam! Giriş yapın.")
    st.stop()

# --- 3. ANA UYGULAMA ---
u_info = st.session_state.db[st.session_state.user]
L = DIL_PAKETI.get(u_info['dil'], DIL_PAKETI["TR"])
TEMA = u_info.get('tema_rengi', '#4FACFE')

st.markdown(f"<style>h1, h2, h3, .stSubheader {{ color: {TEMA} !important; }} .stButton>button {{ background-color: {TEMA} !important; color: white !important; }}</style>", unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.title("🚀 ROTA AI")
st.sidebar.metric(L["labels"]["rutbe"], mevcut_lakap_getir(u_info['level'], u_info['dil']))

# Pomodoro Sidebar Widget (Arka planda çalışması için geliştirildi ✨)
with st.sidebar.container(border=True):
    st.write("⏱️ **POMODORO**")
    if st.session_state.pomo_aktif:
        st.session_state.pomo_kalan -= 1
        time.sleep(1)
        if st.session_state.pomo_kalan <= 0:
            st.session_state.pomo_aktif = False
            u_info['xp'] += 50
            veritabanini_kaydet(st.session_state.db)
            st.toast("XP Kazanıldı! Pomodoro bitti.", icon="🎉")
        st.rerun()
    
    m, s = divmod(int(st.session_state.pomo_kalan), 60)
    st.subheader(f"`{m:02d}:{s:02d}`")
    c1, c2 = st.columns(2)
    if c1.button("▶️"): st.session_state.pomo_aktif = True; st.rerun()
    if c2.button("⏸️"): st.session_state.pomo_aktif = False; st.rerun()

menu = st.sidebar.radio("NAVİGASYON", L["menu"])

if st.sidebar.button("🚪 ÇIKIŞ"):
    if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)
    st.session_state.user = None; st.rerun()

# --- SAYFALAR ---

if menu in ["🏠 Panel", "🏠 Dashboard"]:
    st.title(f"✨ HOŞ GELDİN {st.session_state.user.upper()}")
    # Görev Tablosu
    if not u_info['data'].empty:
        st.plotly_chart(go.Figure([go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Hedef'], name="Hedef"),
                                   go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Yapılan'], name="Biten")]), use_container_width=True)
    
    with st.expander("➕ Yeni Görev Ekle"):
        with st.form("g_add"):
            c1, c2, c3 = st.columns([2,1,1])
            g_n = c1.text_input("Görev")
            g_h = c2.number_input("Hedef", 1)
            g_d = c3.selectbox("Gün", ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"])
            if st.form_submit_button("Listeye Ekle"):
                yeni = pd.DataFrame([{'Gün': g_d, 'Görev': g_n, 'Hedef': g_h, 'Yapılan': 0}])
                u_info['data'] = pd.concat([u_info['data'], yeni], ignore_index=True)
                veritabanini_kaydet(st.session_state.db); st.rerun()

elif menu in ["📊 Alışkanlıklar", "📊 Habits"]:
    st.title("📊 Alışkanlık Takibi")
    h_df = pd.DataFrame(u_info.get('habits', []), columns=["Alışkanlık", "Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"])
    edited = st.data_editor(h_df, num_rows="dynamic", use_container_width=True)
    if not h_df.equals(edited):
        u_info['habits'] = edited.to_dict(orient='records'); veritabanini_kaydet(st.session_state.db)

elif menu in ["🎓 Akademik", "🎓 Academic"]:
    t1, t2 = st.tabs(["📉 Devamsızlık", "📊 GNO"])
    with t1:
        st.subheader("Ders Katılımı")
        # (Devamsızlık kodun buraya mühürlü)
    with t2:
        st.subheader("GNO Tahmini")
        m_gano = st.number_input("Mevcut GNO", 0.0, 4.0, value=float(u_info['mevcut_gano']))
        if st.button("Kaydet"):
            u_info['mevcut_gano'] = m_gano; veritabanini_kaydet(st.session_state.db)

elif menu == "🤖 AI Mentor":
    st.title("🤖 AI AKADEMİK KOÇ")
    if st.button("📊 HAFTALIK ANALİZ RAPORU OLUŞTUR"):
        res = genai.GenerativeModel('gemini-1.5-flash').generate_content(f"Analiz et: {u_info['data'].to_string()}").text
        st.markdown(res)
    # Chat kısmı
    p_m = st.chat_input("Sor...")
    if p_m:
        res = genai.GenerativeModel('gemini-1.5-flash').generate_content(p_m).text
        st.write(res)

elif menu in ["⚙️ Ayarlar", "⚙️ Settings"]:
    st.title("⚙️ AYARLAR")
    new_theme = st.color_picker("Tema Rengi", TEMA)
    if st.button("TEMA UYGULA"):
        u_info['tema_rengi'] = new_theme; veritabanini_kaydet(st.session_state.db); st.rerun()

