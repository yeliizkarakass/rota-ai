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
        "basliklar": {"takip": "📝 GÜNLÜK TAKİP", "mentor": "🤖 AI KOÇ", "sinavlar": "📅 SINAVLAR", "pomo": "⏱️ ODAK", "basari": "🏆 BAŞARILAR", "akademik": "🎓 AKADEMİK YÖNETİM"},
        "labels": {"hedef": "Hedef", "yapilan": "Yapılan", "birim": "Birim", "gorev": "Görev", "sifre": "Şifre", "seviye": "Eğitim Düzeyi", "rutbe": "Rütbe"}
    },
    "EN": {
        "menu": ["🏠 Dashboard", "📊 Habits", "📅 Exams", "⏱️ Focus", "🎓 Academic", "🤖 AI Mentor", "🏆 Achievements", "⚙️ Settings"],
        "butonlar": {"baslat": "🚀 START", "durdur": "⏸️ PAUSE", "sifirla": "🔄 RESET", "analiz": "📊 ANALYZE ✨", "cikis": "🚪 LOGOUT", "ekle": "Add"},
        "basliklar": {"takip": "📝 DAILY TRACKING", "mentor": "🤖 AI COACH", "sinavlar": "📅 EXAMS", "pomo": "⏱️ FOCUS", "basari": "🏆 ACHIEVEMENTS", "akademik": "🎓 ACADEMIC MANAGEMENT"},
        "labels": {"hedef": "Target", "yapilan": "Done", "birim": "Unit", "gorev": "Task", "sifre": "Password", "seviye": "Education Level", "rutbe": "Rank"}
    }
}

# --- 1. FONKSİYONLAR ---

def veritabanini_yukle():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for u in data:
                    # KRİTİK HATA ÖNLEYİCİ: Eksik anahtarları profil bazlı tamir eder
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
                    for col in ['Gün', 'Görev', 'Hedef', 'Birim', 'Yapılan']:
                        if col not in data[u]['data'].columns:
                            data[u]['data'][col] = "" if col != 'Yapılan' else 0
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
if 'son_tik' not in st.session_state: st.session_state.son_tik = time.time()

# Otomatik Giriş Kontrolü
if 'user' not in st.session_state:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                saved_user = json.load(f).get('user')
                if saved_user in st.session_state.db: st.session_state.user = saved_user
                else: st.session_state.user = None
        except: st.session_state.user = None
    else: st.session_state.user = None

# --- 3. GİRİŞ & KAYIT ---
if st.session_state.user is None:
    st.title("🚀 ROTA AI")
    t1, t2 = st.tabs(["🔑 GİRİŞ", "📝 KAYIT"])
    with t1:
        u_in = st.text_input("Kullanıcı")
        p_in = st.text_input("Şifre", type="password")
        rem = st.checkbox("Beni Hatırla")
        if st.button("SİSTEME GİR"):
            if u_in in st.session_state.db and st.session_state.db[u_in]['password'] == p_in:
                st.session_state.user = u_in
                if rem:
                    with open(CONFIG_FILE, "w") as f: json.dump({'user': u_in}, f)
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
                veritabanini_kaydet(st.session_state.db); st.success("Kayıt Başarılı! Giriş yapın.")
            elif nu in st.session_state.db: st.warning("Kullanıcı mevcut.")
    st.stop()

u_id = st.session_state.user
u_info = st.session_state.db[u_id]
L = DIL_PAKETI.get(u_info['dil'], DIL_PAKETI["TR"])
TEMA = u_info.get('tema_rengi', '#4FACFE')

st.markdown(f"<style>h1, h2, h3, .stSubheader {{ color: {TEMA} !important; }} .stButton>button {{ background-color: {TEMA} !important; color: white !important; }}</style>", unsafe_allow_html=True)

# --- 4. SIDEBAR ---
st.sidebar.title("🚀 ROTA AI")
st.sidebar.metric(L["labels"]["rutbe"], mevcut_lakap_getir(u_info['level'], u_info['dil']))

