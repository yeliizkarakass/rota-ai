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

# --- 0. TARAYICI SEKME AYARI ---
st.set_page_config(page_title="ROTA AI", page_icon="🚀", layout="wide")

# --- 1. VERİ YÖNETİMİ VE API ---
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
        "menu": ["🏠 Panel", "📅 Sınavlar", "⏱️ Odak", "🎓 Akademik", "🤖 AI Mentor", "🏆 Başarılar", "⚙️ Ayarlar"],
        "butonlar": {"baslat": "🚀 BAŞLAT", "durdur": "⏸️ DURDUR", "sifirla": "🔄 SIFIRLA", "analiz": "📊 RAPOR OLUŞTUR", "cikis": "🚪 ÇIKIŞ", "ekle": "Ekle"},
        "basliklar": {"takip": "📝 GÜNLÜK TAKİP", "onizleme": "🗓️ Haftalık Önizleme", "mentor": "💬 MENTOR SOHBETİ", "sinavlar": "📅 SINAVLAR", "pomo": "⏱️ ODAK", "basari": "🏆 BAŞARILAR", "akademik": "🎓 AKADEMİK YÖNETİM"},
        "labels": {"hedef": "Hedef", "yapilan": "Yapılan", "birim": "Birim", "gorev": "Görev", "sifre": "Şifre", "seviye": "Eğitim Düzeyi", "rutbe": "Rütbe", "xp_durum": "XP Durumu"}
    },
    "EN": {
        "menu": ["🏠 Dashboard", "📅 Exams", "⏱️ Focus", "🎓 Academic", "🤖 AI Mentor", "🏆 Achievements", "⚙️ Settings"],
        "butonlar": {"baslat": "🚀 START", "durdur": "⏸️ PAUSE", "sifirla": "🔄 RESET", "analiz": "📊 CREATE REPORT", "cikis": "🚪 LOGOUT", "ekle": "Add"},
        "basliklar": {"takip": "📝 DAILY TRACKING", "onizleme": "🗓️ Weekly Preview", "mentor": "💬 MENTOR CHAT", "sinavlar": "📅 EXAMS", "pomo": "⏱️ FOCUS", "basari": "🏆 ACHIEVEMENTS", "akademik": "🎓 ACADEMIC MANAGEMENT"},
        "labels": {"hedef": "Target", "yapilan": "Done", "birim": "Unit", "gorev": "Task", "sifre": "Password", "seviye": "Education Level", "rutbe": "Rank", "xp_durum": "XP Status"}
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
                    defaults = {'xp':0, 'level':1, 'egitim_duzeyi':'Üniversite', 'ana_hedef':'Gelişim', 'sinavlar':[], 'chat_history':[], 'pomo_count':0}
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
            'password': db[u]['password'], 'ana_hedef': db[u].get('ana_hedef', 'Gelişim'),
            'egitim_duzeyi': db[u].get('egitim_duzeyi', 'Üniversite'),
            'xp': db[u].get('xp', 0), 'level': db[u].get('level', 1),
            'pomo_count': db[u].get('pomo_count', 0), 'chat_history': db[u].get('chat_history', []),
            'sinavlar': db[u].get('sinavlar', []), 'data': db[u]['data'].to_dict(orient='records')
        }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=4)

# --- 2. SESSION VE OTOMATİK GİRİŞ ---
if 'db' not in st.session_state: st.session_state.db = veritabanini_yukle()
if 'pomo_kalan_saniye' not in st.session_state: st.session_state.pomo_kalan_saniye = 25 * 60
if 'pomo_calisiyor' not in st.session_state: st.session_state.pomo_calisiyor = False
if 'son_guncelleme' not in st.session_state: st.session_state.son_guncelleme = time.time()

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
        if 'aktif_kullanici' in st.session_state:
            u = st.session_state.aktif_kullanici
            st.session_state.db[u]['xp'] += 30; st.session_state.db[u]['pomo_count'] += 1
            veritabanini_kaydet(st.session_state.db); st.balloons()

