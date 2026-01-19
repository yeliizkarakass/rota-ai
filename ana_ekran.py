import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import json
import os
import google.generativeai as genai
import time

# --- 0. AYARLAR ---
st.set_page_config(page_title="ROTA AI", page_icon="🚀", layout="wide")

# --- 1. VERİ & API ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    API_KEY = None

DB_FILE = "rota_database.json"
CONFIG_FILE = "user_config.json"

def veritabanini_yukle():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for u in data:
                    defaults = {'xp': 0, 'level': 1, 'egitim_duzeyi': 'Üniversite', 'ana_hedef': 'Gelişim', 'sinavlar': [], 'chat_history': [], 'dil': 'TR'}
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
            'password': db[u]['password'], 'ana_hedef': db[u].get('ana_hedef', 'Gelişim'),
            'egitim_duzeyi': db[u].get('egitim_duzeyi', 'Üniversite'), 'dil': db[u].get('dil', 'TR'),
            'xp': db[u].get('xp', 0), 'level': db[u].get('level', 1),
            'chat_history': db[u].get('chat_history', []), 'sinavlar': db[u].get('sinavlar', []), 
            'data': db[u]['data'].to_dict(orient='records')
        }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=4)

if 'db' not in st.session_state: st.session_state.db = veritabanini_yukle()
if 'pomo_kalan_saniye' not in st.session_state: st.session_state.pomo_kalan_saniye = 25 * 60
if 'pomo_calisiyor' not in st.session_state: st.session_state.pomo_calisiyor = False
if 'son_guncelleme' not in st.session_state: st.session_state.son_guncelleme = time.time()

# --- 2. GİRİŞ ---
if 'aktif_kullanici' not in st.session_state:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                st.session_state.aktif_kullanici = config.get('user')
        except: pass

if 'aktif_kullanici' not in st.session_state or st.session_state.aktif_kullanici is None:
    st.title("🚀 ROTA AI")
    t1, t2 = st.tabs(["🔑 GİRİŞ", "📝 KAYIT"])
    with t1:
        u = st.text_input("Kullanıcı Adı", key="l_u")
        p = st.text_input("Şifre", type="password", key="l_p")
        if st.button("GİRİŞ YAP"):
            if u in st.session_state.db and st.session_state.db[u]['password'] == p:
                st.session_state.aktif_kullanici = u
                with open(CONFIG_FILE, "w") as f: json.dump({'user': u}, f)
                st.rerun()
            else: st.error("Hatalı Giriş!")
    with t2:
        nu = st.text_input("Yeni Ad", key="r_u")
        np = st.text_input("Şifre", type="password", key="r_p")
        if st.button("KAYDOL"):
            st.session_state.db[nu] = {'password': np, 'xp': 0, 'level': 1, 'data': pd.DataFrame(columns=['Gün', 'Görev', 'Hedef', 'Birim', 'Yapılan'])}
            veritabanini_kaydet(st.session_state.db)
            st.success("Hesap Oluşturuldu!")
    st.stop()

u_id = st.session_state.aktif_kullanici
u_info = st.session_state.db[u_id]

# --- 3. SIDEBAR ---
st.sidebar.title("🚀 ROTA AI")
menu = st.sidebar.radio("MENÜ", ["🏠 Panel", "⏱️ Odak", "🤖 AI Mentor", "📅 Sınavlar", "⚙️ Ayarlar"])
if st.sidebar.button("🚪 Çıkış"):
    if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)
    st.session_state.aktif_kullanici = None
    st.rerun()

