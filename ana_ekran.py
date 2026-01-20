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
        "basliklar": {"takip": "📝 GÜNLÜK TAKİP", "mentor": "🤖 AI KOÇ", "sinavlar": "📅 SINAVLAR", "pomo": "⏱️ ODAK", "basari": "🏆 BAŞARILAR"},
        "labels": {"rutbe": "Rütbe"}
    },
    "EN": {
        "menu": ["🏠 Dashboard", "📊 Habits", "📅 Exams", "⏱️ Focus", "🎓 Academic", "🤖 AI Mentor", "🏆 Achievements", "⚙️ Settings"],
        "butonlar": {"baslat": "🚀 START", "durdur": "⏸️ PAUSE", "sifirla": "🔄 RESET", "analiz": "📊 ANALYZE ✨", "cikis": "🚪 LOGOUT", "ekle": "Add"},
        "basliklar": {"takip": "📝 DAILY TRACKING", "mentor": "🤖 AI COACH", "sinavlar": "📅 EXAMS", "pomo": "⏱️ FOCUS", "basari": "🏆 ACHIEVEMENTS"},
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

# --- 2. SESSION BAŞLATMA ---
if 'db' not in st.session_state: st.session_state.db = veritabanini_yukle()
if 'pomo_kalan' not in st.session_state: st.session_state.pomo_kalan = 25 * 60
if 'pomo_aktif' not in st.session_state: st.session_state.pomo_aktif = False

# --- 3. OTOMATİK GİRİŞ & GİRİŞ KONTROLÜ ---
if 'user' not in st.session_state:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                saved_user = json.load(f).get('user')
                # KRİTİK: Kullanıcı gerçekten veritabanında var mı kontrol et (KeyError engelleyici)
                if saved_user in st.session_state.db:
                    st.session_state.user = saved_user
                else:
                    st.session_state.user = None
        except: st.session_state.user = None
    else: st.session_state.user = None

if st.session_state.user is None:
    st.title("🚀 ROTA AI")
    t1, t2 = st.tabs(["🔑 GİRİŞ", "📝 KAYIT"])
    with t1:
        u_l = st.text_input("Kullanıcı Adı")
        p_l = st.text_input("Şifre", type="password")
        rem = st.checkbox("Beni Hatırla")
        if st.button("GİRİŞ YAP"):
            if u_l in st.session_state.db and st.session_state.db[u_l]['password'] == p_l:
                st.session_state.user = u_l
                if rem:
                    with open(CONFIG_FILE, "w") as f: json.dump({'user': u_l}, f)
                st.rerun()
            else: st.error("Hatalı Giriş!")
    with t2:
        nu = st.text_input("Yeni Kullanıcı")
        np = st.text_input("Yeni Şifre", type="password")
        if st.button("KAYDOL"):
            if nu and np and nu not in st.session_state.db:
                st.session_state.db[nu] = {'password': np, 'xp': 0, 'level': 1, 'data': pd.DataFrame(columns=['Gün','Görev','Hedef','Yapılan'])}
                veritabanini_kaydet(st.session_state.db); st.success("Hesap Oluşturuldu! Giriş yapın.")
    st.stop()

# --- 4. ANA UYGULAMA ---
u_info = st.session_state.db[st.session_state.user]
L = DIL_PAKETI.get(u_info['dil'], DIL_PAKETI["TR"])
TEMA = u_info.get('tema_rengi', '#4FACFE')

st.markdown(f"<style>h1, h2, h3, .stSubheader {{ color: {TEMA} !important; }} .stButton>button {{ background-color: {TEMA} !important; color: white !important; }}</style>", unsafe_allow_html=True)

# --- 5. SIDEBAR POMODORO & NOTLAR ---
st.sidebar.title("🚀 ROTA AI")
st.sidebar.metric(L["labels"]["rutbe"], mevcut_lakap_getir(u_info['level'], u_info['dil']))

with st.sidebar.container(border=True):
    st.write("⏱️ **ODAKLANMA**")
    if st.session_state.pomo_aktif:
        if st.session_state.pomo_kalan > 0:
            st.session_state.pomo_kalan -= 1
            time.sleep(1)
            st.rerun()
        else:
            st.session_state.pomo_aktif = False
            u_info['xp'] += 50
            veritabanini_kaydet(st.session_state.db); st.balloons(); st.rerun()
    
    m, s = divmod(int(st.session_state.pomo_kalan), 60)
    st.subheader(f"`{m:02d}:{s:02d}`")
    c1, c2, c3 = st.columns(3)
    if c1.button("▶️"): st.session_state.pomo_aktif = True; st.rerun()
    if c2.button("⏸️"): st.session_state.pomo_aktif = False; st.rerun()
    if c3.button("🔄"): st.session_state.pomo_aktif = False; st.session_state.pomo_kalan = 25*60; st.rerun()

menu = st.sidebar.radio("NAVİGASYON", L["menu"])

if st.sidebar.button("🚪 ÇIKIŞ"):
    if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)
    st.session_state.user = None; st.rerun()

