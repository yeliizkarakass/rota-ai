import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import json
import os
import google.generativeai as genai
import time

# --- 0. AYARLAR & STİL ---
st.set_page_config(page_title="ROTA AI", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e0e0e0; }
    .main-title { font-size: 32px; font-weight: 800; color: #1e1e1e; margin-bottom: 20px; }
    .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

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
                    defaults = {'xp': 0, 'level': 1, 'egitim_duzeyi': 'Üniversite', 'ana_hedef': 'Mühendislik Başarısı', 'sinavlar': [], 'chat_history': [], 'dil': 'TR'}
                    for k, v in defaults.items():
                        if k not in data[u]: data[u][k] = v
                    df = pd.DataFrame(data[u]['data'])
                    for col in ['Gün', 'Görev', 'Hedef', 'Birim', 'Yapılan']:
                        if col not in df.columns: df[col] = 0 if col == 'Yapılan' else ""
                    data[u]['data'] = df
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

# --- 2. GİRİŞ KONTROL ---
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
        if st.button("SİSTEME GİRİŞ"):
            if u in st.session_state.db and st.session_state.db[u]['password'] == p:
                st.session_state.aktif_kullanici = u
                with open(CONFIG_FILE, "w") as f: json.dump({'user': u}, f)
                st.rerun()
            else: st.error("Hatalı Giriş!")
    with t2:
        nu = st.text_input("Yeni Ad", key="r_u")
        np = st.text_input("Şifre", type="password", key="r_p")
        if st.button("HESAP OLUŞTUR"):
            st.session_state.db[nu] = {'password': np, 'xp': 0, 'level': 1, 'data': pd.DataFrame(columns=['Gün', 'Görev', 'Hedef', 'Birim', 'Yapılan'])}
            veritabanini_kaydet(st.session_state.db)
            st.success("Hesap Oluşturuldu!")
    st.stop()

u_id = st.session_state.aktif_kullanici
u_info = st.session_state.db[u_id]

# --- 3. SIDEBAR (DÜZELTİLMİŞ) ---
st.sidebar.markdown(f"### 🚀 ROTA AI\n**{u_id.upper()}**")
st.sidebar.progress(min(u_info['xp'] / (u_info['level'] * 200), 1.0))
st.sidebar.caption(f"Lvl {u_info['level']} | {u_info['xp']} XP")
st.sidebar.divider()
menu = st.sidebar.radio("MENÜ", ["🏠 Panel", "⏱️ Odak", "🤖 AI Mentor", "📅 Sınavlar", "⚙️ Ayarlar"], label_visibility="collapsed")
st.sidebar.divider()
if st.sidebar.button("🚪 Güvenli Çıkış", use_container_width=True):
    if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)
    st.session_state.aktif_kullanici = None
    st.rerun()

# --- 4. SAYFALAR ---