with st.sidebar.container(border=True):
    st.write("⏱️ **ODAKLANMA**")
    if st.session_state.pomo_aktif:
        simdi = time.time()
        st.session_state.pomo_kalan -= (simdi - st.session_state.son_tik)
        st.session_state.son_tik = simdi
        if st.session_state.pomo_kalan <= 0:
            st.session_state.pomo_aktif = False
            u_info['xp'] += 50
            if u_info['xp'] >= (u_info['level'] * 200): u_info['level'] += 1
            veritabanini_kaydet(st.session_state.db); st.balloons(); st.rerun()
        time.sleep(1); st.rerun()
    
    m_p, s_p = divmod(max(0, int(st.session_state.pomo_kalan)), 60)
    st.subheader(f"`{m_p:02d}:{s_p:02d}`")
    c1, c2, c3 = st.columns(3)
    if c1.button("▶️"): st.session_state.pomo_aktif = True; st.session_state.son_tik = time.time(); st.rerun()
    if c2.button("⏸️"): st.session_state.pomo_aktif = False; st.rerun()
    if c3.button("🔄"): st.session_state.pomo_aktif = False; st.session_state.pomo_kalan = 25*60; st.rerun()

menu = st.sidebar.radio("NAVİGASYON", L["menu"])

st.sidebar.subheader("📌 Hızlı Notlar")
edited_n = st.sidebar.data_editor(pd.DataFrame(u_info.get('notes', []), columns=["Not"]), num_rows="dynamic", use_container_width=True, hide_index=True)
if u_info['notes'] != edited_n.to_dict(orient='records'):
    u_info['notes'] = edited_n.to_dict(orient='records'); veritabanini_kaydet(st.session_state.db)

if st.sidebar.button(L["butonlar"]["cikis"]):
    if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)
    st.session_state.user = None; st.rerun()

# --- 5. SAYFALAR ---

