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

# --- 0. KONFİGÜRASYON VE SABİTLER ---
st.set_page_config(page_title="ROTA AI PRO", page_icon="🚀", layout="wide")
DB_FILE = "rota_database.json"

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
        "butonlar": {"baslat": "🚀 BAŞLAT", "durdur": "⏸️ DURDUR", "sifirla": "🔄 SIFIRLA", "analiz": "📊 PDF ANALİZ ET ✨", "cikis": "🚪 ÇIKIŞ", "ekle": "Ekle"},
        "basliklar": {"takip": "📝 GÜNLÜK TAKİP", "onizleme": "🗓️ Haftalık Önizleme", "mentor": "💬 MENTOR SOHBETİ", "sinavlar": "📅 SINAVLAR", "pomo": "⏱️ ODAK", "basari": "🏆 BAŞARILAR", "akademik": "🎓 AKADEMİK YÖNETİM"},
        "labels": {"hedef": "Hedef", "yapilan": "Yapılan", "birim": "Birim", "gorev": "Görev", "sifre": "Şifre", "seviye": "Eğitim Düzeyi", "rutbe": "Rütbe"}
    },
    "EN": {
        "menu": ["🏠 Dashboard", "📊 Habits", "📅 Exams", "⏱️ Focus", "🎓 Academic", "🤖 AI Mentor", "🏆 Achievements", "⚙️ Settings"],
        "butonlar": {"baslat": "🚀 START", "durdur": "⏸️ PAUSE", "sifirla": "🔄 RESET", "analiz": "📊 ANALYZE PDF ✨", "cikis": "🚪 LOGOUT", "ekle": "Add"},
        "basliklar": {"takip": "📝 DAILY TRACKING", "onizleme": "🗓️ Weekly Preview", "mentor": "💬 MENTOR CHAT", "sinavlar": "📅 EXAMS", "pomo": "⏱️ FOCUS", "basari": "🏆 ACHIEVEMENTS", "akademik": "🎓 ACADEMIC MANAGEMENT"},
        "labels": {"hedef": "Target", "yapilan": "Done", "birim": "Unit", "gorev": "Task", "sifre": "Password", "seviye": "Education Level", "rutbe": "Rank"}
    }
}

# --- 1. FONKSİYONLAR ---

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
                    defaults = {
                        'xp': 0, 'level': 1, 'ana_hedef': 'Öğrenci', 'sinavlar': [], 
                        'chat_history': [], 'notes': [], 'pomo_count': 0, 'dil': 'TR', 
                        'habits': [], 'attendance': [], 'gpa_list': [], 
                        'mevcut_gano': 0.0, 'tamamlanan_kredi': 0, 'tema_rengi': '#4FACFE'
                    }
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

# --- 2. VERİ VE SESSION BAŞLATMA ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

if 'db' not in st.session_state: st.session_state.db = veritabanini_yukle()
if 'pomo_kalan' not in st.session_state: st.session_state.pomo_kalan = 25 * 60
if 'pomo_aktif' not in st.session_state: st.session_state.pomo_aktif = False
if 'son_tik' not in st.session_state: st.session_state.son_tik = time.time()

# --- 3. GİRİŞ & KAYIT ---
if 'user' not in st.session_state: st.session_state.user = None

if st.session_state.user is None:
    st.title("🚀 ROTA AI")
    t1, t2 = st.tabs(["🔑 GİRİŞ", "📝 KAYIT"])
    with t1:
        u_in = st.text_input("Kullanıcı")
        p_in = st.text_input("Şifre", type="password")
        if st.button("GİRİŞ YAP"):
            if u_in in st.session_state.db and st.session_state.db[u_in]['password'] == p_in:
                st.session_state.user = u_in
                st.rerun()
            else: st.error("Hatalı Giriş!")
    with t2:
        nu = st.text_input("Yeni Kullanıcı")
        np = st.text_input("Şifre Belirle", type="password")
        if st.button("HESAP OLUŞTUR"):
            if nu and np and nu not in st.session_state.db:
                st.session_state.db[nu] = {
                    'password': np, 'xp': 0, 'level': 1, 'ana_hedef': 'Öğrenci',
                    'data': pd.DataFrame(columns=['Gün', 'Görev', 'Hedef', 'Birim', 'Yapılan']),
                    'attendance': [], 'gpa_list': [], 'mevcut_gano': 0.0, 'tamamlanan_kredi': 0,
                    'dil': 'TR', 'sinavlar': [], 'habits': [], 'notes': [], 'tema_rengi': '#4FACFE'
                }
                veritabanini_kaydet(st.session_state.db); st.success("Kayıt Başarılı!")
    st.stop()

