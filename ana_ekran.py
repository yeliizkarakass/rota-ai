import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import json
import os
import google.generativeai as genai
import time
import uuid

# --- 0. TARAYICI SEKME AYARI ---
st.set_page_config(page_title="ROTA AI", page_icon="🚀", layout="wide")

# --- 1. VERİ YÖNETİMİ VE API ---
API_KEY = "AIzaSyBwTbn4D2drDRqRU1-kcyJJvHZuf4KE3gU"
genai.configure(api_key=API_KEY)
DB_FILE = "rota_database.json"
CONFIG_FILE = "user_config.json"

def veritabanini_yukle():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for u in data:
                    defaults = {
                        'xp': 0, 'level': 1, 'egitim_duzeyi': 'Üniversite', 
                        'ana_hedef': 'Gelişim', 'sinavlar': [], 'chat_history': [], 
                        'pomo_count': 0, 'habits': [], 'notes': [], 'tema_rengi': '#4FACFE'
                    }
                    for k, v in defaults.items():
                        if k not in data[u]: data[u][k] = v
                    data[u]['data'] = pd.DataFrame(data[u]['data'])
                    if 'Yapılan' not in data[u]['data'].columns: data[u]['data']['Yapılan'] = 0
                return data
        except: return {}
    return {}

def veritabanini_kaydet(db):
    to_save = {}
    for u in db:
        to_save[u] = {
            'password': db[u]['password'], 
            'ana_hedef': db[u].get('ana_hedef', 'Gelişim'),
            'egitim_duzeyi': db[u].get('egitim_duzeyi', 'Üniversite'),
            'xp': db[u].get('xp', 0), 
            'level': db[u].get('level', 1),
            'pomo_count': db[u].get('pomo_count', 0), 
            'chat_history': db[u].get('chat_history', []),
            'sinavlar': db[u].get('sinavlar', []), 
            'habits': db[u].get('habits', []),
            'notes': db[u].get('notes', []),
            'tema_rengi': db[u].get('tema_rengi', '#4FACFE'),
            'data': db[u]['data'].to_dict(orient='records')
        }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=4)

# --- 2. SESSION BAŞLATMA ---
if 'db' not in st.session_state: st.session_state.db = veritabanini_yukle()
if 'pomo_kalan_saniye' not in st.session_state: st.session_state.pomo_kalan_saniye = 25 * 60
if 'pomo_calisiyor' not in st.session_state: st.session_state.pomo_calisiyor = False
if 'son_guncelleme' not in st.session_state: st.session_state.son_guncelleme = time.time()

# --- 3. GİRİŞ KONTROLÜ ---
if 'aktif_kullanici' not in st.session_state:
    st.session_state.aktif_kullanici = None

if st.session_state.aktif_kullanici is None:
    st.markdown("<h1 style='text-align: center; color: #4FACFE;'>🚀 ROTA AI</h1>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔑 GİRİŞ", "📝 KAYIT"])
    with t1:
        u = st.text_input("Kullanıcı")
        p = st.text_input("Şifre", type="password")
        if st.button("GİRİŞ YAP"):
            if u in st.session_state.db and st.session_state.db[u]['password'] == p:
                st.session_state.aktif_kullanici = u; st.rerun()
            else: st.error("Hatalı Giriş!")
    with t2:
        nu = st.text_input("Yeni Ad")
        np = st.text_input("Yeni Şifre", type="password")
        if st.button("KAYDOL"):
            if nu not in st.session_state.db:
                st.session_state.db[nu] = {'password':np, 'xp':0, 'level':1, 'data':pd.DataFrame(columns=['Gün','Görev','Hedef','Birim','Yapılan']), 'habits':[], 'notes':[]}
                veritabanini_kaydet(st.session_state.db); st.success("Kaydolundu!")
            else: st.warning("Mevcut kullanıcı.")
    st.stop()

u_id = st.session_state.aktif_kullanici
u_info = st.session_state.db[u_id]
TEMA = u_info.get('tema_rengi', '#4FACFE')

# --- 4. CSS TEMA ---
st.markdown(f"<style>h1, h2, h3, .stSubheader {{ color: {TEMA} !important; }} div.stButton > button {{ background-color: {TEMA} !important; color: white !important; }}</style>", unsafe_allow_html=True)

# --- 5. SIDEBAR ---
st.sidebar.title("🚀 ROTA AI")
st.sidebar.metric("SEVİYE", u_info['level'], f"{u_info['xp']} XP")
yeni_tema = st.sidebar.color_picker("🎨 TEMA RENGİ", TEMA)
if yeni_tema != TEMA:
    u_info['tema_rengi'] = yeni_tema
    veritabanini_kaydet(st.session_state.db); st.rerun()

