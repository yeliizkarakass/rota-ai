import streamlit as st
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

# --- 1. VERİ ---
DB_FILE = "rota_database.json"

# API Ayarı
try:
    if "GEMINI_API_KEY" in st.secrets:
        API_KEY = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=API_KEY)
except:
    API_KEY = None

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
        "menu": ["🏠 Panel", "📅 Sınavlar", "⏱️ Odak", "🎓 Akademik", "🤖 AI Mentor", "🏆 Başarılar", "⚙️ Ayarlar"],
        "butonlar": {"baslat": "🚀 BAŞLAT", "durdur": "⏸️ DURDUR", "sifirla": "🔄 SIFIRLA", "analiz": "📊 RAPOR OLUŞTUR", "cikis": "🚪 ÇIKIŞ", "ekle": "Ekle"},
        "basliklar": {"takip": "📝 GÜNLÜK TAKİP", "onizleme": "🗓️ Haftalık Önizleme", "mentor": "💬 MENTOR SOHBETİ", "sinavlar": "📅 SINAVLAR", "pomo": "⏱️ ODAK", "basari": "🏆 BAŞARILAR", "akademik": "🎓 AKADEMİK YÖNETİM"},
        "labels": {"hedef": "Hedef", "yapilan": "Yapılan", "birim": "Birim", "gorev": "Görev", "sifre": "Şifre", "seviye": "Eğitim Düzeyi", "rutbe": "Rütbe", "xp_durum": "XP Durumu"}
    },
    "EN": {
        "menu": ["🏠 Dashboard", "📅 Exams", "⏱️ Focus", "🎓 Academic", "🤖 AI Mentor", "🏆 Achievements", "⚙️ Settings"],
        "butonlar": {"baslat": "🚀 START", "durdur": "⏸️ PAUSE", "sifirla": "🔄 RESET", "analiz": "📊 CREATE REPORT", "cikis": "🚪 LOGOUT", "ekle": "Add"},
        "basliklar": {"takip": "📝 DAILY TRACKING", "onizleme": "🗓️ Weekly Preview", "mentor": "💬 MENTOR CHAT", "sinavlar": "📅 EXAMS", "pomo": "⏱️ FOCUS", "basari": "🏆 ACHIEVEMENTS", "akademik": "🎓 ACADEMIC MANAGEMENT"},
        "labels": {"hedef": "Target", "yapilan": "Done", "birim": "Unit", "gorev": "Task", "sifre": "Password", "seviye": "Education Level", "rutbe": "Rank", "xp_durum": "XP Status"}
    }
}

def mevcut_lakap_getir(lvl, dil):
    secili_lakap = LAKAPLAR[1].get(dil, "TR")
    for l in sorted(LAKAPLAR.keys()):
        if lvl >= l: secili_lakap = LAKAPLAR[l].get(dil, "TR")
    return secili_lakap

def veritabanini_yukle():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for u in data:
                    defaults = {'xp': 0, 'level': 1, 'ana_hedef': 'Öğrenci', 'sinavlar': [], 'chat_history': [], 'notes': [], 'pomo_count': 0, 'dil': 'TR', 'habits': [], 'attendance': [], 'gpa_list': [], 'tema_rengi': '#4FACFE', 'egitim_duzeyi': 'Lisans'}
                    for k, v in defaults.items():
                        if k not in data[u]: data[u][k] = v
                    df = pd.DataFrame(data[u]['data'])
                    for col in ['Gün', 'Görev', 'Hedef', 'Birim', 'Yapılan']:
                        if col not in df.columns: df[col] = "" if col != 'Yapılan' else 0
                    data[u]['data'] = df
                return data
        except: return {}
    return {}