u_id = st.session_state.user
u_info = st.session_state.db[u_id]
L = DIL_PAKETI.get(u_info['dil'], DIL_PAKETI["TR"])
TEMA = u_info.get('tema_rengi', '#4FACFE')

st.markdown(f"<style>h1, h2, h3, .stSubheader {{ color: {TEMA} !important; }} .stButton>button {{ background-color: {TEMA} !important; color: white !important; }}</style>", unsafe_allow_html=True)

# --- 4. SIDEBAR ---
st.sidebar.title("🚀 ROTA AI")
if st.session_state.pomo_aktif and st.session_state.pomo_kalan > 0:
    simdi = time.time()
    st.session_state.pomo_kalan -= (simdi - st.session_state.son_tik)
    st.session_state.son_tik = simdi
    if st.session_state.pomo_kalan <= 0:
        st.session_state.pomo_aktif = False
        u_info['xp'] += 50; u_info['pomo_count'] += 1
        veritabanini_kaydet(st.session_state.db); st.balloons()
    time.sleep(0.1); st.rerun()

m_p, s_p = divmod(max(0, int(st.session_state.pomo_kalan)), 60)
st.sidebar.markdown(f"### ⏳ Sayaç: `{m_p:02d}:{s_p:02d}`")
st.sidebar.metric(L["labels"]["rutbe"], mevcut_lakap_getir(u_info['level'], u_info['dil']))

menu = st.sidebar.radio("NAVİGASYON", L["menu"])

st.sidebar.subheader("📌 Hızlı Notlar")
df_n = pd.DataFrame(u_info.get('notes', []), columns=["Kategori", "Not"])
if df_n.empty: df_n = pd.DataFrame([{"Kategori": "🔵 Ders", "Not": "..."}])
edited_n = st.sidebar.data_editor(df_n, num_rows="dynamic", use_container_width=True, hide_index=True)
if not df_n.equals(edited_n):
    u_info['notes'] = edited_n.to_dict(orient='records'); veritabanini_kaydet(st.session_state.db)

if st.sidebar.button(L["butonlar"]["cikis"]):
    st.session_state.user = None; st.rerun()

# --- 5. SAYFALAR ---

