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

# --- 1. VERİ YÖNETİMİ ---
DB_FILE = "rota_database.json"

def veritabanini_yukle():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for u in data:
                    defaults = {'xp': 0, 'level': 1, 'ana_hedef': 'Mühendis', 'sinavlar': [], 'chat_history': [], 
                                'notes': [], 'pomo_count': 0, 'dil': 'TR', 'habits': [], 'attendance': [], 
                                'gpa_list': [], 'tema_rengi': '#4FACFE'}
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
            'password': db[u]['password'], 'ana_hedef': db[u].get('ana_hedef', 'Mühendis'),
            'egitim_duzeyi': db[u].get('egitim_duzeyi', 'Üniversite'), 'dil': db[u].get('dil', 'TR'),
            'tema_rengi': db[u].get('tema_rengi', '#4FACFE'),
            'xp': db[u].get('xp', 0), 'level': db[u].get('level', 1), 'pomo_count': db[u].get('pomo_count', 0),
            'chat_history': db[u].get('chat_history', []), 'notes': db[u].get('notes', []),
            'habits': db[u].get('habits', []), 'attendance': db[u].get('attendance', []),
            'gpa_list': db[u].get('gpa_list', []), 'sinavlar': db[u].get('sinavlar', []), 
            'data': db[u]['data'].to_dict(orient='records')
        }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=4)

if 'db' not in st.session_state: st.session_state.db = veritabanini_yukle()
if 'pomo_kalan_saniye' not in st.session_state: st.session_state.pomo_kalan_saniye = 25 * 60
if 'pomo_calisiyor' not in st.session_state: st.session_state.pomo_calisiyor = False
if 'son_guncelleme' not in st.session_state: st.session_state.son_guncelleme = time.time()

# API Ayarı
try:
    if "GEMINI_API_KEY" in st.secrets:
        API_KEY = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=API_KEY)
except:
    API_KEY = None

# --- 2. GİRİŞ KONTROLÜ ---
if 'aktif_kullanici' not in st.session_state: st.session_state.aktif_kullanici = None

if st.session_state.aktif_kullanici is None:
    st.title("🚀 ROTA AI")
    t1, t2 = st.tabs(["🔑 GİRİŞ", "📝 KAYIT"])
    with t1:
        u = st.text_input("Kullanıcı Adı")
        p = st.text_input("Şifre", type="password")
        if st.button("GİRİŞ YAP"):
            if u in st.session_state.db and st.session_state.db[u]['password'] == p:
                st.session_state.aktif_kullanici = u; st.rerun()
            else: st.error("Hatalı Giriş!")
    with t2:
        nu = st.text_input("Yeni Kullanıcı")
        np = st.text_input("Şifre Belirle", type="password")
        if st.button("HESAP OLUŞTUR"):
            if nu and np:
                st.session_state.db[nu] = {'password': np, 'xp': 0, 'level': 1, 'data': pd.DataFrame(columns=['Gün', 'Görev', 'Hedef', 'Birim', 'Yapılan']), 'habits': []}
                veritabanini_kaydet(st.session_state.db); st.success("Başarılı!")
    st.stop()

u_id = st.session_state.aktif_kullanici
u_info = st.session_state.db[u_id]
TEMA = u_info.get('tema_rengi', '#4FACFE')

# --- 3. DİNAMİK TEMA CSS ---
st.markdown(f"""
    <style>
    h1, h2, h3, .stSubheader, .stMarkdown p {{ color: {TEMA} !important; }}
    div.stButton > button:first-child {{ background-color: {TEMA} !important; color: white !important; border-radius: 8px; border: none; font-weight: bold; }}
    .stProgress > div > div > div > div {{ background-color: {TEMA} !important; }}
    [data-testid="stExpander"] {{ border: 1px solid {TEMA}; border-radius: 10px; }}
    </style>
""", unsafe_allow_html=True)