def veritabanini_kaydet(db):
    to_save = {}
    for u in db:
        # Seviye Atlama Mantığı (Her 500 XP'de bir seviye)
        current_xp = db[u].get('xp', 0)
        db[u]['level'] = (current_xp // 500) + 1
        
        to_save[u] = {
            'password': db[u]['password'], 
            'ana_hedef': db[u].get('ana_hedef', 'Öğrenci'),
            'egitim_duzeyi': db[u].get('egitim_duzeyi', 'Lisans'), 
            'dil': db[u].get('dil', 'TR'),
            'tema_rengi': db[u].get('tema_rengi', '#4FACFE'),
            'xp': current_xp, 
            'level': db[u]['level'], 
            'pomo_count': db[u].get('pomo_count', 0),
            'chat_history': db[u].get('chat_history', []), 
            'notes': db[u].get('notes', []),
            'habits': db[u].get('habits', []), 
            'attendance': db[u].get('attendance', []),
            'gpa_list': db[u].get('gpa_list', []), 
            'sinavlar': db[u].get('sinavlar', []), 
            'data': db[u]['data'].to_dict(orient='records')
        }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=4)

if 'db' not in st.session_state: st.session_state.db = veritabanini_yukle()
if 'pomo_kalan_saniye' not in st.session_state: st.session_state.pomo_kalan_saniye = 25 * 60
if 'pomo_calisiyor' not in st.session_state: st.session_state.pomo_calisiyor = False
if 'son_guncelleme' not in st.session_state: st.session_state.son_guncelleme = time.time()

# --- 2. GİRİŞ & KAYIT ---
if 'aktif_kullanici' not in st.session_state:
    st.session_state.aktif_kullanici = None

if st.session_state.aktif_kullanici is None:
    st.title("🚀 ROTA AI")
    t1, t2 = st.tabs(["🔑 GİRİŞ", "📝 KAYIT"])
    with t1:
        u = st.text_input("Kullanıcı", key="l_u")
        p = st.text_input("Şifre", type="password", key="l_p")
        if st.button("GİRİŞ YAP"):
            if u in st.session_state.db and st.session_state.db[u]['password'] == p:
                st.session_state.aktif_kullanici = u
                st.rerun()
            else: st.error("Hatalı Giriş!")
    with t2:
        nu = st.text_input("Yeni Kullanıcı Adı", key="r_u")
        np = st.text_input("Şifre Belirle", type="password", key="r_p")
        ne = st.selectbox("Eğitim Düzeyi", ["Ortaokul", "Lise", "Önlisans", "Lisans", "Yüksek Lisans/Doktora"], key="r_e")
        nh = st.text_input("Okul / Bölüm / Hedef Meslek", placeholder="Örn: Bilgisayar Mühendisliği", key="r_h")
        if st.button("HESAP OLUŞTUR"):
            if nu and np:
                if nu not in st.session_state.db:
                    new_df = pd.DataFrame(columns=['Gün', 'Görev', 'Hedef', 'Birim', 'Yapılan'])
                    st.session_state.db[nu] = {
                        'password': np, 'xp': 0, 'level': 1, 
                        'ana_hedef': nh, 'egitim_duzeyi': ne,
                        'tema_rengi': '#4FACFE', 'data': new_df, 
                        'attendance': [], 'gpa_list': []
                    }
                    veritabanini_kaydet(st.session_state.db); st.success("Kayıt Başarılı!")
                else: st.warning("Kullanıcı mevcut.")
    st.stop()

u_id = st.session_state.aktif_kullanici
u_info = st.session_state.db[u_id]
L = DIL_PAKETI.get(u_info.get('dil', 'TR'), DIL_PAKETI["TR"])
TEMA = u_info.get('tema_rengi', '#4FACFE')

