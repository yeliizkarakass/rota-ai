import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import json
import os
import google.generativeai as genai
import time

# --- 0. AYARLAR & CSS ---
st.set_page_config(page_title="ROTA AI", page_icon="🚀", layout="wide")

# Sidebar ve genel arayüz düzeltmeleri için CSS
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {padding-top: 2rem;}
        .st-emotion-cache-16q9sum {font-size: 1.2rem; font-weight: bold;}
        .main-title {font-size: 2.5rem; font-weight: bold; margin-bottom: 1rem;}
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
                    # Eksik anahtarları tamamla
                    defaults = {'xp': 0, 'level': 1, 'egitim_duzeyi': 'Üniversite', 'ana_hedef': 'Gelişim', 'sinavlar': [], 'chat_history': [], 'pomo_count': 0, 'dil': 'TR'}
                    for k, v in defaults.items():
                        if k not in data[u]: data[u][k] = v
                    # DataFrame dönüşümü
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
            'pomo_count': db[u].get('pomo_count', 0), 'chat_history': db[u].get('chat_history', []),
            'sinavlar': db[u].get('sinavlar', []), 'data': db[u]['data'].to_dict(orient='records')
        }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=4)

# --- 2. SİSTEM BAŞLATMA ---
if 'db' not in st.session_state: st.session_state.db = veritabanini_yukle()
if 'pomo_kalan_saniye' not in st.session_state: st.session_state.pomo_kalan_saniye = 25 * 60
if 'pomo_calisiyor' not in st.session_state: st.session_state.pomo_calisiyor = False
if 'son_guncelleme' not in st.session_state: st.session_state.son_guncelleme = time.time()

# --- 3. GİRİŞ KONTROLÜ ---
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
        u = st.text_input("Kullanıcı", key="login_u")
        p = st.text_input("Şifre", type="password", key="login_p")
        hatirla = st.checkbox("Beni Hatırla")
        if st.button("GİRİŞ YAP"):
            if u in st.session_state.db and st.session_state.db[u]['password'] == p:
                st.session_state.aktif_kullanici = u
                if hatirla:
                    with open(CONFIG_FILE, "w") as f: json.dump({'user': u}, f)
                st.rerun()
            else: st.error("Kullanıcı adı veya şifre hatalı!")
    with t2:
        nu = st.text_input("Yeni Kullanıcı Adı", key="reg_u")
        np = st.text_input("Şifre", type="password", key="reg_p")
        if st.button("KAYDOL"):
            if nu and np:
                st.session_state.db[nu] = {'password': np, 'xp': 0, 'level': 1, 'data': pd.DataFrame(columns=['Gün', 'Görev', 'Hedef', 'Birim', 'Yapılan'])}
                veritabanini_kaydet(st.session_state.db)
                st.success("Başarıyla kaydoldunuz! Giriş yapabilirsiniz.")
    st.stop()

u_id = st.session_state.aktif_kullanici
u_info = st.session_state.db[u_id]

# --- 4. SIDEBAR ---
st.sidebar.title("🚀 ROTA AI")
st.sidebar.divider()
st.sidebar.write(f"👤 **Kullanıcı:** {u_id}")
st.sidebar.write(f"📈 **Level:** {u_info['level']} | **XP:** {u_info['xp']}")

menu = st.sidebar.radio("MENÜ", ["🏠 Panel", "⏱️ Odak", "🤖 AI Mentor", "📅 Sınavlar", "⚙️ Ayarlar"])

if st.sidebar.button("🚪 Çıkış Yap"):
    if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)
    st.session_state.aktif_kullanici = None
    st.rerun()

# --- 5. SAYFALAR ---

