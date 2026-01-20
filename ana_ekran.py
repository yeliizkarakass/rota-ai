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

# --- 1. VERİ ---
DB_FILE = "rota_database.json"

# API Ayarı
try:
    if "GEMINI_API_KEY" in st.secrets:
        API_KEY = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=API_KEY)
except:
    API_KEY = None

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
                    defaults = {'xp': 0, 'level': 1, 'ana_hedef': 'Mühendis', 'sinavlar': [], 'chat_history': [], 'notes': [], 'pomo_count': 0, 'dil': 'TR', 'habits': [], 'attendance': [], 'gpa_list': [], 'mevcut_gano': 0.0, 'tamamlanan_kredi': 0}
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
        # Pandas DataFrame'i JSON'a çevirmek için listeye döndürür
        u_dict = db[u].copy()
        if isinstance(u_dict['data'], pd.DataFrame):
            u_dict['data'] = u_dict['data'].to_dict(orient='records')
        to_save[u] = u_dict
    
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=4)
        f.flush() # Dosyayı fiziksel olarak yazmaya zorlar
        os.fsync(f.fileno()) # İşletim sistemine 'şimdi yaz' der

if 'db' not in st.session_state: st.session_state.db = veritabanini_yukle()
if 'pomo_kalan_saniye' not in st.session_state: st.session_state.pomo_kalan_saniye = 25 * 60
if 'pomo_calisiyor' not in st.session_state: st.session_state.pomo_calisiyor = False
if 'son_guncelleme' not in st.session_state: st.session_state.son_guncelleme = time.time()

if 'aktif_kullanici' not in st.session_state:
    st.session_state.aktif_kullanici = None

if st.session_state.aktif_kullanici is None:
    st.title("🚀 ROTA AI")
    t1, t2 = st.tabs(["🔑 GİRİŞ", "📝 KAYIT"])
    with t1:
        u = st.text_input("Kullanıcı", key="l_u")
        p = st.text_input("Şifre", type="password", key="l_p")
        if st.button("GİRİŞ YAP"):
            if u in st.session_state.db and st.session_state.db[u]['password'] == p:
                st.session_state.aktif_kullanici = u
                st.rerun()
            else: st.error("Hatalı Giriş!")
    with t2:
        nu = st.text_input("Yeni Kullanıcı Adı", key="r_u")
        np = st.text_input("Şifre Belirle", type="password", key="r_p")
        if st.button("HESAP OLUŞTUR"):
            if nu and np:
                if nu not in st.session_state.db:
                    new_df = pd.DataFrame(columns=['Gün', 'Görev', 'Hedef', 'Birim', 'Yapılan'])
                    st.session_state.db[nu] = {'password': np, 'xp': 0, 'level': 1, 'ana_hedef': 'Mühendis', 'data': new_df, 'attendance': [], 'gpa_list': [], 'mevcut_gano': 0.0, 'tamamlanan_kredi': 0}
                    veritabanini_kaydet(st.session_state.db)
                    st.success("Kayıt Başarılı! Artık Giriş Sekmesine Geçebilirsiniz.")
                else: st.warning("Kullanıcı mevcut.")
    st.stop()

u_id = st.session_state.aktif_kullanici
u_info = st.session_state.db[u_id]
L = DIL_PAKETI.get(u_info.get('dil', 'TR'), DIL_PAKETI["TR"])

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
st.sidebar.metric(L["labels"]["rutbe"], mevcut_lakap_getir(u_info['level'], u_info.get('dil', 'TR')))

menu = st.sidebar.radio("NAVİGASYON", L["menu"])

st.sidebar.subheader("📌 Hızlı Notlar")
df_n = pd.DataFrame(u_info.get('notes', []), columns=["Kategori", "Not"])
if df_n.empty: df_n = pd.DataFrame([{"Kategori": "🔵 Ders", "Not": "Not..."}])
edited_n = st.sidebar.data_editor(df_n, num_rows="dynamic", use_container_width=True, hide_index=True, key="side_notes_final")
if not df_n.equals(edited_n):
    u_info['notes'] = edited_n.to_dict(orient='records')
    veritabanini_kaydet(st.session_state.db)

if st.sidebar.button(L["butonlar"]["cikis"]):
    st.session_state.aktif_kullanici = None; st.rerun()

