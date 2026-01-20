import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import json
import os
import google.generativeai as genai
import time
import uuid

# --- 0. KONFİGÜRASYON ---
st.set_page_config(page_title="ROTA AI", page_icon="🚀", layout="wide")

DB_FILE = "rota_database.json"
CONFIG_FILE = "user_config.json"

# --- 1. VERİ FONKSİYONLARI ---
def veritabanini_yukle():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for u in data:
                    # Tüm öğrenciler için genel varsayılanlar
                    defaults = {
                        'xp': 0, 'level': 1, 'hedef': 'Başarı', 'egitim_duzeyi': 'Üniversite',
                        'tema_rengi': '#4FACFE', 'pomo_count': 0, 'sinavlar': [], 
                        'habits': [], 'data': []
                    }
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
            'password': db[u]['password'], 'hedef': db[u].get('hedef', 'Başarı'),
            'egitim_duzeyi': db[u].get('egitim_duzeyi', 'Üniversite'),
            'tema_rengi': db[u].get('tema_rengi', '#4FACFE'),
            'xp': db[u].get('xp', 0), 'level': db[u].get('level', 1),
            'pomo_count': db[u].get('pomo_count', 0), 'sinavlar': db[u].get('sinavlar', []), 
            'habits': db[u].get('habits', []), 'data': db[u]['data'].to_dict(orient='records')
        }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=4)

# Session State Hazırlığı
if 'db' not in st.session_state: st.session_state.db = veritabanini_yukle()
if 'pomo_kalan' not in st.session_state: st.session_state.pomo_kalan = 25 * 60
if 'pomo_aktif' not in st.session_state: st.session_state.pomo_aktif = False
if 'son_tik' not in st.session_state: st.session_state.son_tik = time.time()

# --- 2. GİRİŞ & BENİ HATIRLA ---
if 'user' not in st.session_state:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            st.session_state.user = json.load(f).get('user')
    else: st.session_state.user = None

if st.session_state.user is None:
    st.markdown("<h1 style='text-align: center;'>🚀 ROTA AI</h1>", unsafe_allow_html=True)
    tab_l, tab_r = st.tabs(["🔐 GİRİŞ", "📝 KAYIT"])
    
    with tab_l:
        u = st.text_input("Kullanıcı Adı")
        p = st.text_input("Şifre", type="password")
        remember = st.checkbox("Beni Hatırla")
        if st.button("Sisteme Gir"):
            if u in st.session_state.db and st.session_state.db[u]['password'] == p:
                st.session_state.user = u
                if remember:
                    with open(CONFIG_FILE, "w") as f: json.dump({'user': u}, f)
                st.rerun()
            else: st.error("Kullanıcı adı veya şifre hatalı!")
            
    with tab_r:
        nu = st.text_input("Yeni Kullanıcı Adı")
        np = st.text_input("Şifre Belirle", type="password")
        ne = st.selectbox("Eğitim Düzeyi", ["Ortaokul", "Lise", "Üniversite", "Yüksek Lisans", "Sınav Grubu"])
        nh = st.text_input("Ana Hedefin Nedir? (Örn: Tıp, Mühendislik, İyi bir lise...)")
        if st.button("Hesabımı Oluştur"):
            if nu and np and nu not in st.session_state.db:
                st.session_state.db[nu] = {
                    'password': np, 'hedef': nh, 'egitim_duzeyi': ne,
                    'data': pd.DataFrame(columns=['Gün', 'Görev', 'Hedef', 'Birim', 'Yapılan'])
                }
                veritabanini_kaydet(st.session_state.db); st.success("Kayıt başarılı! Giriş yapabilirsiniz.")
    st.stop()

# Aktif Kullanıcı Verileri
u = st.session_state.user
u_data = st.session_state.db[u]
TEMA = u_data.get('tema_rengi', '#4FACFE')

# --- 3. DİNAMİK TEMA ---
st.markdown(f"""
<style>
    h1, h2, h3, .stSubheader {{ color: {TEMA} !important; }}
    .stButton>button {{ background-color: {TEMA} !important; color: white !important; border-radius: 8px; }}
    .stProgress > div > div > div > div {{ background-color: {TEMA} !important; }}
</style>
""", unsafe_allow_html=True)