if menu == "🏠 Panel":
    st.markdown(f"<div class='main-title'>Hoş Geldin, Mühendis {u_id}</div>", unsafe_allow_html=True)
    
    # İstatistikler
    if not u_info['data'].empty:
        c1, c2 = st.columns([2, 1])
        with c1:
            fig = go.Figure([go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Hedef'], name="Hedef", marker_color='#E9ECEF'),
                             go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Yapılan'], name="Yapılan", marker_color='#007BFF')])
            fig.update_layout(height=280, barmode='group', margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            y, h = u_info['data']['Yapılan'].astype(float).sum(), u_info['data']['Hedef'].astype(float).sum()
            fig_p = go.Figure(go.Pie(labels=['Tamamlanan', 'Kalan'], values=[y, max(0, h-y)], hole=.7, marker_colors=['#007BFF', '#FF4B4B']))
            fig_p.update_layout(height=280, showlegend=False, margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig_p, use_container_width=True)

    # Haftalık Görünüm
    st.subheader("🗓️ Haftalık Plan")
    gunler = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
    cols = st.columns(7)
    for i, g in enumerate(gunler):
        with cols[i]:
            st.markdown(f"<div style='background:#007BFF; color:white; text-align:center; padding:5px; border-radius:5px; font-weight:bold;'>{g[:3]}</div>", unsafe_allow_html=True)
            temp = u_info['data'][u_info['data']['Gün'] == g]
            for _, r in temp.iterrows(): st.caption(f"• {r['Görev']}")

    # Görev Yönetimi
    st.divider()
    for g in gunler:
        with st.expander(f"📅 {g} GÖREVLERİ"):
            temp = u_info['data'][u_info['data']['Gün'] == g]
            for idx, row in temp.iterrows():
                col1, col2, col3 = st.columns([4, 2, 1])
                col1.write(f"**{row['Görev']}**")
                y_val = col2.number_input("Yapılan", value=int(row['Yapılan']), key=f"p_{idx}")
                if y_val != row['Yapılan']:
                    u_info['data'].at[idx, 'Yapılan'] = y_val
                    u_info['xp'] += 10
                    if u_info['xp'] >= (u_info['level'] * 200): u_info['level'] += 1; st.balloons()
                    veritabanini_kaydet(st.session_state.db); st.rerun()
                if col3.button("🗑️", key=f"d_{idx}"):
                    u_info['data'] = u_info['data'].drop(idx)
                    veritabanini_kaydet(st.session_state.db); st.rerun()
            
            with st.form(key=f"form_{g}", clear_on_submit=True):
                f1, f2, f3 = st.columns([3, 1, 1])
                ng = f1.text_input("Yeni Görev")
                nh = f2.number_input("Hedef", min_value=1)
                nb = f3.selectbox("Birim", ["Soru", "Konu", "Saat", "Sayfa"])
                if st.form_submit_button("Ekle"):
                    u_info['data'] = pd.concat([u_info['data'], pd.DataFrame([{'Gün': g, 'Görev': ng, 'Hedef': nh, 'Birim': nb, 'Yapılan': 0}])], ignore_index=True)
                    veritabanini_kaydet(st.session_state.db); st.rerun()

elif menu == "🤖 AI Mentor":
    st.title("🤖 AI MENTOR")
    t1, t2 = st.tabs(["📊 HAFTALIK ANALİZ", "💬 MENTOR SOHBET"])
    
    with t1:
        if st.button("ANALİZ RAPORU OLUŞTUR ✨", use_container_width=True):
            with st.spinner("Verileriniz işleniyor..."):
                try:
                    # En stabil model çağrısı
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    res = model.generate_content(f"Sen bir mentor koçusun. Veriler: {u_info['data'].to_string()}. Analiz et.")
                    st.info(res.text)
                except: st.error("AI şu an meşgul, lütfen daha sonra deneyin.")

    with t2:
        chat_h = st.container(height=400)
        with chat_h:
            for m in u_info.get('chat_history', []): st.chat_message(m['role']).write(m['text'])
        if p_m := st.chat_input("Mentorunla konuş..."):
            u_info['chat_history'].append({"role": "user", "text": p_m})
            try:
                res = genai.GenerativeModel('gemini-1.5-flash').generate_content(p_m)
                u_info['chat_history'].append({"role": "assistant", "text": res.text})
                veritabanini_kaydet(st.session_state.db); st.rerun()
            except: st.error("Bağlantı Hatası!")

elif menu == "⏱️ Odak":
    st.title("⏱️ ODAK SAYAÇ")
    if not st.session_state.pomo_calisiyor:
        dk = st.select_slider("Süre (Dakika)", options=[15, 25, 45, 60, 90], value=25)
        st.session_state.pomo_kalan_saniye = dk * 60
    
    col1, col2, col3 = st.columns(3)
    if col1.button("🚀 BAŞLAT", use_container_width=True): st.session_state.pomo_calisiyor = True; st.session_state.son_guncelleme = time.time(); st.rerun()
    if col2.button("⏸️ DURDUR", use_container_width=True): st.session_state.pomo_calisiyor = False; st.rerun()
    if col3.button("🔄 SIFIRLA", use_container_width=True): st.session_state.pomo_calisiyor = False; st.session_state.pomo_kalan_saniye = 25*60; st.rerun()

    if st.session_state.pomo_calisiyor:
        gecen = time.time() - st.session_state.son_guncelleme
        st.session_state.pomo_kalan_saniye -= gecen
        st.session_state.son_guncelleme = time.time()
        if st.session_state.pomo_kalan_saniye <= 0:
            st.session_state.pomo_calisiyor = False; st.balloons()
            u_info['xp'] += 30; veritabanini_kaydet(st.session_state.db)
        time.sleep(1); st.rerun()

    m, s = divmod(int(st.session_state.pomo_kalan_saniye), 60)
    st.markdown(f"<h1 style='text-align:center; font-size:120px; color:#007BFF;'>{m:02d}:{s:02d}</h1>", unsafe_allow_html=True)

elif menu == "📅 Sınavlar":
    st.title("📅 SINAV TAKVİMİ")
    
    # Profesyonel Giriş Formu
    with st.container(border=True):
        st.subheader("Yeni Sınav Ekle")
        with st.form("exam_pro"):
            c1, c2, c3 = st.columns(3)
            ders = c1.text_input("Ders Adı")
            tarih = c2.date_input("Sınav Tarihi")
            notlar = c3.text_input("Küçük Not (Opsiyonel)")
            if st.form_submit_button("Takvime İşle"):
                u_info['sinavlar'].append({'ders': ders, 'tarih': str(tarih), 'not': notlar})
                veritabanini_kaydet(st.session_state.db); st.rerun()

    # Profesyonel Tablo Görünümü
    if u_info['sinavlar']:
        st.divider()
        df_sinav = pd.DataFrame(u_info['sinavlar'])
        df_sinav.columns = ["DERS ADI", "TARİH", "NOTLAR"]
        st.table(df_sinav)
        
        if st.button("Tüm Sınav Listesini Temizle"):
            u_info['sinavlar'] = []; veritabanini_kaydet(st.session_state.db); st.rerun()
    else:
        st.info("Henüz eklenmiş bir sınav yok. Mühendislik hayatında başarılar!")

elif menu == "⚙️ Ayarlar":
    st.title("⚙️ KULLANICI AYARLARI")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Profil Bilgileri")
        u_info['ana_hedef'] = st.text_input("Kariyer Hedefin", u_info.get('ana_hedef', ''))
        u_info['egitim_duzeyi'] = st.selectbox("Eğitim Seviyesi", ["Lise", "Üniversite (Lisans)", "Yüksek Lisans / Doktora"], index=1)
        u_info['dil'] = st.radio("Uygulama Dili", ["TR", "EN"], horizontal=True)
    
    with col2:
        st.subheader("Sistem Durumu")
        st.write(f"📂 Veritabanı: **Aktif**")
        st.write(f"🔑 API Durumu: **{'Bağlı' if API_KEY else 'Bağlantı Yok'}**")
        st.write(f"💾 Dosya: `rota_database.json`")

    if st.button("DEĞİŞİKLİKLERİ KAYDET", use_container_width=True):
        veritabanini_kaydet(st.session_state.db)
        st.success("Ayarlar başarıyla güncellendi!")