# --- 6. SAYFALAR ---

if menu in ["🏠 Panel", "🏠 Dashboard"]:
    st.title(f"✨ HOŞ GELDİN {st.session_state.user.upper()}")
    if not u_info['data'].empty:
        fig = go.Figure([go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Hedef'], name="Hedef"),
                         go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Yapılan'], name="Biten", marker_color=TEMA)])
        st.plotly_chart(fig, use_container_width=True)

elif menu in ["📊 Alışkanlıklar", "📊 Habits"]:
    st.title("📊 Alışkanlık Takibi")
    h_df = pd.DataFrame(u_info.get('habits', []), columns=["Alışkanlık", "Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"])
    e_habits = st.data_editor(h_df, num_rows="dynamic", use_container_width=True, hide_index=True)
    if not h_df.equals(e_habits):
        u_info['habits'] = e_habits.to_dict(orient='records'); veritabanini_kaydet(st.session_state.db); st.rerun()
    st.divider()
    for _, row in e_habits.iterrows():
        tik = sum([1 for gun in ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"] if row.get(gun, False) is True])
        st.markdown(f"**{row['Alışkanlık']}**")
        st.progress(tik / 7, text=f"⭐ %{int((tik/7)*100)}")

elif menu == "🤖 AI Mentor":
    st.title("🤖 AI AKADEMİK KOÇ")
    if st.button("📊 HAFTALIK ANALİZ RAPORU OLUŞTUR"):
        model = genai.GenerativeModel('gemini-1.5-flash')
        gorevler = u_info['data'].to_string()
        res = model.generate_content(f"Hedef: {u_info['ana_hedef']}. Görev Verileri: {gorevler}. Analiz et ve tavsiye ver.").text
        st.markdown(res)
    p_m = st.chat_input("Derslerin hakkında konuş...")
    if p_m:
        res = genai.GenerativeModel('gemini-1.5-flash').generate_content(p_m).text
        st.info(res)

elif menu in ["🎓 Akademik", "🎓 Academic"]:
    t1, t2 = st.tabs(["📉 Devamsızlık", "📊 GNO"])
    with t1:
        st.subheader("Ders Katılımı")
        with st.form("at_add"):
            dn, dl = st.text_input("Ders"), st.number_input("Limit", 1, 15, 4)
            if st.form_submit_button("Ekle"):
                u_info['attendance'].append({"id": str(uuid.uuid4()), "Ders": dn, "Limit": dl, "Yapılan": 0})
                veritabanini_kaydet(st.session_state.db); st.rerun()
        for idx, c in enumerate(u_info['attendance']):
            col1, col2 = st.columns([4, 1])
            col1.write(f"**{c['Ders']}** (Limit: {c['Limit']})")
            v = st.number_input("Kaçırılan", value=c['Yapılan'], key=f"at_{idx}")
            if v != c['Yapılan']:
                u_info['attendance'][idx]['Yapılan'] = v; veritabanini_kaydet(st.session_state.db); st.rerun()
    with t2:
        st.subheader("GNO Tahmini")
        m_g = st.number_input("Mevcut GNO", 0.0, 4.0, value=float(u_info['mevcut_gano']))
        m_k = st.number_input("Toplam Kredi", 0, 300, value=int(u_info['tamamlanan_kredi']))
        if st.button("Genel Bilgileri Kaydet"):
            u_info['mevcut_gano'], u_info['tamamlanan_kredi'] = m_g, m_k
            veritabanini_kaydet(st.session_state.db); st.success("Kaydedildi!")

elif menu in ["⚙️ Ayarlar", "⚙️ Settings"]:
    st.title("⚙️ AYARLAR")
    new_theme = st.color_picker("Tema Rengi", TEMA)
    new_pw = st.text_input("Yeni Şifre", value=u_info['password'], type="password")
    if st.button("GÜNCELLE"):
        u_info['tema_rengi'], u_info['password'] = new_theme, new_pw
        veritabanini_kaydet(st.session_state.db); st.rerun()