# --- 4. SIDEBAR ---
st.sidebar.title("🚀 ROTA AI")
st.sidebar.markdown(f"**Hoş geldin, {u}!**")
st.sidebar.caption(f"{u_data['egitim_duzeyi']} | {u_data['hedef']}")
st.sidebar.divider()

menu = st.sidebar.radio("MENÜ", ["🏠 Panel", "📊 Alışkanlıklar", "📅 Sınavlar", "⏱️ Odaklanma", "🏆 Başarılar", "⚙️ Ayarlar"])

if st.sidebar.button("🚪 Çıkış Yap"):
    if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)
    st.session_state.user = None; st.rerun()

# --- 5. SAYFALAR ---

# --- PANEL ---
if menu == "🏠 Panel":
    st.title(f"✨ {u_data['hedef'].upper()} YOLCULUĞU")
    
    # Grafik Bölümü
    if not u_data['data'].empty:
        c1, c2 = st.columns([2, 1])
        with c1:
            fig = go.Figure([go.Bar(x=u_data['data']['Görev'], y=u_data['data']['Hedef'], name='Hedef', marker_color='#E9ECEF'),
                             go.Bar(x=u_data['data']['Görev'], y=u_data['data']['Yapılan'], name='Yapılan', marker_color=TEMA)])
            fig.update_layout(height=300, barmode='group', title="Hedef vs Yapılan"); st.plotly_chart(fig, use_container_width=True)
        with c2:
            done = u_data['data']['Yapılan'].sum()
            total = u_data['data']['Hedef'].sum()
            fig_pie = go.Figure(go.Pie(labels=['Biten', 'Kalan'], values=[done, max(0, total-done)], hole=.6, marker_colors=[TEMA, '#FF4B4B']))
            fig_pie.update_layout(height=300, showlegend=False, title="Genel İlerleme"); st.plotly_chart(fig_pie, use_container_width=True)

    # Haftalık Önizleme
    st.subheader("🗓️ Haftalık Planın")
    gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    cols = st.columns(7)
    for i, g in enumerate(gunler):
        with cols[i]:
            st.markdown(f"<div style='background:{TEMA}; color:white; text-align:center; border-radius:5px; font-weight:bold;'>{g[:3].upper()}</div>", unsafe_allow_html=True)
            temp = u_data['data'][u_data['data']['Gün'] == g]
            for _, r in temp.iterrows(): st.caption(f"• {r['Görev']}")

    # Görev Ekleme ve Günlük Takip
    st.divider()
    st.subheader("📝 Günlük Takip ve Yeni Hedef")
    secili_gun = st.selectbox("Gün Seç", gunler)
    
    with st.form("yeni_gorev"):
        f1, f2, f3 = st.columns([3, 1, 1])
        g_ad = f1.text_input("Ne yapacaksın?")
        g_hedef = f2.number_input("Hedef Miktar", 1)
        g_birim = f3.selectbox("Birim", ["Soru", "Sayfa", "Dakika", "Konu"])
        if st.form_submit_button("Listeye Ekle"):
            yeni = pd.DataFrame([{'Gün': secili_gun, 'Görev': g_ad, 'Hedef': g_hedef, 'Birim': g_birim, 'Yapılan': 0}])
            u_data['data'] = pd.concat([u_data['data'], yeni], ignore_index=True)
            veritabanini_kaydet(st.session_state.db); st.rerun()

    temp_gun = u_data['data'][u_data['data']['Gün'] == secili_gun]
    for idx, row in temp_gun.iterrows():
        cc1, cc2, cc3 = st.columns([3, 2, 1])
        cc1.write(f"**{row['Görev']}** ({row['Hedef']} {row['Birim']})")
        val = cc2.number_input("Yapılan", value=int(row['Yapılan']), key=f"upd_{idx}")
        if val != row['Yapılan']:
            u_data['data'].at[idx, 'Yapılan'] = val
            u_data['xp'] += 10
            if u_data['xp'] >= u_data['level'] * 200: u_data['level'] += 1; st.balloons()
            veritabanini_kaydet(st.session_state.db); st.rerun()
        if cc3.button("🗑️", key=f"del_{idx}"):
            u_data['data'] = u_data['data'].drop(idx); veritabanini_kaydet(st.session_state.db); st.rerun()

