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
API_KEY = "AIzaSyBwTbn4D2drDRqRU1-kcyJJvHZuf4KE3gU"
genai.configure(api_key=API_KEY)
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
        "butonlar": {"baslat": "🚀 BAŞLAT", "durdur": "⏸️ DURDUR", "sifirla": "🔄 SIFIRLA", "analiz": "📊 RAPOR OLUŞTUR", "cikis": "🚪 ÇIKIŞ", "ekle": "Ekle", "guncelle": "GÜNCELLE"},
        "basliklar": {"takip": "📝 GÜNLÜK TAKİP", "onizleme": "🗓️ Haftalık Önizleme", "mentor": "💬 MENTOR SOHBETİ", "sinavlar": "📅 SINAVLAR", "pomo": "⏱️ ODAK", "basari": "🏆 BAŞARILAR"},
        "labels": {"hedef": "Hedef", "yapilan": "Yapılan", "birim": "Birim", "gorev": "Görev", "sifre": "Şifre", "seviye": "Eğitim Düzeyi", "rutbe": "Rütbe", "xp_durum": "XP Durumu"}
    },
    "EN": {
        "menu": ["🏠 Dashboard", "📅 Exams", "⏱️ Focus", "🤖 AI Mentor", "🏆 Achievements", "⚙️ Settings"],
        "butonlar": {"baslat": "🚀 START", "durdur": "⏸️ PAUSE", "sifirla": "🔄 RESET", "analiz": "📊 CREATE REPORT", "cikis": "🚪 LOGOUT", "ekle": "Add", "guncelle": "UPDATE"},
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
                    defaults = {'xp': 0, 'level': 1, 'egitim_duzeyi': 'Üniversite', 'ana_hedef': 'Gelişim', 'sinavlar': [], 'chat_history': [], 'pomo_count': 0, 'dil': 'TR'}
                    for k, v in defaults.items():
                        if k not in data[u]: data[u][k] = v
                    df = pd.DataFrame(data[u]['data'])
                    if 'Yapılan' not in df.columns: df['Yapılan'] = 0
                    if 'Gün' not in df.columns: df['Gün'] = ""
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

# --- 2. SİSTEM & POMODORO MANTIĞI ---
if 'db' not in st.session_state: st.session_state.db = veritabanini_yukle()
if 'pomo_kalan_saniye' not in st.session_state: st.session_state.pomo_kalan_saniye = 25 * 60
if 'pomo_calisiyor' not in st.session_state: st.session_state.pomo_calisiyor = False
if 'son_guncelleme' not in st.session_state: st.session_state.son_guncelleme = time.time()

# BENİ HATIRLA KONTROLÜ
if 'aktif_kullanici' not in st.session_state:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                st.session_state.aktif_kullanici = config.get('user')
        except: pass

if st.session_state.pomo_calisiyor:
    simdi = time.time()
    st.session_state.pomo_kalan_saniye -= (simdi - st.session_state.son_guncelleme)
    st.session_state.son_guncelleme = simdi
    if st.session_state.pomo_kalan_saniye <= 0:
        st.session_state.pomo_calisiyor = False
        st.session_state.pomo_kalan_saniye = 0
        if 'aktif_kullanici' in st.session_state:
            u = st.session_state.aktif_kullanici
            st.session_state.db[u]['xp'] += 30; st.session_state.db[u]['pomo_count'] += 1
            veritabanini_kaydet(st.session_state.db); st.balloons()

# --- 3. GİRİŞ EKRANI ---
if 'aktif_kullanici' not in st.session_state or st.session_state.aktif_kullanici is None:
    st.title("🚀 ROTA AI")
    t1, t2 = st.tabs(["🔑 GİRİŞ", "📝 KAYIT"])
    with t1:
        u = st.text_input("Kullanıcı", key="l_u")
        p = st.text_input("Şifre", type="password", key="l_p")
        beni_hatirla = st.checkbox("Beni Hatırla")
        if st.button("GİRİŞ YAP"):
            if u in st.session_state.db and st.session_state.db[u]['password'] == p:
                st.session_state.aktif_kullanici = u
                if beni_hatirla:
                    with open(CONFIG_FILE, "w") as f: json.dump({'user': u}, f)
                st.rerun()
            else: st.error("Hatalı!")
    with t2:
        nu = st.text_input("Yeni Ad", key="r_u"); np = st.text_input("Şifre", type="password", key="r_p")
        if st.button("KAYDOL"):
            st.session_state.db[nu] = {'password': np, 'xp': 0, 'level': 1, 'egitim_duzeyi': 'Üniversite', 'ana_hedef': 'Gelişim', 'dil': 'TR', 'data': pd.DataFrame(columns=['Gün', 'Görev', 'Hedef', 'Birim', 'Yapılan'])}
            veritabanini_kaydet(st.session_state.db); st.success("Kaydolundu!")
    st.stop()

u_id = st.session_state.aktif_kullanici
u_info = st.session_state.db[u_id]
L = DIL_PAKETI[u_info.get('dil', 'TR')]

# --- 4. SIDEBAR ---
st.sidebar.title("🚀 ROTA AI")
st.sidebar.markdown(f"🏆 **{L['labels']['rutbe']}:** {mevcut_lakap_getir(u_info['level'], u_info['dil'])}")
st.sidebar.metric("SEVİYE", u_info['level'], f"{u_info['xp']} XP")
tema_rengi = st.sidebar.color_picker("TEMA", "#4FACFE")
st.markdown(f"<style>h1, h2, h3 {{ color: {tema_rengi} !important; }} div.stButton > button:first-child {{ background-color: {tema_rengi}; color: white; }}</style>", unsafe_allow_html=True)

menu = st.sidebar.radio("NAVİGASYON", L["menu"])
if st.sidebar.button(L["butonlar"]["cikis"]):
    if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)
    st.session_state.aktif_kullanici = None; st.rerun()