# --- 4. SIDEBAR ---
st.sidebar.title("🚀 ROTA AI")
# Renk Seçici
new_color = st.sidebar.color_picker("🎨 Tema Rengini Seç", value=TEMA)
if new_color != TEMA:
    u_info['tema_rengi'] = new_color
    veritabanini_kaydet(st.session_state.db); st.rerun()

menu = st.sidebar.radio("MENÜ", ["🏠 Panel", "📅 Sınavlar", "⏱️ Odak", "🎓 Akademik", "🤖 AI Mentor", "🏆 Başarılar", "⚙️ Ayarlar"])

if st.sidebar.button("🚪 OTURUMU KAPAT"):
    st.session_state.aktif_kullanici = None; st.rerun()

# --- 5. SAYFALAR ---

if menu == "🏠 Panel":
    st.title(f"🚀 {u_info.get('ana_hedef', 'Mühendis').upper()} PANELİ")
    
    # İstatistik Grafikleri
    if not u_info['data'].empty:
        c1, c2 = st.columns([2, 1])
        with c1:
            fig = go.Figure([go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Hedef'], name="Hedef", marker_color='#E9ECEF'),
                             go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Yapılan'], name="Yapılan", marker_color=TEMA)])
            fig.update_layout(height=300, barmode='group', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'); st.plotly_chart(fig, use_container_width=True)
        with c2:
            ty, th = u_info['data']['Yapılan'].astype(float).sum(), u_info['data']['Hedef'].astype(float).sum()
            st.plotly_chart(go.Figure(go.Pie(labels=['Biten', 'Kalan'], values=[ty, max(0, th-ty)], hole=.6, marker_colors=[TEMA, '#FF4B4B'])).update_layout(height=300, showlegend=False), use_container_width=True)

    # ALIŞKANLIKLAR (HATA DÜZELTİLDİ)
    st.divider()
    st.subheader("📊 Alışkanlık Takipçisi")
    with st.expander("➕ Yeni Alışkanlık Ekle"):
        with st.form("h_ekle_form", clear_on_submit=True):
            h_adi = st.text_input("Alışkanlık Adı")
            if st.form_submit_button("LİSTEYE EKLE"):
                if h_adi:
                    u_info['habits'].append({"Alışkanlık": h_adi, "Pzt": False, "Sal": False, "Çar": False, "Per": False, "Cum": False, "Cmt": False, "Paz": False})
                    veritabanini_kaydet(st.session_state.db); st.rerun()

    if u_info['habits']:
        h_df = pd.DataFrame(u_info['habits'])
        e_habits = st.data_editor(h_df, num_rows="dynamic", use_container_width=True, hide_index=True)
        if not h_df.equals(e_habits):
            u_info['habits'] = e_habits.to_dict(orient='records')
            veritabanini_kaydet(st.session_state.db); st.rerun()

    # GÜNLÜK TAKİP
    st.divider(); st.subheader("📝 HAFTALIK GÖREV PLANI")
    gunler = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
    for g in gunler:
        with st.expander(f"📅 {g.upper()}"):
            temp = u_info['data'][u_info['data']['Gün'] == g]
            for idx, row in temp.iterrows():
                cc1, cc2, cc3 = st.columns([3, 2, 1])
                cc1.write(f"**{row['Görev']}** ({row['Birim']})")
                y_v = cc2.number_input("Yapılan", value=int(row['Yapılan']), key=f"v_{g}_{idx}")
                if y_v != row['Yapılan']:
                    u_info['data'].at[idx, 'Yapılan'] = y_v; u_info['xp'] += 10
                    veritabanini_kaydet(st.session_state.db); st.rerun()
                if cc3.button("🗑️", key=f"d_{g}_{idx}"):
                    u_info['data'] = u_info['data'].drop(idx).reset_index(drop=True)
                    veritabanini_kaydet(st.session_state.db); st.rerun()
            with st.form(f"f_{g}", clear_on_submit=True):
                f1, f2, f3 = st.columns([2, 1, 1])
                ng, nh, nb = f1.text_input("Görev Adı"), f2.number_input("Hedef", 1), f3.selectbox("Birim", ["Soru", "Saat", "Konu"])
                if st.form_submit_button("Görevi Ekle"):
                    u_info['data'] = pd.concat([u_info['data'], pd.DataFrame([{'Gün': g, 'Görev': ng, 'Hedef': nh, 'Birim': nb, 'Yapılan': 0}])], ignore_index=True)
                    veritabanini_kaydet(st.session_state.db); st.rerun()

elif menu == "📅 Sınavlar":
    st.title("📅 SINAV TAKVİMİ")
    with st.form("ex_f", clear_on_submit=True):
        c1, c2 = st.columns(2); d_a = c1.text_input("Ders Adı"); t_a = c2.date_input("Sınav Tarihi")
        if st.form_submit_button("Takvime Ekle"):
            u_info['sinavlar'].append({'ders': d_a, 'tarih': str(t_a)})
            veritabanini_kaydet(st.session_state.db); st.rerun()
    for idx, ex in enumerate(u_info['sinavlar']):
        st.info(f"📖 {ex['ders']} | 📅 Tarih: {ex['tarih']}")

elif menu == "⏱️ Odak":
    st.title("⏱️ POMODORO ODAK MOTORU")
    dk_s = st.select_slider("Çalışma Süresi (Dakika)", options=[15, 25, 45, 60, 90], value=25)
    c1, c2, c3 = st.columns(3)
    if c1.button("🚀 BAŞLAT"):
        st.session_state.pomo_kalan_saniye = dk_s * 60; st.session_state.pomo_calisiyor = True
        st.session_state.son_guncelleme = time.time(); st.rerun()
    if c2.button("⏸️ DURDUR"): st.session_state.pomo_calisiyor = False; st.rerun()
    if c3.button("🔄 SIFIRLA"): st.session_state.pomo_calisiyor = False; st.session_state.pomo_kalan_saniye = 25*60; st.rerun()
    
    m_e, s_e = divmod(int(st.session_state.pomo_kalan_saniye), 60)
    st.markdown(f"<h1 style='text-align:center; font-size:120px; color:{TEMA};'>{m_e:02d}:{s_e:02d}</h1>", unsafe_allow_html=True)

elif menu == "🤖 AI Mentor":
    st.title("🤖 AI MENTOR ANALİZİ")
    if st.button("📊 HAFTALIK RAPOR OLUŞTUR"):
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"Benim verilerim: {u_info['data'].to_string()}. Bana bir arkadaş gibi tavsiyeler ver."
            res = model.generate_content(prompt).text
            st.info(res)
        except: st.error("API Bağlantısı Kurulamadı.")

elif menu == "🏆 Başarılar":
    st.title("🏆 BAŞARI VE RÜTBE")
    st.metric("GÜNCEL SEVİYE", f"Lvl {u_info['level']}", f"{u_info['xp']} Toplam XP")
    st.progress(min(u_info['xp'] / (u_info['level'] * 500), 1.0))
    st.caption("Bir sonraki seviye için görevleri tamamla!")

elif menu == "⚙️ Ayarlar":
    st.title("⚙️ HESAP AYARLARI")
    with st.form("set_f"):
        nm = st.text_input("Hedef Meslek / Ünvan", value=u_info['ana_hedef'])
        ns = st.text_input("Şifre Değiştir", value=u_info['password'], type="password")
        if st.form_submit_button("BİLGİLERİ GÜNCELLE"):
            u_info['ana_hedef'], u_info['password'] = nm, ns
            veritabanini_kaydet(st.session_state.db); st.success("Başarıyla Güncellendi!")

# Pomodoro Arka Plan Döngüsü
if st.session_state.pomo_calisiyor:
    simdi = time.time()
    st.session_state.pomo_kalan_saniye -= (simdi - st.session_state.son_guncelleme)
    st.session_state.son_guncelleme = simdi
    if st.session_state.pomo_kalan_saniye <= 0:
        st.session_state.pomo_calisiyor = False
        u_info['xp'] += 100; veritabanini_kaydet(st.session_state.db); st.balloons()
    time.sleep(1); st.rerun()