# --- 3. GİRİŞ/KAYIT EKRANI ---
if 'aktif_kullanici' not in st.session_state or st.session_state.aktif_kullanici is None:
    st.markdown("<h1 style='text-align: center; color: #4FACFE;'>🚀 ROTA AI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Geleceğin Mühendisi İçin Akıllı Planlama Asistanı</p>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔑 GİRİŞ", "📝 KAYIT"])
    with t1:
        u = st.text_input("Kullanıcı", key="l_u")
        p = st.text_input("Şifre", type="password", key="l_p")
        beni_hatirla = st.checkbox("Beni Hatırla", key="remember_me")
        if st.button("GİRİŞ YAP", key="b_l"):
            if u in st.session_state.db and st.session_state.db[u]['password'] == p:
                st.session_state.aktif_kullanici = u
                if beni_hatirla:
                    with open(CONFIG_FILE, "w") as f: json.dump({'user': u}, f)
                st.rerun()
            else: st.error("Hatalı Giriş!")
    with t2:
        nu = st.text_input("Ad", key="r_u")
        np = st.text_input("Şifre", type="password", key="r_p")
        ne = st.selectbox("Seviye", ["Üniversite", "Lise", "Ortaokul", "Diğer"], key="r_e")
        nh = st.text_input("Hedef", key="r_h")
        if st.button("KAYDOL", key="b_r"):
            st.session_state.db[nu] = {'password':np, 'xp':0, 'level':1, 'egitim_duzeyi':ne, 'ana_hedef':nh, 'data':pd.DataFrame(columns=['Gün','Görev','Hedef','Birim','Yapılan'])}
            veritabanini_kaydet(st.session_state.db); st.success("Kaydolundu!")
    st.stop()

u_id = st.session_state.aktif_kullanici
u_info = st.session_state.db[u_id]

# --- 4. SIDEBAR VE TEMA AYARI ---
st.sidebar.title("🚀 ROTA AI")
st.sidebar.markdown(f"**Profil:** {u_id}")
st.sidebar.caption(f"{u_info['egitim_duzeyi']} | {u_info['ana_hedef']}")
st.sidebar.divider()
st.sidebar.metric("SEVİYE", u_info['level'], f"{u_info['xp']} XP")

# TEMA RENGİ SEÇİCİ
tema_rengi = st.sidebar.color_picker("⚙️ TEMA RENGİNİ SEÇ", "#4FACFE")

# CSS İLE TEMAYI TÜM SİTEYE YAYMA
st.markdown(f"""
    <style>
    /* Başlıklar */
    h1, h2, h3, .stSubheader {{ color: {tema_rengi} !important; }}
    /* Butonlar */
    div.stButton > button:first-child {{
        background-color: {tema_rengi};
        color: white;
        border: none;
    }}
    /* Sidebar başlıkları */
    .sidebar .sidebar-content {{ background-image: linear-gradient(#2e7bcf,#2e7bcf); }}
    /* Slider ve Progress Bar */
    .stProgress > div > div > div > div {{ background-color: {tema_rengi} !important; }}
    </style>
""", unsafe_allow_html=True)

if st.sidebar.button("📊 ANALİZ ET", key="b_ai"):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        res = model.generate_content(f"Planı analiz et: {u_info['data'].to_string()}").text
        st.sidebar.info(res)
    except: st.sidebar.warning("AI şu an meşgul.")

menu = st.sidebar.radio("NAVİGASYON", ["🏠 Panel", "📅 Sınavlar", "⏱️ Odak", "🏆 Başarılar", "⚙️ Ayarlar"])
if st.sidebar.button("🚪 ÇIKIŞ", key="b_out"):
    if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)
    st.session_state.aktif_kullanici = None; st.rerun()

# --- 5. ÜST SAYAÇ ---
if st.session_state.pomo_calisiyor:
    m, s = divmod(max(0, int(st.session_state.pomo_kalan_saniye)), 60)
    st.markdown(f"""<div style="background-color:{tema_rengi}; color:white; padding:10px; border-radius:10px; text-align:center; font-weight:bold; margin-bottom:15px;">⏱️ ODAK SEANSI: {m:02d}:{s:02d}</div>""", unsafe_allow_html=True)