# --- 5. PANEL ---
if menu in ["🏠 Panel", "🏠 Dashboard"]:
    st.title(f"✨ {u_id.upper()}")
    if not u_info['data'].empty:
        c1, c2 = st.columns([2, 1])
        with c1:
            fig = go.Figure([go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Hedef'], name=L["labels"]["hedef"], marker_color='#E0E0E0'),
                             go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Yapılan'], name=L["labels"]["yapilan"], marker_color=tema_rengi)])
            fig.update_layout(height=250, barmode='group'); st.plotly_chart(fig, use_container_width=True)
        with c2:
            ty, th = u_info['data']['Yapılan'].sum(), u_info['data']['Hedef'].sum()
            st.plotly_chart(go.Figure(go.Pie(labels=[L['labels']['yapilan'], 'Kalan'], values=[ty, max(0, th - ty)], hole=.6, marker_colors=[tema_rengi, '#FF5252'])).update_layout(height=250, showlegend=False), use_container_width=True)

    st.divider(); st.subheader(L["basliklar"]["onizleme"])
    gunler = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
    cols = st.columns(7)
    for i, g in enumerate(gunler):
        with cols[i]:
            st.markdown(f"<div style='background:{tema_rengi}; color:white; text-align:center; border-radius:5px; font-weight:bold;'>{g[:3].upper()}</div>", unsafe_allow_html=True)
            temp_gun = u_info['data'][u_info['data']['Gün'] == g]
            for _, r in temp_gun.iterrows(): st.caption(f"• {r['Görev']}")

    st.divider(); st.subheader(L["basliklar"]["takip"])
    for g in gunler:
        with st.expander(f"📅 {g.upper()}"):
            temp = u_info['data'][u_info['data']['Gün'] == g]
            for idx, row in temp.iterrows():
                cc1, cc2, cc3 = st.columns([3, 2, 1])
                cc1.write(f"**{row['Görev']}** ({row['Birim']})")
                y_v = cc2.number_input(L["labels"]["yapilan"], value=int(row['Yapılan']), key=f"y_{g}_{idx}")
                if y_v != row['Yapılan']:
                    u_info['xp'] += 10
                    if u_info['xp'] >= (u_info['level'] * 200): u_info['level'] += 1; st.balloons()
                    u_info['data'].at[idx, 'Yapılan'] = y_v; veritabanini_kaydet(st.session_state.db); st.rerun()
                if cc3.button("🗑️", key=f"d_{g}_{idx}"): u_info['data'] = u_info['data'].drop(idx); veritabanini_kaydet(st.session_state.db); st.rerun()
            with st.form(f"f_{g}", clear_on_submit=True):
                f1, f2, f3 = st.columns([2, 1, 1])
                ng, nh, nb = f1.text_input(L['labels']['gorev']), f2.number_input(L['labels']['hedef'], 1), f3.selectbox(L['labels']['birim'], ["Konu", "Soru", "Sayfa", "Saat"])
                if st.form_submit_button(L["butonlar"]["ekle"]):
                    u_info['data'] = pd.concat([u_info['data'], pd.DataFrame([{'Gün': g, 'Görev': ng, 'Hedef': nh, 'Birim': nb, 'Yapılan': 0}])], ignore_index=True)
                    veritabanini_kaydet(st.session_state.db); st.rerun()

# --- 6. AI MENTOR ---
elif menu in ["🤖 AI Mentor"]:
    st.title("🤖 AI MENTOR")
    if st.button(L["butonlar"]["analiz"]):
        with st.spinner("Analiz ediliyor..."):
            res = genai.GenerativeModel('gemini-1.5-flash-latest').generate_content(f"Sen bir mentorsun. Seviye: {u_info['egitim_duzeyi']}. Hedef: {u_info['ana_hedef']}. Veriler: {u_info['data'].to_string()}").text
            st.info(res)
    st.divider()
    ch = st.container(height=300)
    for m in u_info.get('chat_history', []): ch.chat_message(m['role']).write(m['text'])
    p_m = st.chat_input("Mentorunla konuş...")
    if p_m:
        u_info['chat_history'].append({"role": "user", "text": p_m})
        try:
            res = genai.GenerativeModel('gemini-1.5-flash-latest').generate_content(p_m).text
            u_info['chat_history'].append({"role": "assistant", "text": res})
            veritabanini_kaydet(st.session_state.db); st.rerun()
        except: st.warning("Hata!")

# --- 7. ODAK (POMODORO) ---
elif menu in ["⏱️ Odak", "⏱️ Focus"]:
    st.title(L["basliklar"]["pomo"])
    if not st.session_state.pomo_calisiyor:
        pdk = st.select_slider("Dakika Seç", options=[15, 25, 30, 45, 60, 90], value=25)
        st.session_state.pomo_kalan_saniye = pdk * 60

    c1, c2, c3 = st.columns(3)
    if c1.button(L["butonlar"]["baslat"], use_container_width=True):
        st.session_state.pomo_calisiyor = True
        st.session_state.son_guncelleme = time.time()
        st.rerun()
    if c2.button(L["butonlar"]["durdur"], use_container_width=True):
        st.session_state.pomo_calisiyor = False
        st.rerun()
    if c3.button(L["butonlar"]["sifirla"], use_container_width=True):
        st.session_state.pomo_calisiyor = False
        st.session_state.pomo_kalan_saniye = 25 * 60
        st.rerun()
    
    m, s = divmod(max(0, int(st.session_state.pomo_kalan_saniye)), 60)
    st.markdown(f"<h1 style='text-align:center; font-size:100px;'>{m:02d}:{s:02d}</h1>", unsafe_allow_html=True)

# --- 8. SINAVLAR ---
elif menu in ["📅 Sınavlar", "📅 Exams"]:
    st.title(L["basliklar"]["sinavlar"])
    pdf = st.file_uploader("Sınav Takvimi (PDF)", type="pdf")
    if pdf and st.button("Sınavları Çıkar"):
        reader = PyPDF2.PdfReader(pdf); text = "".join([p.extract_text() for p in reader.pages])
        try:
            res = genai.GenerativeModel('gemini-1.5-flash-latest').generate_content(f"JSON sınav çıkar: {text}").text
            st.info(res)
        except: st.error("Hata!")
    with st.form("ms"):
        c1, c2 = st.columns(2); d, t = c1.text_input("Ders"), c2.date_input("Tarih")
        if st.form_submit_button("Ekle"):
            u_info['sinavlar'].append({'ders': d, 'tarih': t.strftime("%d.%m.%Y")}); veritabanini_kaydet(st.session_state.db); st.rerun()
    for s in u_info['sinavlar']: st.warning(f"📌 {s['ders']} | {s['tarih']}")

# --- 9. BAŞARILAR ---
elif menu in ["🏆 Başarılar", "🏆 Achievements"]:
    st.title(L["basliklar"]["basari"])
    k1, k2, k3 = st.columns(3)
    k1.metric(L["labels"]["rutbe"], mevcut_lakap_getir(u_info['level'], u_info['dil']))
    k2.metric("SEVİYE", u_info['level'])
    k3.metric("TOPLAM XP", u_info['xp'])
    st.divider()
    sx = u_info['level'] * 200
    st.write(f"**{L['labels']['xp_durum']}** ({u_info['xp']} / {sx})")
    st.progress(min(u_info['xp'] / sx, 1.0))
    st.divider(); st.subheader("🏅 Koleksiyonun")
    b1, b2, b3 = st.columns(3)
    if u_info.get('pomo_count', 0) >= 10: b1.success("🔥 ODAK USTASI")
    else: b1.info(f"🔒 ODAK USTASI ({u_info.get('pomo_count', 0)}/10)")
    if u_info['level'] >= 10: b2.success("👑 VİZYONER")
    else: b2.info("🔒 VİZYONER (Lvl 10)")

# --- 10. AYARLAR ---
elif menu in ["⚙️ Ayarlar", "⚙️ Settings"]:
    st.title(L["menu"][-1])
    with st.form("ayarlar"):
        nl = st.selectbox("Dil", ["TR", "EN"], index=0 if u_info['dil'] == 'TR' else 1)
        ns = st.text_input(L['labels']['sifre'], u_info['password'], type="password")
        ne = st.selectbox(L['labels']['seviye'], ["Üniversite", "Lise", "Ortaokul", "Diğer"])
        nh = st.text_input("Ana Hedef", u_info['ana_hedef'])
        if st.form_submit_button(L["butonlar"]["guncelle"]):
            u_info['dil'], u_info['password'], u_info['egitim_duzeyi'], u_info['ana_hedef'] = nl, ns, ne, nh
            veritabanini_kaydet(st.session_state.db); st.success("Tamam!"); st.rerun()

if st.session_state.pomo_calisiyor:
    time.sleep(1)
    st.rerun()