# --- PANEL ---
if menu == "🏠 Panel":
    st.markdown(f"<div class='main-title'>Hoş geldin, {u_id.upper()}!</div>", unsafe_allow_html=True)
    
    if not u_info['data'].empty:
        c1, c2 = st.columns([2, 1])
        with c1:
            fig = go.Figure([go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Hedef'], name="Hedef", marker_color='#E0E0E0'),
                             go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Yapılan'], name="Yapılan", marker_color='#4FACFE')])
            fig.update_layout(height=300, barmode='group')
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            yapilan = u_info['data']['Yapılan'].astype(float).sum()
            hedef = u_info['data']['Hedef'].astype(float).sum()
            fig_pie = go.Figure(go.Pie(labels=['Yapılan', 'Kalan'], values=[yapilan, max(0, hedef-yapilan)], hole=.6))
            fig_pie.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()
    gunler = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
    for g in gunler:
        with st.expander(f"📅 {g}"):
            temp = u_info['data'][u_info['data']['Gün'] == g]
            for idx, row in temp.iterrows():
                col1, col2, col3 = st.columns([3, 2, 1])
                col1.write(f"**{row['Görev']}** ({row['Birim']})")
                y_yeni = col2.number_input("Yapılan", value=int(row['Yapılan']), key=f"inp_{idx}")
                if y_yeni != row['Yapılan']:
                    u_info['data'].at[idx, 'Yapılan'] = y_yeni
                    u_info['xp'] += 10
                    veritabanini_kaydet(st.session_state.db)
                    st.rerun()
                if col3.button("🗑️", key=f"del_{idx}"):
                    u_info['data'] = u_info['data'].drop(idx)
                    veritabanini_kaydet(st.session_state.db)
                    st.rerun()
            
            with st.form(key=f"add_{g}"):
                f1, f2, f3 = st.columns([2,1,1])
                ng = f1.text_input("Görev")
                nh = f2.number_input("Hedef", min_value=1)
                nb = f3.selectbox("Birim", ["Soru", "Konu", "Saat", "Sayfa"])
                if st.form_submit_button("Ekle"):
                    yeni_satir = pd.DataFrame([{'Gün': g, 'Görev': ng, 'Hedef': nh, 'Birim': nb, 'Yapılan': 0}])
                    u_info['data'] = pd.concat([u_info['data'], yeni_satir], ignore_index=True)
                    veritabanini_kaydet(st.session_state.db)
                    st.rerun()

# --- AI MENTOR ---
elif menu == "🤖 AI Mentor":
    st.title("🤖 AI MENTOR")
    
    tab1, tab2 = st.tabs(["📊 Haftalık Analiz", "💬 Mentor Sohbet"])
    
    with tab1:
        st.subheader("Haftalık Performans Analizi")
        if st.button("Haftamı Analiz Et ✨"):
            with st.spinner("Analiz ediliyor..."):
                try:
                    # Model isimlerini deneme mekanizması (404 hatasını önlemek için)
                    model_names = ['gemini-1.5-flash', 'gemini-pro']
                    success = False
                    for m_name in model_names:
                        try:
                            model = genai.GenerativeModel(m_name)
                            prompt = f"Sen bir eğitim koçusun. Kullanıcı verileri: {u_info['data'].to_string()}. Başarıyı yorumla ve 3 tavsiye ver."
                            response = model.generate_content(prompt)
                            st.info(response.text)
                            success = True
                            break
                        except: continue
                    if not success: st.error("Google AI modellerine şu an ulaşılamıyor.")
                except Exception as e:
                    st.error(f"Bir hata oluştu: {e}")

    with tab2:
        chat_container = st.container(height=400)
        with chat_container:
            for m in u_info.get('chat_history', []):
                st.chat_message(m['role']).write(m['text'])
        
        if prompt := st.chat_input("Mentoruna bir şey sor..."):
            u_info['chat_history'].append({"role": "user", "text": prompt})
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                res = model.generate_content(prompt)
                u_info['chat_history'].append({"role": "assistant", "text": res.text})
                veritabanini_kaydet(st.session_state.db)
                st.rerun()
            except: st.error("Mesaj iletilemedi.")

# --- ODAK (POMODORO) ---
elif menu == "⏱️ Odak":
    st.title("⏱️ Odaklanma Zamanı")
    if not st.session_state.pomo_calisiyor:
        p_dakika = st.slider("Süre Seç (Dakika)", 5, 120, 25)
        st.session_state.pomo_kalan_saniye = p_dakika * 60
    
    c1, c2, c3 = st.columns(3)
    if c1.button("🚀 Başlat", use_container_width=True):
        st.session_state.pomo_calisiyor = True
        st.session_state.son_guncelleme = time.time()
        st.rerun()
    if c2.button("⏸️ Durdur", use_container_width=True):
        st.session_state.pomo_calisiyor = False
        st.rerun()
    if c3.button("🔄 Sıfırla", use_container_width=True):
        st.session_state.pomo_calisiyor = False
        st.session_state.pomo_kalan_saniye = 25 * 60
        st.rerun()

    if st.session_state.pomo_calisiyor:
        gecen = time.time() - st.session_state.son_guncelleme
        st.session_state.pomo_kalan_saniye -= gecen
        st.session_state.son_guncelleme = time.time()
        if st.session_state.pomo_kalan_saniye <= 0:
            st.session_state.pomo_calisiyor = False
            st.balloons()
            st.success("Odaklanma süresi bitti! +30 XP")
            u_info['xp'] += 30
            veritabanini_kaydet(st.session_state.db)
        time.sleep(1)
        st.rerun()

    m, s = divmod(int(st.session_state.pomo_kalan_saniye), 60)
    st.markdown(f"<h1 style='text-align:center; font-size:100px;'>{m:02d}:{s:02d}</h1>", unsafe_allow_html=True)

# --- SINAVLAR ---
elif menu == "📅 Sınavlar":
    st.title("📅 Sınav Takvimi")
    # Manuel sınav ekleme
    with st.form("exam_form"):
        d, t = st.text_input("Ders Adı"), st.date_input("Sınav Tarihi")
        if st.form_submit_button("Sınav Ekle"):
            u_info['sinavlar'].append({'ders': d, 'tarih': str(t)})
            veritabanini_kaydet(st.session_state.db)
            st.rerun()
    
    for s in u_info['sinavlar']:
        st.warning(f"📌 **{s['ders']}** - {s['tarih']}")

# --- AYARLAR ---
elif menu == "⚙️ Ayarlar":
    st.title("⚙️ Ayarlar")
    u_info['ana_hedef'] = st.text_input("Ana Hedefin", u_info.get('ana_hedef', ''))
    u_info['egitim_duzeyi'] = st.selectbox("Eğitim Düzeyi", ["Lise", "Üniversite", "Yüksek Lisans"], index=1)
    if st.button("Kaydet"):
        veritabanini_kaydet(st.session_state.db)
        st.success("Ayarlar kaydedildi!")