# --- 4. SAYFALAR ---
if menu == "🏠 Panel":
    st.title(f"✨ Merhaba {u_id}")
    if not u_info['data'].empty:
        c1, c2 = st.columns([2, 1])
        with c1:
            fig = go.Figure([go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Hedef'], name="Hedef"),
                             go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Yapılan'], name="Yapılan")])
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            y, h = u_info['data']['Yapılan'].astype(float).sum(), u_info['data']['Hedef'].astype(float).sum()
            st.plotly_chart(go.Figure(go.Pie(labels=['Biten', 'Kalan'], values=[y, max(0, h-y)], hole=.6)), use_container_width=True)

    st.subheader("🗓️ Haftalık Önizleme")
    gunler = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
    cols = st.columns(7)
    for i, g in enumerate(gunler):
        with cols[i]:
            st.markdown(f"<div style='background:#4FACFE; color:white; text-align:center; border-radius:5px;'>{g[:3]}</div>", unsafe_allow_html=True)
            temp = u_info['data'][u_info['data']['Gün'] == g]
            for _, r in temp.iterrows(): st.caption(f"• {r['Görev']}")

    st.divider()
    for g in gunler:
        with st.expander(f"📅 {g}"):
            temp = u_info['data'][u_info['data']['Gün'] == g]
            for idx, row in temp.iterrows():
                col1, col2, col3 = st.columns([3, 2, 1])
                col1.write(row['Görev'])
                y_val = col2.number_input("Yapılan", value=int(row['Yapılan']), key=f"v_{idx}")
                if y_val != row['Yapılan']:
                    u_info['data'].at[idx, 'Yapılan'] = y_val
                    u_info['xp'] += 10
                    veritabanini_kaydet(st.session_state.db); st.rerun()
                if col3.button("🗑️", key=f"d_{idx}"):
                    u_info['data'] = u_info['data'].drop(idx)
                    veritabanini_kaydet(st.session_state.db); st.rerun()
            with st.form(f"f_{g}", clear_on_submit=True):
                f1, f2, f3 = st.columns([2, 1, 1])
                ng, nh, nb = f1.text_input("Görev"), f2.number_input("Hedef", 1), f3.selectbox("Birim", ["Soru", "Saat", "Konu"])
                if st.form_submit_button("Ekle"):
                    u_info['data'] = pd.concat([u_info['data'], pd.DataFrame([{'Gün': g, 'Görev': ng, 'Hedef': nh, 'Birim': nb, 'Yapılan': 0}])], ignore_index=True)
                    veritabanini_kaydet(st.session_state.db); st.rerun()

elif menu == "🤖 AI Mentor":
    st.title("🤖 AI MENTOR")
    if st.button("HAFTALIK ANALİZ ✨"):
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            res = model.generate_content(f"Veriler: {u_info['data'].to_string()}. Analiz et.")
            st.info(res.text)
        except Exception as e: st.error(f"Hata: {e}")
    st.divider()
    ch = st.container(height=300)
    for m in u_info.get('chat_history', []): ch.chat_message(m['role']).write(m['text'])
    if p_m := st.chat_input("Sor..."):
        u_info['chat_history'].append({"role": "user", "text": p_m})
        try:
            res = genai.GenerativeModel('gemini-1.5-flash').generate_content(p_m)
            u_info['chat_history'].append({"role": "assistant", "text": res.text})
            veritabanini_kaydet(st.session_state.db); st.rerun()
        except: st.error("Bağlantı hatası.")

elif menu == "⏱️ Odak":
    st.title("⏱️ POMODORO")
    if not st.session_state.pomo_calisiyor:
        dk = st.slider("Dakika", 5, 120, 25)
        st.session_state.pomo_kalan_saniye = dk * 60
    c1, c2, c3 = st.columns(3)
    if c1.button("BAŞLAT"):
        st.session_state.pomo_calisiyor = True
        st.session_state.son_guncelleme = time.time()
        st.rerun()
    if c2.button("DURDUR"): st.session_state.pomo_calisiyor = False; st.rerun()
    if c3.button("SIFIRLA"): st.session_state.pomo_calisiyor = False; st.session_state.pomo_kalan_saniye = 25*60; st.rerun()
    
    if st.session_state.pomo_calisiyor:
        gecen = time.time() - st.session_state.son_guncelleme
        st.session_state.pomo_kalan_saniye -= gecen
        st.session_state.son_guncelleme = time.time()
        if st.session_state.pomo_kalan_saniye <= 0:
            st.session_state.pomo_calisiyor = False; st.balloons()
            u_info['xp'] += 30; veritabanini_kaydet(st.session_state.db)
        time.sleep(1); st.rerun()
    
    m, s = divmod(int(st.session_state.pomo_kalan_saniye), 60)
    st.header(f"{m:02d}:{s:02d}")

elif menu == "📅 Sınavlar":
    st.title("📅 SINAV TAKVİMİ")
    with st.form("exam_form"):
        d, t = st.text_input("Ders Adı"), st.date_input("Sınav Tarihi")
        if st.form_submit_button("Ekle"):
            u_info['sinavlar'].append({'ders': d, 'tarih': str(t)})
            veritabanini_kaydet(st.session_state.db); st.rerun()
    if u_info['sinavlar']:
        st.table(pd.DataFrame(u_info['sinavlar']))

elif menu == "⚙️ Ayarlar":
    st.title("⚙️ AYARLAR")
    u_info['ana_hedef'] = st.text_input("Kariyer Hedefin", u_info.get('ana_hedef', ''))
    u_info['egitim_duzeyi'] = st.selectbox("Düzey", ["Lise", "Üniversite"], index=1)
    if st.button("AYARLARI KAYDET"):
        veritabanini_kaydet(st.session_state.db)
        st.success("Kaydedildi!")