# --- ALIŞKANLIKLAR ---
elif menu == "📊 Alışkanlıklar":
    st.title("📊 Alışkanlık Takip Sistemi")
    with st.form("h_ekle"):
        h_ad = st.text_input("Yeni Alışkanlık (Örn: Erken Kalkış, Kitap Okuma)")
        if st.form_submit_button("Ekle"):
            u_data['habits'].append({"Ad": h_ad, "Pzt": False, "Sal": False, "Çar": False, "Per": False, "Cum": False, "Cmt": False, "Paz": False})
            veritabanini_kaydet(st.session_state.db); st.rerun()
    
    if u_data['habits']:
        h_df = pd.DataFrame(u_data['habits'])
        updated_h = st.data_editor(h_df, use_container_width=True, hide_index=True)
        if not h_df.equals(updated_h):
            u_data['habits'] = updated_h.to_dict(orient='records')
            veritabanini_kaydet(st.session_state.db); st.rerun()

# --- SINAVLAR ---
elif menu == "📅 Sınavlar":
    st.title("📅 Sınav Takvimi")
    with st.form("s_ekle"):
        c1, c2 = st.columns(2)
        s_ders = c1.text_input("Ders Adı")
        s_tarih = c2.date_input("Sınav Tarihi")
        if st.form_submit_button("Sınavı Kaydet"):
            u_data['sinavlar'].append({"Ders": s_ders, "Tarih": str(s_tarih)})
            veritabanini_kaydet(st.session_state.db); st.rerun()
    
    for i, s in enumerate(u_data['sinavlar']):
        col1, col2 = st.columns([5, 1])
        col1.info(f"📖 **{s['Ders']}** - 📅 {s['Tarih']}")
        if col2.button("🗑️", key=f"sdel_{i}"):
            u_data['sinavlar'].pop(i); veritabanini_kaydet(st.session_state.db); st.rerun()

# --- ODAKLANMA ---
elif menu == "⏱️ Odaklanma":
    st.title("⏱️ Odaklanma (Pomodoro)")
    sure = st.select_slider("Süre Seç (Dakika)", options=[15, 25, 45, 60], value=25)
    
    c1, c2, c3 = st.columns(3)
    if c1.button("▶️ Başlat"): st.session_state.pomo_kalan = sure * 60; st.session_state.pomo_aktif = True
    if c2.button("⏸️ Durdur"): st.session_state.pomo_aktif = False
    if c3.button("🔄 Sıfırla"): st.session_state.pomo_kalan = 25 * 60; st.session_state.pomo_aktif = False
    
    m, s = divmod(st.session_state.pomo_kalan, 60)
    st.markdown(f"<h1 style='text-align:center; font-size:100px; color:{TEMA};'>{m:02d}:{s:02d}</h1>", unsafe_allow_html=True)
    
    if st.session_state.pomo_aktif and st.session_state.pomo_kalan > 0:
        time.sleep(1)
        st.session_state.pomo_kalan -= 1
        if st.session_state.pomo_kalan == 0:
            u_data['xp'] += 50; u_data['pomo_count'] += 1
            veritabanini_kaydet(st.session_state.db); st.balloons()
        st.rerun()

# --- BAŞARILAR ---
elif menu == "🏆 Başarılar":
    st.title("🏆 Başarılar ve İstatistik")
    col1, col2, col3 = st.columns(3)
    col1.metric("Mevcut Seviye", u_data['level'])
    col2.metric("Toplam XP", u_data['xp'])
    col3.metric("Tamamlanan Odaklanma", u_data['pomo_count'])
    
    st.subheader("Gelişim Barı")
    progress = (u_data['xp'] % 200) / 200
    st.progress(progress)
    st.caption(f"Bir sonraki seviye için {(u_data['level'] * 200) - u_data['xp']} XP kaldı.")

# --- AYARLAR ---
elif menu == "⚙️ Ayarlar":
    st.title("⚙️ Ayarlar ve Kişiselleştirme")
    u_data['tema_rengi'] = st.color_picker("Uygulama Tema Rengini Değiştir", TEMA)
    u_data['hedef'] = st.text_input("Hedefini Güncelle", u_data['hedef'])
    u_data['password'] = st.text_input("Şifreni Değiştir", u_data['password'], type="password")
    if st.button("Tüm Ayarları Kaydet"):
        veritabanini_kaydet(st.session_state.db); st.success("Ayarlar mühürlendi!")
