import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import json
import os
import google.generativeai as genai
import time

try:
    import PyPDF2
except ImportError:
    os.system('pip install PyPDF2')
    import PyPDF2

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
        "menu": ["🏠 Panel", "📅 Sınavlar", "⏱️ Odak", "🤖 AI Mentor", "🏆 Başarılar", "⚙️ Ayarlar"],
        "butonlar": {"baslat": "🚀 BAŞLAT", "durdur": "⏸️ DURDUR", "sifirla": "🔄 SIFIRLA", "analiz": "📊 RAPOR OLUŞTUR", "cikis": "🚪 ÇIKIŞ", "ekle": "Ekle"},
        "basliklar": {"takip": "📝 GÜNLÜK TAKİP", "onizleme": "🗓️ Haftalık Önizleme", "mentor": "💬 MENTOR SOHBETİ", "sinavlar": "📅 SINAVLAR", "pomo": "⏱️ ODAK", "basari": "🏆 BAŞARILAR"},
        "labels": {"hedef": "Hedef", "yapilan": "Yapılan", "birim": "Birim", "gorev": "Görev", "sifre": "Şifre", "seviye": "Eğitim Düzeyi", "rutbe": "Rütbe", "xp_durum": "XP Durumu"}
    },
    "EN": {
        "menu": ["🏠 Dashboard", "📅 Exams", "⏱️ Focus", "🤖 AI Mentor", "🏆 Achievements", "⚙️ Settings"],
        "butonlar": {"baslat": "🚀 START", "durdur": "⏸️ PAUSE", "sifirla": "🔄 RESET", "analiz": "📊 CREATE REPORT", "cikis": "🚪 LOGOUT", "ekle": "Add"},
        "basliklar": {"takip": "📝 DAILY TRACKING", "onizleme": "🗓️ Weekly Preview", "mentor": "💬 MENTOR CHAT", "sinavlar": "📅 EXAMS", "pomo": "⏱️ FOCUS", "basari": "🏆 ACHIEVEMENTS"},
        "labels": {"hedef": "Target", "yapilan": "Done", "birim": "Unit", "gorev": "Task", "sifre": "Password", "seviye": "Education Level", "rutbe": "Rank", "xp_durum": "XP Status"}
    }
}

def mevcut_lakap_getir(lvl, dil):
    secili_lakap = LAKAPLAR[1][dil]
    for l in sorted(LAKAPLAR.keys()):
        if lvl >= l: secili_lakap = LAKAPLAR[l][dil]
    return secili_lakap

