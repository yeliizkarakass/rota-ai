import streamlit as st
import pandas as pd
import json
import os
import time
import uuid
import plotly.graph_objects as go
import google.generativeai as genai

# PDF Kütüphanesi Kontrolü
try:
    import PyPDF2
except:
    os.system('pip install PyPDF2')
    import PyPDF2

# --- 0. AYARLAR ---
st.set_page_config(page_title="ROTA AI", page_icon="🚀", layout="wide")
DB_FILE = "rota_database.json"

# API Ayarı
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- 1. VERİ YÖNETİMİ (EN SAĞLAM HALİ) ---
def veritabanini_yukle():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for u in data:
                    # Eksik alanları tamir et
                    defaults = {
                        'xp': 0, 'level': 1, 'ana_hedef': 'Gelişim', 'dil': 'TR',
                        'sinavlar': [], 'habits': [], 'notes': [], 'attendance': [],
                        'mevcut_gano': 0.0, 'tamamlanan_kredi': 0, 'chat_history': []
                    }
                    for k, v in defaults.items():
                        if k not in data[u]: data[u][k] = v
                    # DataFrame dönüşümü
                    if not isinstance(data[u].get('data'), pd.DataFrame):
                        data[u]['data'] = pd.DataFrame(data[u].get('data', []))
                return data
        except: return {}
    return {}

def veritabanini_kaydet(db):
    to_save = {}
    for u in db:
        temp = db[u].copy()
        if isinstance(temp['data'], pd.DataFrame):
            temp['data'] = temp['data'].to_dict(orient='records')
        to_save[u] = temp
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=4)

if 'db' not in st.session_state: st.session_state.db = veritabanini_yukle()
if 'pomo_kalan' not in st.session_state: st.session_state.pomo_kalan = 25 * 60
if 'pomo_aktif' not in st.session_state: st.session_state.pomo_aktif = False

# --- 2. GİRİŞ SİSTEMİ ---
if 'user' not in st.session_state: st.session_state.user = None

if st.session_state.user is None:
    st.title("🚀 ROTA AI")
    t1, t2 = st.tabs(["GİRİŞ", "KAYIT"])
    with t1:
        u = st.text_input("Kullanıcı Adı")
        p = st.text_input("Şifre", type="password")
        if st.button("GİRİŞ"):
            if u in st.session_state.db and st.session_state.db[u]['password'] == p:
                st.session_state.user = u
                st.rerun()
            else: st.error("Hatalı giriş!")
    with t2:
        nu = st.text_input("Yeni Ad")
        np = st.text_input("Yeni Şifre", type="password")
        if st.button("KAYDOL"):
            if nu and np and nu not in st.session_state.db:
                st.session_state.db[nu] = {'password':np, 'xp':0, 'level':1, 'data':pd.DataFrame(columns=['Gün','Görev','Hedef','Yapılan'])}
                veritabanini_kaydet(st.session_state.db)
                st.success("Kayıt başarılı! Giriş yapın.")
    st.stop()

# --- 3. ANA UYGULAMA ---
u_info = st.session_state.db[st.session_state.user]
L_MENU = ["🏠 Panel", "📊 Alışkanlıklar", "📅 Sınavlar", "⏱️ Odak", "🎓 Akademik", "🤖 AI Mentor", "🏆 Başarılar", "⚙️ Ayarlar"]
menu = st.sidebar.radio("MENÜ", L_MENU)

# Sidebar Notlar
st.sidebar.subheader("📌 Hızlı Notlar")
n_df = pd.DataFrame(u_info.get('notes', []), columns=["Not"])
if n_df.empty: n_df = pd.DataFrame([{"Not": "..."}])
edited_n = st.sidebar.data_editor(n_df, num_rows="dynamic", use_container_width=True, hide_index=True)
if not n_df.equals(edited_n):
    u_info['notes'] = edited_n.to_dict(orient='records')
    veritabanini_kaydet(st.session_state.db)

if st.sidebar.button("🚪 ÇIKIŞ"):
    st.session_state.user = None
    st.rerun()

