import streamlit as st
import pandas as pd
import json
import os
import time
import plotly.graph_objects as go

# --- 0. AYARLAR ---
st.set_page_config(page_title="ROTA AI", page_icon="🚀", layout="wide")

# --- 1. VERİ YÖNETİMİ ---
DB_FILE = "rota_database.json"

def veritabanini_yukle():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for u in data:
                    defaults = {'xp': 0, 'level': 1, 'habits': [], 'tema_rengi': '#4FACFE', 'data': []}
                    for k, v in defaults.items():
                        if k not in data[u]: data[u][k] = v
                    data[u]['data'] = pd.DataFrame(data[u]['data'])
                return data
        except: return {}
    return {}

def veritabanini_kaydet(db):
    to_save = {}
    for u in db:
        to_save[u] = {
            'password': db[u]['password'],
            'tema_rengi': db[u].get('tema_rengi', '#4FACFE'),
            'xp': db[u].get('xp', 0),
            'level': db[u].get('level', 1),
            'habits': db[u].get('habits', []),
            'data': db[u]['data'].to_dict(orient='records')
        }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=4)

if 'db' not in st.session_state: st.session_state.db = veritabanini_yukle()

# --- 2. GİRİŞ ---
if 'aktif_kullanici' not in st.session_state: st.session_state.aktif_kullanici = None

if st.session_state.aktif_kullanici is None:
    st.title("🚀 ROTA AI")
    u = st.text_input("Kullanıcı")
    p = st.text_input("Şifre", type="password")
    if st.button("GİRİŞ YAP"):
        if u in st.session_state.db and st.session_state.db[u]['password'] == p:
            st.session_state.aktif_kullanici = u; st.rerun()
        else: st.error("Hatalı Giriş!")
    st.stop()

u_id = st.session_state.aktif_kullanici
u_info = st.session_state.db[u_id]

# --- 3. RENK PALETİ VE CSS (EN TEPEDE) ---
# Sidebar'ın en üstüne sabitledim
st.sidebar.markdown("### 🎨 GÖRÜNÜM")
yeni_renk = st.sidebar.color_picker("Tema Rengini Seç", value=u_info.get('tema_rengi', '#4FACFE'))

if yeni_renk != u_info.get('tema_rengi'):
    u_info['tema_rengi'] = yeni_renk
    veritabanini_kaydet(st.session_state.db)
    st.rerun()

TEMA = u_info['tema_rengi']

st.markdown(f"""
    <style>
    h1, h2, h3, .stSubheader {{ color: {TEMA} !important; }}
    div.stButton > button:first-child {{ background-color: {TEMA} !important; color: white !important; }}
    .stProgress > div > div > div > div {{ background-color: {TEMA} !important; }}
    </style>
""", unsafe_allow_html=True)

# --- 4. PANEL VE ALIŞKANLIKLAR ---
st.title(f"✨ HOŞ GELDİN {u_id.upper()}")

# ALIŞKANLIK EKLEME KISMI (BU SEFER ÇOK DAHA BASİT VE GARANTİ)
st.subheader("📊 Alışkanlık Takipçisi")
col_h1, col_h2 = st.columns([3, 1])

with col_h1:
    yeni_aliskanlik_adi = st.text_input("Yeni Alışkanlık Yazın...", key="new_habit_input", placeholder="Örn: 05:30 Kalkış")

with col_h2:
    st.write("##") # Hizalama için
    if st.button("➕ LİSTEYE EKLE"):
        if yeni_aliskanlik_adi:
            yeni_obj = {"Alışkanlık": yeni_aliskanlik_adi, "Pzt": False, "Sal": False, "Çar": False, "Per": False, "Cum": False, "Cmt": False, "Paz": False}
            u_info['habits'].append(yeni_obj)
            veritabanini_kaydet(st.session_state.db)
            st.success("Eklendi!")
            time.sleep(0.5)
            st.rerun()

# Listeyi Göster
if u_info['habits']:
    h_df = pd.DataFrame(u_info['habits'])
    edited_habits = st.data_editor(h_df, use_container_width=True, hide_index=True, key="habit_editor_final")
    
    if not h_df.equals(edited_habits):
        u_info['habits'] = edited_habits.to_dict(orient='records')
        veritabanini_kaydet(st.session_state.db)
        st.rerun()

if st.sidebar.button("🚪 ÇIKIŞ"):
    st.session_state.aktif_kullanici = None; st.rerun()
