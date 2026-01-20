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

# --- 0. AYARLAR ---
st.set_page_config(page_title="ROTA AI PRO", page_icon="🚀", layout="wide")

# --- 1. VERİ YÖNETİMİ ---
DB_FILE = "rota_database.json"

try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except:
    pass

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
        "basliklar": {"takip": "📝 GÜNLÜK TAKİP", "onizleme": "🗓️ Haftalık Önizleme", "mentor": "💬 MENTOR SOHBETİ", "sinavlar": "📅 SINAVLAR", "pomo": "⏱️ ODAK", "basari": "🏆 BAŞARILAR VE İSTATİSTİK", "akademik": "🎓 AKADEMİK YÖNETİM"},
        "labels": {"hedef": "Hedef", "yapilan": "Yapılan", "birim": "Birim", "gorev": "Görev", "sifre": "Şifre", "seviye": "Eğitim Düzeyi", "rutbe": "Rütbe"}
    },
    "EN": {
        "menu": ["🏠 Dashboard", "📊 Habits", "📅 Exams", "⏱️ Focus", "🎓 Academic", "🤖 AI Mentor", "🏆 Achievements", "⚙️ Settings"],
        "butonlar": {"baslat": "🚀 START", "durdur": "⏸️ PAUSE", "sifirla": "🔄 RESET", "analiz": "📊 ANALYZE PDF ✨", "cikis": "🚪 LOGOUT", "ekle": "Add"},
        "basliklar": {"takip": "📝 DAILY TRACKING", "onizleme": "🗓️ Weekly Preview", "mentor": "💬 MENTOR CHAT", "sinavlar": "📅 EXAMS", "pomo": "⏱️ FOCUS", "basari": "🏆 ACHIEVEMENTS & STATS", "akademik": "🎓 ACADEMIC MANAGEMENT"},
        "labels": {"hedef": "Target", "yapilan": "Done", "birim": "Unit", "gorev": "Task", "sifre": "Password", "seviye": "Education Level", "rutbe": "Rank"}
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
                    defaults = {
                        'xp': 0, 'level': 1, 'ana_hedef': 'Öğrenci', 'sinavlar': [], 
                        'chat_history': [], 'notes': [], 'pomo_count': 0, 'dil': 'TR', 
                        'habits': [], 'attendance': [], 'gpa_list': [], 
                        'mevcut_gano': 0.0, 'tamamlanan_kredi': 0
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
        u_in = st.text_input("Kullanıcı")
        p_in = st.text_input("Şifre", type="password")
        if st.button("GİRİŞ YAP"):
            if u_in in st.session_state.db and st.session_state.db[u_in]['password'] == p_in:
                st.session_state.aktif_kullanici = u_in
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
                    'dil': 'TR', 'sinavlar': [], 'habits': [], 'notes': []
                }
                veritabanini_kaydet(st.session_state.db); st.success("Kayıt Başarılı!")
    st.stop()

u_id = st.session_state.aktif_kullanici
u_info = st.session_state.db[u_id]
L = DIL_PAKETI.get(u_info.get('dil', 'TR'), DIL_PAKETI["TR"])

# --- 3. SIDEBAR ---
st.sidebar.title("🚀 ROTA AI")
if st.session_state.pomo_calisiyor:
    simdi = time.time()
    st.session_state.pomo_kalan_saniye -= (simdi - st.session_state.son_guncelleme)
    st.session_state.son_guncelleme = simdi
    if st.session_state.pomo_kalan_saniye <= 0:
        st.session_state.pomo_calisiyor = False
        u_info['xp'] += 30; u_info['pomo_count'] += 1
        if u_info['xp'] >= (u_info['level'] * 200): u_info['level'] += 1
        veritabanini_kaydet(st.session_state.db); st.balloons()

m_g, s_g = divmod(max(0, int(st.session_state.pomo_kalan_saniye)), 60)
st.sidebar.markdown(f"### ⏳ Sayaç: `{m_g:02d}:{s_g:02d}`")
st.sidebar.metric(L["labels"]["rutbe"], mevcut_lakap_getir(u_info['level'], u_info.get('dil', 'TR')))

menu = st.sidebar.radio("NAVİGASYON", L["menu"])

st.sidebar.subheader("📌 Hızlı Notlar")
df_n = pd.DataFrame(u_info.get('notes', []), columns=["Kategori", "Not"])
if df_n.empty: df_n = pd.DataFrame([{"Kategori": "🔵 Ders", "Not": "Not..."}])
edited_n = st.sidebar.data_editor(df_n, num_rows="dynamic", use_container_width=True, hide_index=True)
if not df_n.equals(edited_n):
    u_info['notes'] = edited_n.to_dict(orient='records')
    veritabanini_kaydet(st.session_state.db)

if st.sidebar.button(L["butonlar"]["cikis"]):
    st.session_state.aktif_kullanici = None; st.rerun()

# --- 4. SAYFALAR ---

# --- PANEL ---
if menu in ["🏠 Panel", "🏠 Dashboard"]:
    st.title(f"✨ {u_info.get('ana_hedef', 'Öğrenci').upper()} {u_id.upper()}")
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

    st.subheader(L["basliklar"]["onizleme"])
    gunler = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
    cols = st.columns(7)
    for i, g in enumerate(gunler):
        with cols[i]:
            st.markdown(f"<div style='background:#4FACFE; color:white; text-align:center; border-radius:5px; font-weight:bold; padding:5px;'>{g[:3].upper()}</div>", unsafe_allow_html=True)
            for _, r in u_info['data'][u_info['data']['Gün'] == g].iterrows(): st.caption(f"• {r['Görev']}")

    st.divider(); st.subheader(L["basliklar"]["takip"])
    for g in gunler:
        with st.expander(f"📅 {g.upper()} GÖREVLERİ"):
            temp = u_info['data'][u_info['data']['Gün'] == g]
            for idx, row in temp.iterrows():
                cc1, cc2, cc3 = st.columns([3, 2, 1])
                cc1.write(f"**{row['Görev']}**")
                y_v = cc2.number_input(L["labels"]["yapilan"], value=int(row['Yapılan']), key=f"v_{g}_{idx}")
                if y_v != row['Yapılan']:
                    u_info['data'].at[idx, 'Yapılan'] = y_v; u_info['xp'] += 10
                    veritabanini_kaydet(st.session_state.db); st.rerun()
                if cc3.button("🗑️", key=f"d_{g}_{idx}"):
                    u_info['data'] = u_info['data'].drop(idx).reset_index(drop=True)
                    veritabanini_kaydet(st.session_state.db); st.rerun()
            with st.form(f"f_{g}", clear_on_submit=True):
                f1, f2, f3 = st.columns([2, 1, 1])
                ng, nh, nb = f1.text_input(L["labels"]["gorev"]), f2.number_input(L["labels"]["hedef"], 1), f3.selectbox(L["labels"]["birim"], ["Soru", "Saat", "Sayfa"])
                if st.form_submit_button(L["butonlar"]["ekle"]):
                    u_info['data'] = pd.concat([u_info['data'], pd.DataFrame([{'Gün': g, 'Görev': ng, 'Hedef': nh, 'Birim': nb, 'Yapılan': 0}])], ignore_index=True)
                    veritabanini_kaydet(st.session_state.db); st.rerun()

# --- ALIŞKANLIKLAR ---
elif menu in ["📊 Alışkanlıklar", "📊 Habits"]:
    st.title("📊 Alışkanlık Takip Sistemi")
    h_df = pd.DataFrame(u_info.get('habits', []), columns=["Alışkanlık", "Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"])
    if h_df.empty: h_df = pd.DataFrame([{"Alışkanlık": "Kitap Okuma 📖", "Pzt": False, "Sal": False, "Çar": False, "Per": False, "Cum": False, "Cmt": False, "Paz": False}])
    edited_h = st.data_editor(h_df, num_rows="dynamic", use_container_width=True, hide_index=True)
    if not h_df.equals(edited_h):
        u_info['habits'] = edited_h.to_dict(orient='records')
        veritabanini_kaydet(st.session_state.db)

# --- SINAVLAR ---
elif menu in ["📅 Sınavlar", "📅 Exams"]:
    st.title(L["basliklar"]["sinavlar"])
    pdf = st.file_uploader("PDF Yükle", type="pdf")
    if pdf and st.button(L["butonlar"]["analiz"]):
        try:
            reader = PyPDF2.PdfReader(pdf); txt = "".join([p.extract_text() for p in reader.pages])
            res = genai.GenerativeModel('gemini-1.5-flash').generate_content(f"Sınavları ayıkla: {txt}").text
            st.info(res)
        except: st.error("AI Meşgul.")
    
    with st.form("ex_f", clear_on_submit=True):
        c1, c2 = st.columns(2); d_a = c1.text_input("Ders"); t_a = c2.date_input("Tarih")
        if st.form_submit_button("Ekle"):
            u_info['sinavlar'].append({'id': str(uuid.uuid4()), 'ders': d_a, 'tarih': str(t_a)})
            veritabanini_kaydet(st.session_state.db); st.rerun()
    for idx, ex in enumerate(u_info.get('sinavlar', [])):
        col1, col2 = st.columns([5, 1])
        col1.info(f"📖 {ex['ders']} - 📅 {ex['tarih']}")
        if col2.button("🗑️", key=f"ex_del_{idx}"):
            u_info['sinavlar'].pop(idx); veritabanini_kaydet(st.session_state.db); st.rerun()

# --- ODAK ---
elif menu in ["⏱️ Odak", "⏱️ Focus"]:
    st.title(L["basliklar"]["pomo"])
    dk = st.select_slider("Dakika", options=[15, 25, 45, 60, 90], value=25)
    if st.button(L["butonlar"]["baslat"]):
        st.session_state.pomo_kalan_saniye = dk * 60; st.session_state.pomo_calisiyor = True; st.rerun()
    m, s = divmod(int(st.session_state.pomo_kalan_saniye), 60)
    st.markdown(f"<h1 style='text-align:center; font-size:150px; color:#4FACFE;'>{m:02d}:{s:02d}</h1>", unsafe_allow_html=True)

# --- AKADEMİK (DEVAMSIZLIK & GNO) ---
elif menu in ["🎓 Akademik", "🎓 Academic"]:
    st.title(L["basliklar"]["akademik"])
    t1, t2 = st.tabs(["📉 Devamsızlık", "📊 GNO Tahmini"])
    with t1:
        with st.expander("➕ Yeni Ders Ekle"):
            with st.form("att_f"):
                dn, dg, dl = st.text_input("Ders"), st.selectbox("Gün", ['Pazartesi','Salı','Çarşamba','Perşembe','Cuma']), st.number_input("Limit", 1, 15, 4)
                if st.form_submit_button("Ekle"):
                    u_info['attendance'].append({"id": str(uuid.uuid4()), "Ders": dn, "Gün": dg, "Limit": dl, "Yapılan": 0})
                    veritabanini_kaydet(st.session_state.db); st.rerun()
        for course in u_info.get('attendance', []):
            with st.container(border=True):
                st.write(f"**{course['Ders']}** - Limit: {course['Limit']}")
                c_id = course.get('id')
                curr = st.number_input(f"Kaçırılan", value=course['Yapılan'], key=f"at_{c_id}")
                if curr != course['Yapılan']:
                    for i, c_item in enumerate(u_info['attendance']):
                        if c_item.get('id') == c_id: u_info['attendance'][i]['Yapılan'] = curr
                    veritabanini_kaydet(st.session_state.db); st.rerun()
    with t2:
        m_gano = st.number_input("Mevcut GNO", 0.0, 4.0, value=float(u_info.get('mevcut_gano', 0.0)))
        m_kredi = st.number_input("Tamamlanan Kredi", 0, 240, value=int(u_info.get('tamamlanan_kredi', 0)))
        if m_gano != u_info['mevcut_gano'] or m_kredi != u_info['tamamlanan_kredi']:
            u_info['mevcut_gano'], u_info['tamamlanan_kredi'] = m_gano, m_kredi
            veritabanini_kaydet(st.session_state.db)

# --- BAŞARILAR ---
elif menu in ["🏆 Başarılar", "🏆 Achievements"]:
    st.title(L["basliklar"]["basari"])
    col1, col2, col3 = st.columns(3)
    col1.metric("RÜTBE", mevcut_lakap_getir(u_info['level'], u_info['dil']))
    col2.metric("SEVİYE", u_info['level'])
    col3.metric("TOPLAM XP", u_info['xp'])
    st.progress(min(u_info['xp'] / (u_info['level'] * 200), 1.0))
    st.divider()
    if u_info.get('pomo_count', 0) >= 10: st.success("🔥 ODAK USTASI ROZETİ")

# --- AYARLAR ---
elif menu in ["⚙️ Ayarlar", "⚙️ Settings"]:
    st.title("⚙️ AYARLAR")
    with st.form("set_f"):
        new_dil = st.selectbox("Dil", ["TR", "EN"], index=0 if u_info['dil'] == 'TR' else 1)
        new_h = st.text_input("Hedef", value=u_info['ana_hedef'])
        if st.form_submit_button("KAYDET"):
            u_info['dil'], u_info['ana_hedef'] = new_dil, new_h
            veritabanini_kaydet(st.session_state.db); st.rerun()

if st.session_state.pomo_calisiyor:
    time.sleep(1); st.rerun()