# --- SAYFA İÇERİKLERİ ---

if menu == "🏠 Panel":
    st.title(f"✨ HOŞ GELDİN {st.session_state.user.upper()}")
    
    # Grafik
    if not u_info['data'].empty:
        fig = go.Figure([go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Hedef'], name="Hedef"),
                         go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Yapılan'], name="Biten")])
        st.plotly_chart(fig, use_container_width=True)

    # Görev Ekleme
    with st.form("g_ekle"):
        c1, c2, c3 = st.columns([2,1,1])
        gun = c1.selectbox("Gün", ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"])
        gorev = c2.text_input("Görev")
        hdf = c3.number_input("Hedef", 1)
        if st.form_submit_button("Ekle"):
            yeni = pd.DataFrame([{'Gün':gun, 'Görev':gorev, 'Hedef':hdf, 'Yapılan':0}])
            u_info['data'] = pd.concat([u_info['data'], yeni], ignore_index=True)
            veritabanini_kaydet(st.session_state.db); st.rerun()

elif menu == "📊 Alışkanlıklar":
    st.title("📊 Alışkanlık Takibi")
    h_df = pd.DataFrame(u_info.get('habits', []), columns=["Alışkanlık", "Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"])
    edited_h = st.data_editor(h_df, num_rows="dynamic", use_container_width=True, hide_index=True)
    if not h_df.equals(edited_h):
        u_info['habits'] = edited_h.to_dict(orient='records')
        veritabanini_kaydet(st.session_state.db)

elif menu == "📅 Sınavlar":
    st.title("📅 Sınavlar")
    pdf = st.file_uploader("Sınav Takvimi PDF", type="pdf")
    if pdf and st.button("AI ANALİZ"):
        reader = PyPDF2.PdfReader(pdf)
        txt = "".join([p.extract_text() for p in reader.pages])
        res = genai.GenerativeModel('gemini-1.5-flash').generate_content(f"Sınavları ayıkla: {txt}").text
        st.info(res)
    
    with st.form("s_f"):
        d, t = st.text_input("Ders"), st.date_input("Tarih")
        if st.form_submit_button("Sınav Ekle"):
            u_info['sinavlar'].append({"Ders": d, "Tarih": str(t)})
            veritabanini_kaydet(st.session_state.db); st.rerun()
    for s in u_info['sinavlar']: st.write(f"📖 {s['Ders']} - 📅 {s['Tarih']}")

elif menu == "⏱️ Odak":
    st.title("⏱️ Odak")
    if st.button("25 DK BAŞLAT"):
        st.session_state.pomo_kalan = 25 * 60; st.session_state.pomo_aktif = True
    m, s = divmod(int(st.session_state.pomo_kalan), 60)
    st.header(f"{m:02d}:{s:02d}")

elif menu == "🎓 Akademik":
    st.title("🎓 Akademik")
    with st.expander("📉 Devamsızlık Ekle"):
        with st.form("at"):
            dn, dl = st.text_input("Ders"), st.number_input("Limit", 1)
            if st.form_submit_button("Kaydet"):
                u_info['attendance'].append({"Ders": dn, "Limit": dl, "Yapılan": 0})
                veritabanini_kaydet(st.session_state.db); st.rerun()
    for a in u_info['attendance']: st.write(f"{a['Ders']}: {a['Yapılan']}/{a['Limit']}")

elif menu == "🏆 Başarılar":
    st.title("🏆 Başarılar")
    st.metric("SEVİYE", u_info['level'])
    st.write(f"Toplam XP: {u_info['xp']}")
    st.progress(min((u_info['xp'] % 200) / 200, 1.0))

elif menu == "⚙️ Ayarlar":
    st.title("⚙️ Ayarlar")
    nh = st.text_input("Yeni Hedef", value=u_info['ana_hedef'])
    if st.button("KAYDET"):
        u_info['ana_hedef'] = nh
        veritabanini_kaydet(st.session_state.db); st.success("Tamam!")