menu = st.sidebar.radio("NAVİGASYON", ["🏠 Panel", "📅 Sınavlar", "⏱️ Odak", "🏆 Başarılar", "⚙️ Ayarlar"])

# --- 6. PANEL ---
if menu == "🏠 Panel":
    st.title(f"✨ HOŞ GELDİN {u_id.upper()}")
    
    # Grafik
    if not u_info['data'].empty:
        c1, c2 = st.columns([2, 1])
        with c1:
            fig = go.Figure([go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Hedef'], name='Hedef', marker_color='#E0E0E0'),
                             go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Yapılan'], name='Yapılan', marker_color=TEMA)])
            fig.update_layout(height=250, barmode='group'); st.plotly_chart(fig, use_container_width=True)
        with c2:
            ty, th = u_info['data']['Yapılan'].sum(), u_info['data']['Hedef'].sum()
            st.plotly_chart(go.Figure(go.Pie(labels=['Biten','Kalan'], values=[ty, max(0,th-ty)], hole=.6, marker_colors=[TEMA, '#FF5252'])).update_layout(height=250, showlegend=False), use_container_width=True)

    # Alışkanlıklar
    st.divider()
    st.subheader("📊 Alışkanlık Takibi")
    with st.expander("➕ Yeni Alışkanlık Ekle"):
        h_name = st.text_input("Alışkanlık İsmi")
        if st.button("Ekle"):
            u_info['habits'].append({"Alışkanlık": h_name, "Pzt": False, "Sal": False, "Çar": False, "Per": False, "Cum": False, "Cmt": False, "Paz": False})
            veritabanini_kaydet(st.session_state.db); st.rerun()
    
    if u_info['habits']:
        h_df = pd.DataFrame(u_info['habits'])
        edited_h = st.data_editor(h_df, use_container_width=True, hide_index=True)
        if not h_df.equals(edited_h):
            u_info['habits'] = edited_h.to_dict(orient='records'); veritabanini_kaydet(st.session_state.db); st.rerun()

    # Günlük Takip
    st.divider()
    gunler = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
    for g in gunler:
        with st.expander(f"📅 {g.upper()}"):
            temp = u_info['data'][u_info['data']['Gün'] == g]
            for idx, row in temp.iterrows():
                cc1, cc2, cc3 = st.columns([3, 2, 1])
                cc1.write(f"**{row['Görev']}**")
                y_v = cc2.number_input("Yapılan", value=int(row['Yapılan']), key=f"y_{g}_{idx}")
                if y_v != row['Yapılan']:
                    u_info['xp'] += 10; u_info['data'].at[idx, 'Yapılan'] = y_v
                    veritabanini_kaydet(st.session_state.db); st.rerun()
                if cc3.button("🗑️", key=f"d_{g}_{idx}"):
                    u_info['data'] = u_info['data'].drop(idx); veritabanini_kaydet(st.session_state.db); st.rerun()
            with st.form(f"f_{g}", clear_on_submit=True):
                f1, f2, f3 = st.columns([2,1,1])
                ng, nh, nb = f1.text_input("Görev"), f2.number_input("Hedef", 1), f3.selectbox("Birim", ["Soru", "Sayfa", "Saat"])
                if st.form_submit_button("Ekle"):
                    u_info['data'] = pd.concat([u_info['data'], pd.DataFrame([{'Gün':g, 'Görev':ng, 'Hedef':nh, 'Birim':nb, 'Yapılan':0}])], ignore_index=True)
                    veritabanini_kaydet(st.session_state.db); st.rerun()

elif menu == "⏱️ Odak":
    st.title("⏱️ ODAK")
    m, s = divmod(max(0, int(st.session_state.pomo_kalan_saniye)), 60)
    st.markdown(f"<h1 style='text-align:center; font-size:100px; color:{TEMA};'>{m:02d}:{s:02d}</h1>", unsafe_allow_html=True)
    if st.button("25 DK BAŞLAT"):
        st.session_state.pomo_kalan_saniye = 25 * 60; st.session_state.pomo_calisiyor = True
        st.session_state.son_guncelleme = time.time(); st.rerun()

# --- SAYAÇ DÖNGÜSÜ ---
if st.session_state.pomo_calisiyor:
    simdi = time.time()
    st.session_state.pomo_kalan_saniye -= (simdi - st.session_state.son_guncelleme)
    st.session_state.son_guncelleme = simdi
    if st.session_state.pomo_kalan_saniye <= 0:
        st.session_state.pomo_calisiyor = False; u_info['xp'] += 50
        veritabanini_kaydet(st.session_state.db); st.balloons()
    time.sleep(1); st.rerun()