# Dinamik CSS Uygulama (Tema Rengi İçin)
st.markdown(f"""
    <style>
    .stButton>button {{ background-color: {TEMA}; color: white; border-radius: 8px; }}
    .stProgress > div > div > div > div {{ background-color: {TEMA}; }}
    h1, h2, h3 {{ color: {TEMA}; }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. SIDEBAR ---
st.sidebar.title("🚀 ROTA AI")
if st.session_state.pomo_calisiyor:
    simdi = time.time()
    st.session_state.pomo_kalan_saniye -= (simdi - st.session_state.son_guncelleme)
    st.session_state.son_guncelleme = simdi
    if st.session_state.pomo_kalan_saniye <= 0:
        st.session_state.pomo_calisiyor = False
        u_info['xp'] += 50; u_info['pomo_count'] += 1
        veritabanini_kaydet(st.session_state.db); st.balloons()

m_g, s_g = divmod(max(0, int(st.session_state.pomo_kalan_saniye)), 60)
st.sidebar.markdown(f"### ⏳ Sayaç: `{m_g:02d}:{s_g:02d}`")
st.sidebar.metric(L["labels"]["rutbe"], mevcut_lakap_getir(u_info['level'], u_info.get('dil', 'TR')))

menu = st.sidebar.radio("NAVİGASYON", L["menu"])

st.sidebar.subheader("📌 Hızlı Notlar")
df_n = pd.DataFrame(u_info.get('notes', []), columns=["Kategori", "Not"])
if df_n.empty: df_n = pd.DataFrame([{"Kategori": "🔵 Genel", "Not": "Not..."}])
edited_n = st.sidebar.data_editor(df_n, num_rows="dynamic", use_container_width=True, hide_index=True, key="side_notes_final")
if not df_n.equals(edited_n):
    u_info['notes'] = edited_n.to_dict(orient='records')
    veritabanini_kaydet(st.session_state.db)

if st.sidebar.button(L["butonlar"]["cikis"]):
    st.session_state.aktif_kullanici = None; st.rerun()

# --- 4. SAYFALAR ---

# PANEL
if menu in ["🏠 Panel", "🏠 Dashboard"]:
    st.title(f"✨ {u_info.get('ana_hedef', 'Öğrenci').upper()}")
    st.caption(f"🎓 {u_info.get('egitim_duzeyi', 'Lisans')}")
    
    if not u_info['data'].empty:
        c1, c2 = st.columns([2, 1])
        with c1:
            fig = go.Figure([go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Hedef'], name=L["labels"]["hedef"], marker_color='#E9ECEF'),
                             go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Yapılan'], name=L["labels"]["yapilan"], marker_color=TEMA)])
            fig.update_layout(height=300, barmode='group'); st.plotly_chart(fig, use_container_width=True)
        with c2:
            ty = u_info['data']['Yapılan'].astype(float).sum()
            th = u_info['data']['Hedef'].astype(float).sum()
            st.plotly_chart(go.Figure(go.Pie(labels=['Biten', 'Kalan'], values=[ty, max(0.1, th-ty)], hole=.6, marker_colors=[TEMA, '#FF4B4B'])).update_layout(height=300, showlegend=False), use_container_width=True)

    st.subheader(L["basliklar"]["onizleme"])
    gunler = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
    cols = st.columns(7)
    for i, g in enumerate(gunler):
        with cols[i]:
            st.markdown(f"<div style='background:{TEMA}; color:white; text-align:center; border-radius:5px; font-weight:bold; padding:5px;'>{g[:3].upper()}</div>", unsafe_allow_html=True)
            temp_g = u_info['data'][u_info['data']['Gün'] == g]
            for _, r in temp_g.iterrows(): st.caption(f"• {r['Görev']}")

    st.divider(); st.subheader(L["basliklar"]["takip"])
    for g in gunler:
        with st.expander(f"📅 {g.upper()} GÖREVLERİ"):
            temp = u_info['data'][u_info['data']['Gün'] == g]
            for idx, row in temp.iterrows():
                cc1, cc2, cc3 = st.columns([3, 2, 1])
                cc1.write(f"**{row['Görev']}**")
                y_v = cc2.number_input(L["labels"]["yapilan"], value=int(row['Yapılan']), key=f"v_{g}_{idx}")
                if y_v != row['Yapılan']:
                    u_info['data'].at[idx, 'Yapılan'] = y_v
                    u_info['xp'] += 10
                    veritabanini_kaydet(st.session_state.db); st.rerun()
                if cc3.button("🗑️", key=f"d_{g}_{idx}"):
                    u_info['data'] = u_info['data'].drop(idx).reset_index(drop=True)
                    veritabanini_kaydet(st.session_state.db); st.rerun()
            with st.form(f"f_{g}", clear_on_submit=True):
                f1, f2, f3 = st.columns([2, 1, 1])
                ng, nh, nb = f1.text_input(L["labels"]["gorev"]), f2.number_input(L["labels"]["hedef"], 1), f3.selectbox(L["labels"]["birim"], ["Soru", "Saat", "Konu"])
                if st.form_submit_button(L["butonlar"]["ekle"]):
                    u_info['data'] = pd.concat([u_info['data'], pd.DataFrame([{'Gün': g, 'Görev': ng, 'Hedef': nh, 'Birim': nb, 'Yapılan': 0}])], ignore_index=True)
                    veritabanini_kaydet(st.session_state.db); st.rerun()
     st.divider()
    st.subheader("📊 Alışkanlık Takipçisi")
    h_df = pd.DataFrame(u_info.get('habits', []), columns=["Alışkanlık", "Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"])
    if h_df.empty: h_df = pd.DataFrame([{"Alışkanlık": "05:30 Kalkış ⏰", "Pzt": False, "Sal": False, "Çar": False, "Per": False, "Cum": False, "Cmt": False, "Paz": False}])
    e_habits = st.data_editor(h_df, num_rows="dynamic", use_container_width=True, hide_index=True, key="h_editor")
    if not h_df.equals(e_habits):
        u_info['habits'] = e_habits.to_dict(orient='records'); veritabanini_kaydet(st.session_state.db)
    for _, row in e_habits.iterrows():
        tik = sum([1 for gun in ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"] if row.get(gun, False) is True])
        c_h1, c_h2 = st.columns([3, 7])
        c_h1.caption(f"**{row['Alışkanlık']}**")
        c_h2.progress(tik / 7, text=f"⭐ %{int((tik/7)*100)}")

# SINAVLAR (Kodun geri kalanı aynı mantıkla devam eder...)
elif menu in ["📅 Sınavlar", "📅 Exams"]:
    st.title(L["basliklar"]["sinavlar"])
    pdf = st.file_uploader("Sınav Takvimi PDF", type="pdf")
    if pdf and st.button("Analiz ✨"):
        st.info("AI Analiz Özelliği Aktif Ediliyor...")
    
    with st.form("ex_f", clear_on_submit=True):
        c1, c2 = st.columns(2); d_a = c1.text_input("Ders Adı"); t_a = c2.date_input("Sınav Tarihi")
        if st.form_submit_button("Ekle"):
            u_info['sinavlar'].append({'id': str(uuid.uuid4()), 'ders': d_a, 'tarih': str(t_a)})
            veritabanini_kaydet(st.session_state.db); st.rerun()

    if u_info['sinavlar']:
        for idx, ex in enumerate(u_info['sinavlar']):
            sc1, sc2, sc3 = st.columns([3, 2, 1])
            sc1.write(f"📖 **{ex['ders']}**")
            sc2.write(f"📅 {ex['tarih']}")
            if sc3.button("🗑️", key=f"ex_del_{idx}"):
                u_info['sinavlar'].pop(idx)
                veritabanini_kaydet(st.session_state.db); st.rerun()

# ODAK
elif menu in ["⏱️ Odak", "⏱️ Focus"]:
    st.title(L["basliklar"]["pomo"])
    dk_s = st.select_slider("Dakika", options=[15, 25, 45, 60, 90], value=25)
    c1, c2, c3 = st.columns(3)
    if c1.button(L["butonlar"]["baslat"]): 
        st.session_state.pomo_kalan_saniye = dk_s * 60
        st.session_state.pomo_calisiyor = True; st.session_state.son_guncelleme = time.time(); st.rerun()
    if c2.button(L["butonlar"]["durdur"]): st.session_state.pomo_calisiyor = False; st.rerun()
    if c3.button(L["butonlar"]["sifirla"]): st.session_state.pomo_calisiyor = False; st.session_state.pomo_kalan_saniye = 25*60; st.rerun()
    m_e, s_e = divmod(int(st.session_state.pomo_kalan_saniye), 60)
    st.markdown(f"<h1 style='text-align:center; font-size:150px; color:{TEMA};'>{m_e:02d}:{s_e:02d}</h1>", unsafe_allow_html=True)

# AKADEMİK
elif menu in ["🎓 Akademik", "🎓 Academic"]:
    st.title(L["basliklar"]["akademik"])
    t1, t2 = st.tabs(["📉 Devamsızlık", "📊 GNO"])
    with t1:
        st.subheader("🗓️ Ders Katılımı")
        with st.form("att_new_form"):
            c_n, c_d, c_l = st.columns([3, 2, 1])
            c_name = c_n.text_input("Ders Adı")
            c_day = c_d.selectbox("Gün", ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"])
            c_limit = c_l.number_input("Limit", 1, 20, 4)
            if st.form_submit_button("Ekle"):
                u_info['attendance'].append({"id": str(uuid.uuid4()), "Ders": c_name, "Gün": c_day, "Limit": c_limit, "Yapılan": 0})
                veritabanini_kaydet(st.session_state.db); st.rerun()
        
        for course in u_info['attendance']:
            with st.container(border=True):
                ac1, ac2, ac3 = st.columns([3, 2, 1])
                ac1.write(f"**{course['Ders']}** ({course['Gün']})")
                curr = ac2.number_input("Kaçırılan", value=course['Yapılan'], key=f"at_{course['id']}")
                if curr != course['Yapılan']:
                    course['Yapılan'] = curr; veritabanini_kaydet(st.session_state.db); st.rerun()
                if ac3.button("🗑️", key=f"del_at_{course['id']}"):
                    u_info['attendance'] = [c for c in u_info['attendance'] if c['id'] != course['id']]
                    veritabanini_kaydet(st.session_state.db); st.rerun()

# AYARLAR (Tema burada değişiyor)
elif menu in ["⚙️ Ayarlar", "⚙️ Settings"]:
    st.title("⚙️ Özelleştirme")
    with st.form("settings_f"):
        st.subheader("🎨 Görünüm")
        nt = st.color_picker("Uygulama Ana Rengi", value=TEMA)
        
        st.subheader("👤 Profil Bilgileri")
        nl = st.selectbox("Dil", ["TR", "EN"], index=0 if u_info['dil'] == 'TR' else 1)
        ne = st.selectbox("Eğitim Düzeyi", ["Ortaokul", "Lise", "Önlisans", "Lisans", "Yüksek Lisans/Doktora"], index=["Ortaokul", "Lise", "Önlisans", "Lisans", "Yüksek Lisans/Doktora"].index(u_info.get('egitim_duzeyi', 'Lisans')))
        nm = st.text_input("Bölüm / Hedef", value=u_info.get('ana_hedef', 'Öğrenci'))
        ns = st.text_input("Şifre Değiştir", value=u_info['password'], type="password")
        
        if st.form_submit_button("DEĞİŞİKLİKLERİ KAYDET"):
            u_info.update({'dil': nl, 'tema_rengi': nt, 'egitim_duzeyi': ne, 'ana_hedef': nm, 'password': ns})
            veritabanini_kaydet(st.session_state.db); st.rerun()

# BAŞARILAR ve AI MENTOR kısımlarını da benzer şekilde TEMA değişkeniyle güncelleyebilirsin.

if st.session_state.pomo_calisiyor:
    time.sleep(1); st.rerun()