def veritabanini_yukle():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for u in data:
                    defaults = {'xp': 0, 'level': 1, 'egitim_duzeyi': 'Üniversite', 'ana_hedef': 'Mühendis', 'sinavlar': [], 'chat_history': [], 'notes': [], 'pomo_count': 0, 'dil': 'TR', 'habits': []}
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
        to_save[u] = {
            'password': db[u]['password'], 'ana_hedef': db[u].get('ana_hedef', 'Mühendis'),
            'egitim_duzeyi': db[u].get('egitim_duzeyi', 'Üniversite'), 'dil': db[u].get('dil', 'TR'),
            'xp': db[u].get('xp', 0), 'level': db[u].get('level', 1), 'pomo_count': db[u].get('pomo_count', 0),
            'chat_history': db[u].get('chat_history', []), 'notes': db[u].get('notes', []),
            'habits': db[u].get('habits', []), 'sinavlar': db[u].get('sinavlar', []), 
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
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                st.session_state.aktif_kullanici = config.get('user')
        except: pass

if st.session_state.get('aktif_kullanici') is None:
    st.title("🚀 ROTA AI")
    t1, t2 = st.tabs(["🔑 GİRİŞ", "📝 KAYIT"])
    with t1:
        u = st.text_input("Kullanıcı", key="l_u")
        p = st.text_input("Şifre", type="password", key="l_p")
        if st.button("GİRİŞ YAP"):
            if u in st.session_state.db and st.session_state.db[u]['password'] == p:
                st.session_state.aktif_kullanici = u
                with open(CONFIG_FILE, "w") as f: json.dump({'user': u}, f)
                st.rerun()
            else: st.error("Hatalı Giriş!")
    with t2:
        nu = st.text_input("Yeni Kullanıcı Adı", key="r_u")
        np = st.text_input("Şifre Belirle", type="password", key="r_p")
        if st.button("HESAP OLUŞTUR"):
            if nu and np:
                new_df = pd.DataFrame(columns=['Gün', 'Görev', 'Hedef', 'Birim', 'Yapılan'])
                st.session_state.db[nu] = {'password': np, 'xp': 0, 'level': 1, 'ana_hedef': 'Mühendis', 'data': new_df}
                veritabanini_kaydet(st.session_state.db); st.success("Kayıt Başarılı!")
    st.stop()

u_id = st.session_state.aktif_kullanici
u_info = st.session_state.db[u_id]
L = DIL_PAKETI[u_info.get('dil', 'TR')]

# --- 3. SIDEBAR ---
st.sidebar.title("🚀 ROTA AI")
if st.session_state.pomo_calisiyor:
    simdi = time.time()
    st.session_state.pomo_kalan_saniye -= (simdi - st.session_state.son_guncelleme)
    st.session_state.son_guncelleme = simdi
    if st.session_state.pomo_kalan_saniye <= 0:
        st.session_state.pomo_calisiyor = False
        u_info['xp'] += 30; u_info['pomo_count'] += 1
        veritabanini_kaydet(st.session_state.db); st.balloons()

m_g, s_g = divmod(max(0, int(st.session_state.pomo_kalan_saniye)), 60)
st.sidebar.markdown(f"### ⏳ Sayaç: `{m_g:02d}:{s_g:02d}`")
st.sidebar.metric(L["labels"]["rutbe"], mevcut_lakap_getir(u_info['level'], u_info['dil']))

menu = st.sidebar.radio("NAVİGASYON", L["menu"])

st.sidebar.subheader("📌 Hızlı Notlar")
df_n = pd.DataFrame(u_info.get('notes', []), columns=["Kategori", "Not"])
if df_n.empty: df_n = pd.DataFrame([{"Kategori": "🔵 Ders", "Not": "Not..."}])
edited_n = st.sidebar.data_editor(df_n, num_rows="dynamic", use_container_width=True, hide_index=True, key="side_notes_final")
if not df_n.equals(edited_n):
    u_info['notes'] = edited_n.to_dict(orient='records')
    veritabanini_kaydet(st.session_state.db)

if st.sidebar.button(L["butonlar"]["cikis"]):
    if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)
    st.session_state.aktif_kullanici = None; st.rerun()

# --- 4. SAYFALAR ---