# PANEL
if menu in ["🏠 Panel", "🏠 Dashboard"]:
    st.title(f"✨ {u_info.get('ana_hedef', 'Mühendis').upper()} {u_id.upper()}")
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
            temp_g = u_info['data'][u_info['data']['Gün'] == g]
            for _, r in temp_g.iterrows(): st.caption(f"• {r['Görev']}")

    st.divider(); st.subheader(L["basliklar"]["takip"])
    for g in gunler:
        with st.expander(f"📅 {g.upper()} GÖREVLERİ"):
            temp = u_info['data'][u_info['data']['Gün'] == g]
            for idx, row in temp.iterrows():
                cc1, cc2, cc3 = st.columns([3, 2, 1])
                cc1.write(f"**{row['Görev']}**")
                y_v = cc2.number_input(L["labels"]["yapilan"], value=int(row['Yapılan']), key=f"v_{g}_{idx}")
                if y_v != row['Yapılan']:
                    u_info['data'].at[idx, 'Yapılan'] = y_v
                    u_info['xp'] += 10
                    veritabanini_kaydet(st.session_state.db); st.rerun()
                if cc3.button("🗑️", key=f"d_{g}_{idx}"):
                    u_info['data'] = u_info['data'].drop(idx).reset_index(drop=True)
                    veritabanini_kaydet(st.session_state.db); st.rerun()
            with st.form(f"f_{g}", clear_on_submit=True):
                f1, f2, f3 = st.columns([2, 1, 1])
                ng, nh, nb = f1.text_input(L["labels"]["gorev"]), f2.number_input(L["labels"]["hedef"], 1), f3.selectbox(L["labels"]["birim"], ["Soru", "Saat", "Konu"])
                if st.form_submit_button(L["butonlar"]["ekle"]):
                    u_info['data'] = pd.concat([u_info['data'], pd.DataFrame([{'Gün': g, 'Görev': ng, 'Hedef': nh, 'Birim': nb, 'Yapılan': 0}])], ignore_index=True)
                    veritabanini_kaydet(st.session_state.db); st.rerun()

    st.divider()
    st.subheader("📊 Alışkanlık Takipçisi")
    h_df = pd.DataFrame(u_info.get('habits', []), columns=["Alışkanlık", "Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"])
    if h_df.empty: h_df = pd.DataFrame([{"Alışkanlık": "05:30 Kalkış ⏰", "Pzt": False, "Sal": False, "Çar": False, "Per": False, "Cum": False, "Cmt": False, "Paz": False}])
    e_habits = st.data_editor(h_df, num_rows="dynamic", use_container_width=True, hide_index=True, key="h_editor")
    if not h_df.equals(e_habits):
        u_info['habits'] = e_habits.to_dict(orient='records'); veritabanini_kaydet(st.session_state.db)
    for _, row in e_habits.iterrows():
        tik = sum([1 for gun in ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"] if row.get(gun, False) is True])
        c_h1, c_h2 = st.columns([3, 7])
        c_h1.caption(f"**{row['Alışkanlık']}**")
        c_h2.progress(tik / 7, text=f"⭐ %{int((tik/7)*100)}")

elif menu in ["📅 Sınavlar", "📅 Exams"]:
    st.title(L["basliklar"]["sinavlar"])
    pdf = st.file_uploader("PDF", type="pdf")
    if pdf and st.button("Analiz ✨"):
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(pdf); txt = "".join([p.extract_text() for p in reader.pages])
            res = genai.GenerativeModel('gemini-1.5-flash').generate_content(f"Sınavları listele: {txt}").text
            st.info(res)
        except: st.error("AI Meşgul.")
    
    with st.form("ex_f", clear_on_submit=True):
        c1, c2 = st.columns(2); d_a = c1.text_input("Ders"); t_a = c2.date_input("Tarih")
        if st.form_submit_button("Ekle"):
            u_info['sinavlar'].append({'id': str(uuid.uuid4()), 'ders': d_a, 'tarih': str(t_a)})
            veritabanini_kaydet(st.session_state.db); st.rerun()

    if u_info['sinavlar']:
        st.write("---")
        for idx, ex in enumerate(u_info['sinavlar']):
            sc1, sc2, sc3 = st.columns([3, 2, 1])
            sc1.write(f"📖 **{ex['ders']}**")
            sc2.write(f"📅 {ex['tarih']}")
            if sc3.button("🗑️", key=f"ex_del_{idx}"):
                u_info['sinavlar'].pop(idx)
                veritabanini_kaydet(st.session_state.db); st.rerun()

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

elif menu in ["🎓 Akademik", "🎓 Academic"]:
    st.title(L["basliklar"]["akademik"])
    t1, t2 = st.tabs(["📉 Devamsızlık", "📊 GNO Tahmini"])
    with t1:
        st.subheader("🗓️ Ders Katılımı")
        c_top1, c_top2 = st.columns([3, 1])
        with c_top1:
            with st.expander("➕ Yeni Ders Ekle"):
                with st.form("att_new_form"):
                    c_n = st.text_input("Ders Adı")
                    c_d = st.selectbox("Gün", ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"])
                    c_l = st.number_input("Limit", 1, 15, 4)
                    if st.form_submit_button("Ekle"):
                        u_info['attendance'].append({"id": str(uuid.uuid4()), "Ders": c_n, "Gün": c_d, "Limit": c_l, "Yapılan": 0})
                        veritabanini_kaydet(st.session_state.db); st.rerun()
        with c_top2:
            if st.button("🗑️ TÜMÜNÜ SİL", key="clear_all_att"):
                u_info['attendance'] = []
                veritabanini_kaydet(st.session_state.db); st.rerun()
        
        st.divider()
        gunler_a = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
        cols_a = st.columns(5)
        for i, g in enumerate(gunler_a):
            with cols_a[i]:
                st.markdown(f"<div style='background:#FF4B4B; color:white; text-align:center; border-radius:5px; font-weight:bold; padding:5px;'>{g[:3].upper()}</div>", unsafe_allow_html=True)
                for course in list(u_info['attendance']):
                    if course.get('Gün') == g:
                        with st.container(border=True):
                            st.write(f"**{course['Ders']}**")
                            c_id = course.get('id', str(uuid.uuid4()))
                            curr = st.number_input(f"Kaçırılan", value=course['Yapılan'], key=f"at_in_{c_id}", min_value=0)
                            if curr != course['Yapılan']:
                                for idx, c_item in enumerate(u_info['attendance']):
                                    if c_item.get('id') == c_id: 
                                        u_info['attendance'][idx]['Yapılan'] = curr
                                veritabanini_kaydet(st.session_state.db); st.rerun()
                            kalan = course['Limit'] - curr
                            if kalan <= 1: st.error(f"Kalan: {kalan}")
                            else: st.success(f"Kalan: {kalan}")
                            if st.button("🗑️ Sil", key=f"btn_del_{c_id}"):
                                u_info['attendance'] = [c for c in u_info['attendance'] if c.get('id') != c_id]
                                veritabanini_kaydet(st.session_state.db); st.rerun()
    with t2:
        st.subheader("📊 Genel Ortalama Tahmini")
        col_gano1, col_gano2 = st.columns(2)
        m_gano = col_gano1.number_input("Mevcut GNO (Eski Dönemler)", 0.0, 4.0, value=float(u_info.get('mevcut_gano', 0.0)), step=0.01)
        m_kredi = col_gano2.number_input("Tamamlanan Toplam Kredi", 0, 240, value=int(u_info.get('tamamlanan_kredi', 0)))
        
        if m_gano != u_info['mevcut_gano'] or m_kredi != u_info['tamamlanan_kredi']:
            u_info['mevcut_gano'] = m_gano
            u_info['tamamlanan_kredi'] = m_kredi
            veritabanini_kaydet(st.session_state.db)

        st.divider()
        st.write("➕ **Yeni Dönem Derslerini Ekle**")
        with st.form("gpa_f"):
            g1, g2, g3 = st.columns([3, 1, 1])
            gn = g1.text_input("Ders"); gc = g2.number_input("Kredi", 1, 10, 3)
            gr = g3.selectbox("Not", ["AA", "BA", "BB", "CB", "CC", "DC", "DD", "FD", "FF"])
            if st.form_submit_button("Ekle"):
                u_info['gpa_list'].append({"ders": gn, "kredi": gc, "not": gr})
                veritabanini_kaydet(st.session_state.db); st.rerun()
        
        if u_info['gpa_list']:
            st.table(pd.DataFrame(u_info['gpa_list']))
            nk = {"AA": 4.0, "BA": 3.5, "BB": 3.0, "CB": 2.5, "CC": 2.0, "DC": 1.5, "DD": 1.0, "FD": 0.5, "FF": 0.0}
            
            eski_toplam_puan = m_gano * m_kredi
            yeni_toplam_puan = sum([nk[r['not']] * r['kredi'] for r in u_info['gpa_list']])
            yeni_toplam_kredi = sum([r['kredi'] for r in u_info['gpa_list']])
            
            genel_kredi = m_kredi + yeni_toplam_kredi
            if genel_kredi > 0:
                genel_gano = (eski_toplam_puan + yeni_toplam_puan) / genel_kredi
                st.metric("Tahmini Yeni Genel GNO", f"{genel_gano:.2f}")
                st.caption(f"Toplam Kredi: {genel_kredi} | Dönem Ortalaması: {(yeni_toplam_puan/yeni_toplam_kredi if yeni_toplam_kredi > 0 else 0):.2f}")
            
            if st.button("Ders Listesini Temizle", key="clear_gpa"): u_info['gpa_list'] = []; veritabanini_kaydet(st.session_state.db); st.rerun()

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
                u_info['chat_history'].append({"role": "assistant", "text": res}); veritabanini_kaydet(st.session_state.db); st.rerun()
            except: st.error("Hata!")

elif menu in ["🏆 Başarılar", "🏆 Achievements"]:
    st.title(L["basliklar"]["basari"])
    k1, k2, k3 = st.columns(3)
    k1.metric("RÜTBE", mevcut_lakap_getir(u_info['level'], u_info.get('dil', 'TR')))
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
        nl = st.selectbox("Dil / Language", ["TR", "EN"], index=0 if u_info.get('dil') == 'TR' else 1)
        ns = st.text_input(L["labels"]["sifre"], value=u_info['password'], type="password")
        nm = st.text_input(L["labels"]["hedef"], value=u_info.get('ana_hedef', 'Mühendis'))
        if st.form_submit_button(L["butonlar"]["ekle"]):
            u_info['dil'] = nl
            u_info['password'] = ns
            u_info['ana_hedef'] = nm
            veritabanini_kaydet(st.session_state.db)
            st.success("Kaydedildi / Saved!")
            st.rerun()

if st.session_state.pomo_calisiyor:
    time.sleep(1); st.rerun()