# --- 6. PANEL ---
if menu == "🏠 Panel":
    st.title(f"✨ PANEL | {u_id.upper()}")
    if not u_info['data'].empty:
        c1, c2 = st.columns([2, 1])
        with c1:
            fig = go.Figure([go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Hedef'], name='Hedef', marker_color='#E0E0E0'),
                             go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Yapılan'], name='Yapılan', marker_color=tema_rengi)])
            fig.update_layout(height=250, barmode='group', margin=dict(l=0,r=0,t=0,b=0)); st.plotly_chart(fig, use_container_width=True)
        with c2:
            ty, th = u_info['data']['Yapılan'].sum(), u_info['data']['Hedef'].sum()
            st.plotly_chart(go.Figure(go.Pie(labels=['Biten','Kalan'], values=[ty, max(0,th-ty)], hole=.6, marker_colors=[tema_rengi, '#FF5252'])).update_layout(height=250, showlegend=False), use_container_width=True)

    st.divider(); st.subheader("🗓️ Haftalık Önizleme")
    gunler = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
    cols = st.columns(7)
    for i, g in enumerate(gunler):
        with cols[i]:
            st.markdown(f"<div style='background:{tema_rengi}; color:white; text-align:center; border-radius:5px; font-weight:bold;'>{g[:3].upper()}</div>", unsafe_allow_html=True)
            for _, r in u_info['data'][u_info['data']['Gün'] == g].iterrows(): st.markdown(f"**• {r['Görev']}**")

    st.divider(); st.subheader("📝 GÜNLÜK TAKİP")
    for g in gunler:
        with st.expander(f"📅 {g.upper()}"):
            temp = u_info['data'][u_info['data']['Gün'] == g]
            for idx, row in temp.iterrows():
                cc1, cc2, cc3 = st.columns([3, 2, 1])
                cc1.write(f"**{row['Görev']}**")
                y_v = cc2.number_input(f"Yapılan", value=int(row['Yapılan']), key=f"y_{g}_{idx}")
                if y_v != row['Yapılan']:
                    if y_v > row['Yapılan']: u_info['xp'] += 10
                    if u_info['xp'] >= (u_info['level'] * 150): u_info['level'] += 1; st.balloons()
                    u_info['data'].at[idx, 'Yapılan'] = y_v; veritabanini_kaydet(st.session_state.db); st.rerun()
                if cc3.button("🗑️", key=f"d_{g}_{idx}"): u_info['data'] = u_info['data'].drop(idx); veritabanini_kaydet(st.session_state.db); st.rerun()
            with st.form(f"f_{g}", clear_on_submit=True):
                f1, f2, f3 = st.columns([2,1,1])
                ng, nh, nb = f1.text_input("Görev"), f2.number_input("Hedef", 1), f3.selectbox("Birim", ["Soru", "Sayfa", "Saat"])
                if st.form_submit_button("Ekle"):
                    u_info['data'] = pd.concat([u_info['data'], pd.DataFrame([{'Gün':g, 'Görev':ng, 'Hedef':nh, 'Birim':nb, 'Yapılan':0}])], ignore_index=True)
                    veritabanini_kaydet(st.session_state.db); st.rerun()

    st.divider(); st.subheader("💬 AI MENTOR")
    ch = st.container(height=300)
    for m in u_info.get('chat_history', []): ch.chat_message(m['role']).write(m['text'])
    p_m = st.chat_input("Derslerin hakkında konuş...")
    if p_m:
        try:
            res = genai.GenerativeModel('gemini-1.5-flash-latest').generate_content(p_m).text
            u_info['chat_history'].append({"role":"user", "text":p_m}); u_info['chat_history'].append({"role":"assistant", "text":res})
            veritabanini_kaydet(st.session_state.db); st.rerun()
        except: st.warning("Mentor meşgul.")

elif menu == "📅 Sınavlar":
    st.title("📅 SINAVLAR")
    t1, t2 = st.tabs(["📄 PDF", "✍️ MANUEL"])
    with t1:
        pdf = st.file_uploader("Yükle", type="pdf")
        if pdf:
            reader = PyPDF2.PdfReader(pdf); text = "".join([p.extract_text() for p in reader.pages])
            try:
                model = genai.GenerativeModel('gemini-1.5-flash-latest')
                res = model.generate_content(f"JSON sınav çıkar: {text}").text
                s, e = res.find('['), res.rfind(']') + 1
                tum_s = json.loads(res[s:e])
                sec = st.multiselect("Ders:", [f"{x['ders']} | {x['tarih']}" for x in tum_s])
                if st.button("Kaydet"):
                    u_info['sinavlar'] += [x for x in tum_s if f"{x['ders']} | {x['tarih']}" in sec]
                    veritabanini_kaydet(st.session_state.db); st.rerun()
            except: st.error("Hata!")
    with t2:
        with st.form("m"):
            md, mt = st.text_input("Ders"), st.date_input("Tarih")
            if st.form_submit_button("Ekle"):
                u_info['sinavlar'].append({'ders':md, 'tarih':mt.strftime("%d.%m.%Y")}); veritabanini_kaydet(st.session_state.db); st.rerun()
    for i, s in enumerate(u_info['sinavlar']):
        c1, c2 = st.columns([5,1])
        c1.info(f"{s['ders']} - {s['tarih']}")
        if c2.button("🗑️", key=f"s_{i}"): u_info['sinavlar'].pop(i); veritabanini_kaydet(st.session_state.db); st.rerun()

elif menu == "⏱️ Odak":
    st.title("⏱️ ODAK")
    pdk = st.select_slider("Süre", options=[15, 25, 30, 45, 60], value=25)
    if st.button("🚀 BAŞLAT"):
        st.session_state.pomo_kalan_saniye = pdk * 60; st.session_state.pomo_calisiyor = True
        st.session_state.son_guncelleme = time.time(); st.rerun()
    m, s = divmod(max(0, int(st.session_state.pomo_kalan_saniye)), 60)
    st.markdown(f"<h1 style='text-align:center; font-size:150px;'>{m:02d}:{s:02d}</h1>", unsafe_allow_html=True)

elif menu == "🏆 Başarılar":
    st.title("🏆 BAŞARILAR")
    col1, col2, col3 = st.columns(3)
    p_sayisi = u_info.get('pomo_count', 0)
    with col1:
        if p_sayisi >= 10: st.success("🔥 ODAK USTASI\n\n10 Pomodoro Bitti!")
        else: st.info(f"🔒 ODAK USTASI\n\n{p_sayisi}/10")
    with col2:
        if u_info['level'] >= 5: st.warning("👑 SADIK ÜYE\n\nLvl 5 Başarı!")
        else: st.info(f"🔒 SADIK ÜYE\n\nHedef: Level 5")
    with col3:
        if u_info['xp'] >= 1000: st.error("🌟 XP AVCIYSI\n\n1000 XP Geçildi!")
        else: st.info(f"🔒 XP AVCIYSI\n\nHedef: 1000 XP")

elif menu == "⚙️ Ayarlar":
    st.title("⚙️ AYARLAR")
    with st.form("settings"):
        nh, ne, ns = st.text_input("Hedef", u_info['ana_hedef']), st.selectbox("Seviye", ["Üniversite", "Lise", "Ortaokul", "Diğer"]), st.text_input("Şifre", u_info['password'], type="password")
        if st.form_submit_button("GÜNCELLE"):
            u_info['ana_hedef'], u_info['egitim_duzeyi'], u_info['password'] = nh, ne, ns
            veritabanini_kaydet(st.session_state.db); st.success("Güncellendi!"); time.sleep(1); st.rerun()

if st.session_state.pomo_calisiyor: time.sleep(1); st.rerun()