if menu in ["🏠 Panel", "🏠 Dashboard"]:
    st.title(f"✨ {u_info.get('ana_hedef', 'Öğrenci').upper()} {u_id.upper()}")
    if not u_info['data'].empty:
        c1, c2 = st.columns([2, 1])
        with c1:
            fig = go.Figure([go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Hedef'], name="Hedef", marker_color='#E9ECEF'),
                             go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Yapılan'], name="Biten", marker_color=TEMA)])
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            ty, th = u_info['data']['Yapılan'].astype(float).sum(), u_info['data']['Hedef'].astype(float).sum()
            st.plotly_chart(go.Figure(go.Pie(labels=['Biten', 'Kalan'], values=[ty, max(0, th-ty)], hole=.6, marker_colors=[TEMA, '#FF4B4B'])), use_container_width=True)

    st.subheader(L["basliklar"]["onizleme"])
    cols = st.columns(7)
    gunler = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
    for i, g in enumerate(gunler):
        with cols[i]:
            st.markdown(f"<div style='background:{TEMA}; color:white; text-align:center; border-radius:5px; font-weight:bold;'>{g[:3].upper()}</div>", unsafe_allow_html=True)
            for _, r in u_info['data'][u_info['data']['Gün'] == g].iterrows(): st.caption(f"• {r['Görev']}")

    st.divider(); st.subheader(L["basliklar"]["takip"])
    for g in gunler:
        with st.expander(f"📅 {g.upper()}"):
            temp = u_info['data'][u_info['data']['Gün'] == g]
            for idx, row in temp.iterrows():
                cc1, cc2, cc3 = st.columns([3, 2, 1])
                cc1.write(f"**{row['Görev']}**")
                y_v = cc2.number_input("Biten", value=int(row['Yapılan']), key=f"v_{g}_{idx}")
                if y_v != row['Yapılan']:
                    u_info['data'].at[idx, 'Yapılan'] = y_v; u_info['xp'] += 10
                    veritabanini_kaydet(st.session_state.db); st.rerun()
                if cc3.button("🗑️", key=f"d_{g}_{idx}"):
                    u_info['data'] = u_info['data'].drop(idx); veritabanini_kaydet(st.session_state.db); st.rerun()
            with st.form(f"f_{g}", clear_on_submit=True):
                f1, f2, f3 = st.columns([2, 1, 1])
                ng, nh, nb = f1.text_input(L["labels"]["gorev"]), f2.number_input(L["labels"]["hedef"], 1), f3.selectbox("Birim", ["Soru", "Saat", "Konu"])
                if st.form_submit_button(L["butonlar"]["ekle"]):
                    u_info['data'] = pd.concat([u_info['data'], pd.DataFrame([{'Gün': g, 'Görev': ng, 'Hedef': nh, 'Yapılan': 0}])], ignore_index=True)
                    veritabanini_kaydet(st.session_state.db); st.rerun()

elif menu in ["📊 Alışkanlıklar", "📊 Habits"]:
    st.title("📊 Alışkanlık Takip Sistemi")
    h_df = pd.DataFrame(u_info.get('habits', []), columns=["Alışkanlık", "Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"])
    edited_h = st.data_editor(h_df, num_rows="dynamic", use_container_width=True, hide_index=True)
    if not h_df.equals(edited_h):
        u_info['habits'] = edited_h.to_dict(orient='records'); veritabanini_kaydet(st.session_state.db)

elif menu in ["📅 Sınavlar", "📅 Exams"]:
    st.title(L["basliklar"]["sinavlar"])
    pdf = st.file_uploader("PDF Yükle", type="pdf")
    if pdf and st.button(L["butonlar"]["analiz"]):
        reader = PyPDF2.PdfReader(pdf); txt = "".join([p.extract_text() for p in reader.pages])
        st.info(genai.GenerativeModel('gemini-1.5-flash').generate_content(f"Sınavları ayıkla: {txt}").text)
    
    with st.form("ex"):
        c1, c2 = st.columns(2); d, t = c1.text_input("Ders"), c2.date_input("Tarih")
        if st.form_submit_button("Ekle"):
            # Sınavları ID ile kaydediyoruz ki silerken karışmasın
            u_info['sinavlar'].append({'id': str(uuid.uuid4()), 'ders': d, 'tarih': str(t)})
            veritabanini_kaydet(st.session_state.db); st.rerun()
    
    st.divider()
    # SINAV SİLME MANTIĞI BURADA ✨
    for idx, s in enumerate(u_info.get('sinavlar', [])):
        sc1, sc2, sc3 = st.columns([4, 2, 1])
        sc1.write(f"📖 **{s['ders']}**")
        sc2.write(f"📅 {s['tarih']}")
        if sc3.button("🗑️", key=f"ex_del_{idx}"):
            u_info['sinavlar'].pop(idx)
            veritabanini_kaydet(st.session_state.db); st.rerun()

elif menu in ["⏱️ Odak", "⏱️ Focus"]:
    st.title(L["basliklar"]["pomo"])
    dk = st.select_slider("Dakika", options=[15, 25, 45, 60], value=25)
    c1, c2, c3 = st.columns(3)
    if c1.button("🚀 BAŞLAT"): st.session_state.pomo_kalan = dk*60; st.session_state.pomo_aktif = True; st.session_state.son_tik = time.time(); st.rerun()
    if c2.button("⏸️ DURDUR"): st.session_state.pomo_aktif = False; st.rerun()
    if c3.button("🔄 SIFIRLA"): st.session_state.pomo_aktif = False; st.session_state.pomo_kalan = 25*60; st.rerun()
    st.markdown(f"<h1 style='text-align:center; font-size:150px; color:{TEMA};'>{m_p:02d}:{s_p:02d}</h1>", unsafe_allow_html=True)

elif menu in ["🎓 Akademik", "🎓 Academic"]:
    st.title(L["basliklar"]["akademik"])
    t_a1, t_a2 = st.tabs(["📉 Devamsızlık", "📊 GNO Tahmini"])
    with t_a1:
        with st.form("at_f"):
            dn, dl = st.text_input("Ders"), st.number_input("Limit", 1, 15, 4)
            if st.form_submit_button("Ders Ekle"):
                u_info['attendance'].append({"id": str(uuid.uuid4()), "Ders": dn, "Limit": dl, "Yapılan": 0})
                veritabanini_kaydet(st.session_state.db); st.rerun()
        for idx, course in enumerate(u_info['attendance']):
            col1, col2, col3 = st.columns([3, 2, 1])
            col1.write(f"**{course['Ders']}** (Limit: {course['Limit']})")
            val = col2.number_input("Kaçırılan", value=course['Yapılan'], key=f"at_{idx}")
            if val != course['Yapılan']:
                u_info['attendance'][idx]['Yapılan'] = val; veritabanini_kaydet(st.session_state.db); st.rerun()
            if col3.button("🗑️", key=f"at_d_{idx}"):
                u_info['attendance'].pop(idx); veritabanini_kaydet(st.session_state.db); st.rerun()
    with t_a2:
        u_info['mevcut_gano'] = st.number_input("Mevcut GNO", 0.0, 4.0, value=float(u_info.get('mevcut_gano', 0.0)))
        u_info['tamamlanan_kredi'] = st.number_input("Toplam Kredi", 0, 300, value=int(u_info.get('tamamlanan_kredi', 0)))
        if st.button("Genel Bilgileri Kaydet"): veritabanini_kaydet(st.session_state.db); st.success("Kaydedildi!")

elif menu == "🤖 AI Mentor":
    st.title("🤖 AI AKADEMİK KOÇ")
    for msg in u_info.get('chat_history', []): st.chat_message(msg['role']).write(msg['text'])
    p_m = st.chat_input("Yaz...")
    if p_m:
        u_info.setdefault('chat_history', []).append({"role": "user", "text": p_m})
        res = genai.GenerativeModel('gemini-1.5-flash').generate_content(p_m).text
        u_info['chat_history'].append({"role": "assistant", "text": res}); veritabanini_kaydet(st.session_state.db); st.rerun()

elif menu in ["🏆 Başarılar", "🏆 Achievements"]:
    st.title(L["basliklar"]["basari"])
    col1, col2, col3 = st.columns(3)
    col1.metric("RÜTBE", mevcut_lakap_getir(u_info['level'], u_info['dil']))
    col2.metric("SEVİYE", u_info['level']); col3.metric("XP", u_info['xp'])
    st.progress(min(u_info['xp'] / (u_info['level'] * 200), 1.0))

elif menu in ["⚙️ Ayarlar", "⚙️ Settings"]:
    st.title("⚙️ AYARLAR")
    with st.form("set"):
        new_id = st.text_input("Kullanıcı Adı", value=u_id)
        new_pw = st.text_input("Şifre", value=u_info['password'], type="password")
        new_dil = st.selectbox("Dil", ["TR", "EN"], index=0 if u_info['dil'] == 'TR' else 1)
        new_theme = st.color_picker("Tema Rengi", value=TEMA)
        if st.form_submit_button("GÜNCELLE"):
            if new_id != u_id: st.session_state.db[new_id] = st.session_state.db.pop(u_id); st.session_state.user = new_id
            u_info = st.session_state.db[st.session_state.user]
            u_info.update({'password': new_pw, 'dil': new_dil, 'tema_rengi': new_theme})
            veritabanini_kaydet(st.session_state.db); st.rerun()