if menu in ["🏠 Panel", "🏠 Dashboard"]:
    st.title(f"✨ {u_info.get('ana_hedef', 'Öğrenci').upper()} {u_id.upper()}")
    if not u_info['data'].empty:
        fig = go.Figure([go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Hedef'], name="Hedef"),
                         go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Yapılan'], name="Biten", marker_color=TEMA)])
        st.plotly_chart(fig, use_container_width=True)

    for g in ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']:
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
                ng, nh, nb = f1.text_input("Görev"), f2.number_input("Hedef", 1), f3.selectbox("Birim", ["Soru", "Saat", "Konu"])
                if st.form_submit_button("Ekle"):
                    u_info['data'] = pd.concat([u_info['data'], pd.DataFrame([{'Gün': g, 'Görev': ng, 'Hedef': nh, 'Birim': nb, 'Yapılan': 0}])], ignore_index=True)
                    veritabanini_kaydet(st.session_state.db); st.rerun()

elif menu in ["📊 Alışkanlıklar", "📊 Habits"]:
    st.title("📊 Alışkanlık Takip Sistemi")
    h_df = pd.DataFrame(u_info.get('habits', []), columns=["Alışkanlık", "Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"])
    e_habits = st.data_editor(h_df, num_rows="dynamic", use_container_width=True, hide_index=True)
    if not h_df.equals(e_habits):
        u_info['habits'] = e_habits.to_dict(orient='records'); veritabanini_kaydet(st.session_state.db); st.rerun()
    st.divider()
    for _, row in e_habits.iterrows():
        tik = sum([1 for gun in ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"] if row.get(gun, False) is True])
        st.progress(tik / 7, text=f"**{row['Alışkanlık']}** ⭐ %{int((tik/7)*100)}")

elif menu in ["📅 Sınavlar", "📅 Exams"]:
    st.title(L["basliklar"]["sinavlar"])
    pdf = st.file_uploader("PDF Yükle", type="pdf")
    if pdf and st.button(L["butonlar"]["analiz"]):
        reader = PyPDF2.PdfReader(pdf); txt = "".join([p.extract_text() for p in reader.pages])
        st.info(genai.GenerativeModel('gemini-1.5-flash').generate_content(f"Sınavları ayıkla: {txt}").text)
    with st.form("ex_f"):
        c1, c2 = st.columns(2); d_s, t_s = c1.text_input("Ders"), c2.date_input("Tarih")
        if st.form_submit_button("Ekle"):
            u_info['sinavlar'].append({'id': str(uuid.uuid4()), 'ders': d_s, 'tarih': str(t_s)})
            veritabanini_kaydet(st.session_state.db); st.rerun()
    for idx, s in enumerate(u_info.get('sinavlar', [])):
        sc1, sc2, sc3 = st.columns([4, 2, 1])
        sc1.write(f"📖 **{s['ders']}**"); sc2.write(f"📅 {s['tarih']}")
        if sc3.button("🗑️", key=f"ex_del_{idx}"):
            u_info['sinavlar'].pop(idx); veritabanini_kaydet(st.session_state.db); st.rerun()

elif menu in ["🎓 Akademik", "🎓 Academic"]:
    st.title(L["basliklar"]["akademik"])
    t1, t2 = st.tabs(["📉 Devamsızlık", "📊 GNO Tahmini"])
    with t1:
        with st.form("at_f"):
            c1, c2 = st.columns(2); dn, dl = c1.text_input("Ders"), c2.number_input("Limit", 1, 15, 4)
            if st.form_submit_button("Ders Ekle"):
                u_info['attendance'].append({"id": str(uuid.uuid4()), "Ders": dn, "Limit": dl, "Yapılan": 0})
                veritabanini_kaydet(st.session_state.db); st.rerun()
        for idx, c in enumerate(u_info['attendance']):
            col1, col2, col3 = st.columns([4, 2, 1])
            col1.write(f"**{c['Ders']}** (Limit: {c['Limit']})")
            val = col2.number_input("Kaçırılan", value=c['Yapılan'], key=f"at_{idx}")
            if val != c['Yapılan']: u_info['attendance'][idx]['Yapılan'] = val; veritabanini_kaydet(st.session_state.db); st.rerun()
            if col3.button("🗑️", key=f"at_d_{idx}"): u_info['attendance'].pop(idx); veritabanini_kaydet(st.session_state.db); st.rerun()
    with t2:
        m_g = st.number_input("Mevcut GNO", 0.0, 4.0, value=float(u_info['mevcut_gano']), step=0.01)
        m_k = st.number_input("Toplam Kredi", 0, 300, value=int(u_info['tamamlanan_kredi']))
        u_info['mevcut_gano'], u_info['tamamlanan_kredi'] = m_g, m_k
        with st.form("gpa_add"):
            f1, f2, f3 = st.columns(3)
            dn, dk, dnot = f1.text_input("Ders"), f2.number_input("Kredi", 1), f3.selectbox("Not", ["AA","BA","BB","CB","CC","DC","DD","FF"])
            if st.form_submit_button("Ekle"):
                u_info['gpa_list'].append({"ders":dn, "kredi":dk, "not":dnot}); veritabanini_kaydet(st.session_state.db); st.rerun()
        skala = {"AA":4, "BA":3.5, "BB":3, "CB":2.5, "CC":2, "DC":1.5, "DD":1, "FF":0}
        tp = m_g * m_k + sum([skala[x['not']] * x['kredi'] for x in u_info['gpa_list']])
        tk = m_k + sum([x['kredi'] for x in u_info['gpa_list']])
        if tk > 0: st.success(f"Tahmini GNO: {tp/tk:.2f}")

elif menu == "🤖 AI Mentor":
    st.title(L["basliklar"]["mentor"])
    if st.button("📊 HAFTALIK ANALİZ RAPORU OLUŞTUR"):
        res = genai.GenerativeModel('gemini-1.5-flash').generate_content(f"Analiz: {u_info['data'].to_string()}").text
        st.markdown(res)
    p_m = st.chat_input("Sor...")
    if p_m:
        u_info.setdefault('chat_history', []).append({"role": "user", "text": p_m})
        res = genai.GenerativeModel('gemini-1.5-flash').generate_content(p_m).text
        u_info['chat_history'].append({"role": "assistant", "text": res}); veritabanini_kaydet(st.session_state.db); st.rerun()
    for msg in reversed(u_info.get('chat_history', [])): st.chat_message(msg['role']).write(msg['text'])

elif menu in ["🏆 Başarılar", "🏆 Achievements"]:
    st.title(L["basliklar"]["basari"])
    col1, col2, col3 = st.columns(3)
    col1.metric("RÜTBE", mevcut_lakap_getir(u_info['level'], u_info['dil']))
    col2.metric("SEVİYE", u_info['level']); col3.metric("XP", u_info['xp'])
    st.progress(min(u_info['xp'] / (u_info['level'] * 200), 1.0))

elif menu in ["⚙️ Ayarlar", "⚙️ Settings"]:
    st.title("⚙️ AYARLAR")
    with st.form("set"):
        new_pw = st.text_input("Yeni Şifre", value=u_info['password'], type="password")
        new_dil = st.selectbox("Dil", ["TR", "EN"], index=0 if u_info['dil'] == 'TR' else 1)
        new_theme = st.color_picker("Tema Rengi", value=TEMA)
        if st.form_submit_button("GÜNCELLE"):
            u_info.update({'password': new_pw, 'dil': new_dil, 'tema_rengi': new_theme})
            veritabanini_kaydet(st.session_state.db); st.rerun()