if menu in ["🏠 Panel", "🏠 Dashboard"]:
    st.title(f"✨ {u_info.get('ana_hedef', 'Mühendis').upper()} {u_id.upper()}")
    
    # 📊 GRAFİKLER
    if not u_info['data'].empty:
        c1, c2 = st.columns([2, 1])
        with c1:
            fig = go.Figure([go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Hedef'], name=L["labels"]["hedef"], marker_color='#E9ECEF'),
                             go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Yapılan'], name=L["labels"]["yapilan"], marker_color='#4FACFE')])
            fig.update_layout(height=300, barmode='group'); st.plotly_chart(fig, use_container_width=True)
        with c2:
            ty = u_info['data']['Yapılan'].astype(float).sum()
            th = u_info['data']['Hedef'].astype(float).sum()
            st.plotly_chart(go.Figure(go.Pie(labels=['Biten', 'Kalan'], values=[ty, max(0, th-ty)], hole=.6, marker_colors=['#4FACFE', '#FF4B4B'])).update_layout(height=300, showlegend=False), use_container_width=True)

    # 🗓️ HAFTALIK ÖNİZLEME
    st.subheader(L["basliklar"]["onizleme"])
    gunler = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
    cols = st.columns(7)
    for i, g in enumerate(gunler):
        with cols[i]:
            st.markdown(f"<div style='background:#4FACFE; color:white; text-align:center; border-radius:5px; font-weight:bold; padding:5px;'>{g[:3].upper()}</div>", unsafe_allow_html=True)
            temp_g = u_info['data'][u_info['data']['Gün'] == g]
            for _, r in temp_g.iterrows(): st.caption(f"• {r['Görev']}")

    # 📝 GÖREV TAKİBİ
    st.divider(); st.subheader(L["basliklar"]["takip"])
    for g in gunler:
        with st.expander(f"📅 {g.upper()} GÖREVLERİ"):
            temp = u_info['data'][u_info['data']['Gün'] == g]
            for idx, row in temp.iterrows():
                cc1, cc2, cc3 = st.columns([3, 2, 1])
                cc1.write(f"**{row['Görev']}**")
                y_v = cc2.number_input(L["labels"]["yapilan"], value=int(row['Yapılan']), key=f"v_{idx}")
                if y_v != row['Yapılan']:
                    u_info['data'].at[idx, 'Yapılan'] = y_v
                    u_info['xp'] += 10
                    if u_info['xp'] >= (u_info['level'] * 200): u_info['level'] += 1; st.balloons()
                    veritabanini_kaydet(st.session_state.db); st.rerun()
                if cc3.button("🗑️", key=f"d_{idx}"):
                    u_info['data'] = u_info['data'].drop(idx); veritabanini_kaydet(st.session_state.db); st.rerun()
            with st.form(f"f_{g}", clear_on_submit=True):
                f1, f2, f3 = st.columns([2, 1, 1])
                ng, nh, nb = f1.text_input(L["labels"]["gorev"]), f2.number_input(L["labels"]["hedef"], 1), f3.selectbox(L["labels"]["birim"], ["Soru", "Saat", "Konu"])
                if st.form_submit_button(L["butonlar"]["ekle"]):
                    u_info['data'] = pd.concat([u_info['data'], pd.DataFrame([{'Gün': g, 'Görev': ng, 'Hedef': nh, 'Birim': nb, 'Yapılan': 0}])], ignore_index=True)
                    veritabanini_kaydet(st.session_state.db); st.rerun()

    # ⭐ ALIŞKANLIK TAKİPÇİSİ (NEW!)
    st.divider()
    st.subheader("📊 Alışkanlık Takipçisi (Habit Tracker)")
    h_df = pd.DataFrame(u_info.get('habits', []), columns=["Alışkanlık", "Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"])
    if h_df.empty:
        h_df = pd.DataFrame([{"Alışkanlık": "05:30 Kalkış ⏰", "Pzt": False, "Sal": False, "Çar": False, "Per": False, "Cum": False, "Cmt": False, "Paz": False}])
    
    e_habits = st.data_editor(h_df, num_rows="dynamic", use_container_width=True, hide_index=True, key="h_editor")
    if not h_df.equals(e_habits):
        u_info['habits'] = e_habits.to_dict(orient='records')
        veritabanini_kaydet(st.session_state.db)
    
    # Yıldızlı İlerleme
    for _, row in e_habits.iterrows():
        tik = sum([row["Pzt"], row["Sal"], row["Çar"], row["Per"], row["Cum"], row["Cmt"], row["Paz"]])
        yildizlar = "⭐" * int(tik/1.4) + "▫️" * (5 - int(tik/1.4))
        c_h1, c_h2 = st.columns([3, 7])
        c_h1.caption(f"**{row['Alışkanlık']}**")
        c_h2.progress(tik / 7, text=f"{yildizlar} %{int((tik/7)*100)}")

elif menu in ["📅 Sınavlar", "📅 Exams"]:
    st.title(L["basliklar"]["sinavlar"])
    pdf = st.file_uploader("PDF", type="pdf")
    if pdf and st.button("Analiz ✨"):
        reader = PyPDF2.PdfReader(pdf); txt = "".join([p.extract_text() for p in reader.pages])
        try:
            res = genai.GenerativeModel('gemini-1.5-flash').generate_content(f"Sınavları çıkar: {txt}").text
            st.info(res)
        except: st.error("AI Meşgul.")
    with st.form("ex_f"):
        c1, c2 = st.columns(2); d_a = c1.text_input("Ders"); t_a = c2.date_input("Tarih")
        if st.form_submit_button("Ekle"):
            u_info['sinavlar'].append({'ders': d_a, 'tarih': str(t_a)})
            veritabanini_kaydet(st.session_state.db); st.rerun()
    if u_info['sinavlar']: st.table(pd.DataFrame(u_info['sinavlar']))

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
    st.markdown(f"<h1 style='text-align:center; font-size:150px; color:#4FACFE;'>{m_e:02d}:{s_e:02d}</h1>", unsafe_allow_html=True)

elif menu in ["🤖 AI Mentor"]:
    st.title("🤖 AI MENTOR")
    if st.button(L["butonlar"]["analiz"]):
        try:
            res = genai.GenerativeModel('gemini-1.5-flash').generate_content(f"Analiz: {u_info['data'].to_string()}").text
            st.info(res)
        except: st.error("AI Meşgul.")
    st.divider()
    with st.popover("💬 Mentor Sohbet"):
        for m in u_info.get('chat_history', []): st.chat_message(m['role']).write(m['text'])
        p_m = st.chat_input("Yaz...")
        if p_m:
            u_info['chat_history'].append({"role": "user", "text": p_m})
            try:
                res = genai.GenerativeModel('gemini-1.5-flash').generate_content(p_m).text
                u_info['chat_history'].append({"role": "assistant", "text": res})
                veritabanini_kaydet(st.session_state.db); st.rerun()
            except: st.error("Hata!")

elif menu in ["🏆 Başarılar", "🏆 Achievements"]:
    st.title(L["basliklar"]["basari"])
    k1, k2, k3 = st.columns(3)
    k1.metric("RÜTBE", mevcut_lakap_getir(u_info['level'], u_info['dil']))
    k2.metric("SEVİYE", u_info['level']); k3.metric("XP", u_info['xp'])
    st.progress(min(u_info['xp'] / (u_info['level'] * 200), 1.0))
    st.divider()
    b1, b2 = st.columns(2)
    if u_info.get('pomo_count', 0) >= 10: b1.success("🔥 ODAK USTASI")
    else: b1.info(f"🔒 ODAK USTASI ({u_info.get('pomo_count', 0)}/10)")
    if u_info['level'] >= 10: b2.success("👑 VİZYONER")
    else: b2.info("🔒 VİZYONER (Lvl 10)")

elif menu in ["⚙️ Ayarlar", "⚙️ Settings"]:
    st.title(L["menu"][-1])
    with st.form("settings_f"):
        nl = st.selectbox("Dil", ["TR", "EN"], index=0 if u_info['dil'] == 'TR' else 1)
        ni = st.text_input("Kullanıcı Adı", value=u_id)
        ns = st.text_input("Şifre", value=u_info['password'], type="password")
        nm = st.text_input("Meslek / Hedef", value=u_info.get('ana_hedef', 'Mühendis'))
        if st.form_submit_button("KAYDET"):
            if ni != u_id:
                st.session_state.db[ni] = st.session_state.db.pop(u_id)
                st.session_state.aktif_kullanici = ni
            st.session_state.db[st.session_state.aktif_kullanici].update({'dil': nl, 'password': ns, 'ana_hedef': nm})
            veritabanini_kaydet(st.session_state.db); st.rerun()

if st.session_state.pomo_calisiyor:
    time.sleep(1); st.rerun()
