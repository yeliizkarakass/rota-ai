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
        "menu": ["🏠 Panel", "📅 Sınavlar", "⏱️ Odak", "🎓 Akademik", "🏆 Başarılar", "🤖 AI Mentor", "⚙️ Ayarlar"],
        "butonlar": {"baslat": "🚀 BAŞLAT", "durdur": "⏸️ DURDUR", "sifirla": "🔄 SIFIRLA", "ekle": "Ekle", "kaydet": "Kaydet", "cikis": "🚪 ÇIKIŞ"},
        "basliklar": {"takip": "📝 GÜNLÜK TAKİP", "onizleme": "🗓️ Haftalık Önizleme", "sinavlar": "📅 SINAV TAKVİMİ", "pomo": "⏱️ ODAK", "akademik": "🎓 AKADEMİK YÖNETİM", "aliskanlik": "📊 ALIŞKANLIK TAKİPÇİSİ", "basari": "🏆 BAŞARI KÜRSÜSÜ"},
        "labels": {"hedef": "Hedef", "yapilan": "Yapılan", "birim": "Birim", "gorev": "Görev", "rutbe": "Rütbe", "tema": "Hızlı Tema"}
    },
    "EN": {
        "menu": ["🏠 Dashboard", "📅 Exams", "⏱️ Focus", "🎓 Academic", "🏆 Achievements", "🤖 AI Mentor", "⚙️ Settings"],
        "butonlar": {"baslat": "🚀 START", "durdur": "⏸️ PAUSE", "sifirla": "🔄 RESET", "ekle": "Add", "kaydet": "Save", "cikis": "🚪 LOGOUT"},
        "basliklar": {"takip": "📝 DAILY TRACKING", "onizleme": "🗓️ Weekly Preview", "sinavlar": "📅 EXAM SCHEDULE", "pomo": "⏱️ FOCUS", "akademik": "🎓 ACADEMIC MANAGEMENT", "aliskanlik": "📊 HABIT TRACKER", "basari": "🏆 HALL OF FAME"},
        "labels": {"hedef": "Target", "yapilan": "Done", "birim": "Unit", "gorev": "Task", "rutbe": "Rank", "tema": "Quick Theme"}
    }
}

def veritabanini_yukle():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for u in data:
                    defaults = {'xp': 0, 'level': 1, 'ana_hedef': 'Öğrenci', 'sinavlar': [], 'notes': [], 'pomo_count': 0, 'dil': 'TR', 'habits': [], 'attendance': [], 'gpa_list': [], 'tema_rengi': '#4FACFE', 'egitim_duzeyi': 'Lisans', 'mevcut_gno': 0.0, 'toplam_kredi': 0}
                    for k, v in defaults.items():
                        if k not in data[u]: data[u][k] = v
                    data[u]['data'] = pd.DataFrame(data[u]['data'])
                return data
        except: return {}
    return {}

def veritabanini_kaydet(db):
    to_save = {}
    for u in db:
        current_xp = db[u].get('xp', 0)
        db[u]['level'] = (current_xp // 500) + 1
        user_copy = db[u].copy()
        if isinstance(user_copy['data'], pd.DataFrame):
            user_copy['data'] = user_copy['data'].to_dict(orient='records')
        to_save[u] = user_copy
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=4)

if 'db' not in st.session_state: st.session_state.db = veritabanini_yukle()
if 'pomo_kalan_saniye' not in st.session_state: st.session_state.pomo_kalan_saniye = 25 * 60
if 'pomo_calisiyor' not in st.session_state: st.session_state.pomo_calisiyor = False
if 'son_guncelleme' not in st.session_state: st.session_state.son_guncelleme = time.time()

if 'aktif_kullanici' not in st.session_state: st.session_state.aktif_kullanici = None

# --- GİRİŞ & KAYIT ---
if st.session_state.aktif_kullanici is None:
    st.title("🚀 ROTA AI")
    t1, t2 = st.tabs(["🔑 GİRİŞ", "📝 KAYIT"])
    with t1:
        u = st.text_input("Kullanıcı")
        p = st.text_input("Şifre", type="password")
        if st.button("GİRİŞ YAP"):
            if u in st.session_state.db and st.session_state.db[u]['password'] == p:
                st.session_state.aktif_kullanici = u
                st.rerun()
            else: st.error("Hatalı Giriş!")
    with t2:
        nu = st.text_input("Yeni Kullanıcı Adı")
        np = st.text_input("Şifre Belirle", type="password")
        if st.button("HESAP OLUŞTUR"):
            if nu and np and nu not in st.session_state.db:
                st.session_state.db[nu] = {'password': np, 'xp': 0, 'level': 1, 'ana_hedef': 'Öğrenci', 'data': pd.DataFrame(columns=['Gün', 'Görev', 'Hedef', 'Birim', 'Yapılan']), 'dil': 'TR', 'tema_rengi': '#4FACFE', 'habits': [], 'notes': [], 'mevcut_gno': 0.0, 'toplam_kredi': 0, 'pomo_count': 0}
                veritabanini_kaydet(st.session_state.db)
                st.success("Kayıt Başarılı!")
    st.stop()

u_id = st.session_state.aktif_kullanici
u_info = st.session_state.db[u_id]
L = DIL_PAKETI.get(u_info.get('dil', 'TR'), DIL_PAKETI["TR"])
TEMA = u_info.get('tema_rengi', '#4FACFE')

# Dinamik Tema Uygulama
st.markdown(f"""
    <style>
    .stButton>button {{ background-color: {TEMA}; color: white; border-radius:8px; font-weight: bold; }}
    h1, h2, h3 {{ color: {TEMA}; }}
    .stProgress > div > div > div > div {{ background-color: {TEMA}; }}
    [data-testid="stExpander"] {{ border: 1px solid {TEMA}; }}
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.title("🚀 ROTA AI")

# Sidebar Renk Seçici (İstediğin Özellik)
new_side_color = st.sidebar.color_picker(L["labels"]["tema"], TEMA)
if new_side_color != TEMA:
    u_info['tema_rengi'] = new_side_color
    veritabanini_kaydet(st.session_state.db)
    st.rerun()

lvl = u_info['level']
dil = u_info.get('dil', 'TR')
rütbe = LAKAPLAR[1][dil]
for k in sorted(LAKAPLAR.keys()):
    if lvl >= k: rütbe = LAKAPLAR[k][dil]

st.sidebar.metric(L["labels"]["rutbe"], rütbe)
st.sidebar.progress(min((u_info['xp'] % 500) / 500, 1.0), text=f"XP: {u_info['xp']}")
menu = st.sidebar.radio("NAVİGASYON", L["menu"])

st.sidebar.subheader("📌 Hızlı Notlar")
n_df = pd.DataFrame(u_info.get('notes', []), columns=["Kategori", "Not"])
if n_df.empty: n_df = pd.DataFrame([{"Kategori": "🔵 Genel", "Not": "Not..."}])
edited_notes = st.sidebar.data_editor(n_df, num_rows="dynamic", use_container_width=True, hide_index=True)
if not n_df.equals(edited_notes):
    u_info['notes'] = edited_notes.to_dict(orient='records'); veritabanini_kaydet(st.session_state.db)

if st.sidebar.button(L["butonlar"]["cikis"]):
    st.session_state.aktif_kullanici = None; st.rerun()

# --- PANEL ---
if menu in ["🏠 Panel", "🏠 Dashboard"]:
    st.title(f"✨ {u_info.get('ana_hedef', 'Öğrenci').upper()}")
    if not u_info['data'].empty:
        c1, c2 = st.columns([2, 1])
        with c1:
            fig = go.Figure([go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Hedef'], name="Hedef", marker_color='#E9ECEF'),
                             go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Yapılan'], name="Yapılan", marker_color=TEMA)])
            fig.update_layout(height=300, barmode='group'); st.plotly_chart(fig, use_container_width=True)
        with c2:
            done = u_info['data']['Yapılan'].astype(float).sum()
            todo = u_info['data']['Hedef'].astype(float).sum()
            st.plotly_chart(go.Figure(go.Pie(labels=['Biten', 'Kalan'], values=[done, max(0.1, todo-done)], hole=.6, marker_colors=[TEMA, '#FF4B4B'])).update_layout(height=300, showlegend=False), use_container_width=True)

    st.subheader(L["basliklar"]["takip"])
    gunler = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
    for g in gunler:
        with st.expander(f"📅 {g.upper()}"):
            mask = u_info['data']['Gün'] == g
            temp_df = u_info['data'][mask]
            for idx, row in temp_df.iterrows():
                cc1, cc2, cc3 = st.columns([3, 2, 1])
                cc1.write(f"**{row['Görev']}**")
                y_v = cc2.number_input(f"{row['Birim']}", value=int(row['Yapılan']), key=f"p_{idx}")
                if y_v != row['Yapılan']:
                    u_info['data'].at[idx, 'Yapılan'] = y_v
                    u_info['xp'] += 20; veritabanini_kaydet(st.session_state.db); st.rerun()
                if cc3.button("🗑️", key=f"del_g_{idx}"):
                    u_info['data'] = u_info['data'].drop(idx).reset_index(drop=True)
                    veritabanini_kaydet(st.session_state.db); st.rerun()
            with st.form(f"f_{g}", clear_on_submit=True):
                c_a, c_b, c_c = st.columns([2, 1, 1])
                ng, nh, nb = c_a.text_input("Görev"), c_b.number_input("Hedef", 1), c_c.selectbox("Birim", ["Soru", "Saat", "Sayfa"])
                if st.form_submit_button("Ekle"):
                    u_info['data'] = pd.concat([u_info['data'], pd.DataFrame([{'Gün': g, 'Görev': ng, 'Hedef': nh, 'Birim': nb, 'Yapılan': 0}])], ignore_index=True)
                    veritabanini_kaydet(st.session_state.db); st.rerun()

    st.divider(); st.subheader(L["basliklar"]["aliskanlik"])
    h_df = pd.DataFrame(u_info.get('habits', []), columns=["Alışkanlık", "Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"])
    if h_df.empty: h_df = pd.DataFrame([{"Alışkanlık": "Kitap Okuma 📖", "Pzt": False, "Sal": False, "Çar": False, "Per": False, "Cum": False, "Cmt": False, "Paz": False}])
    edited_h = st.data_editor(h_df, num_rows="dynamic", use_container_width=True, hide_index=True)
    if not h_df.equals(edited_h):
        u_info['habits'] = edited_h.to_dict(orient='records'); veritabanini_kaydet(st.session_state.db)
    for _, row in edited_h.iterrows():
        tik = sum([1 for gun in ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"] if row.get(gun, False) is True])
        c_h1, c_h2 = st.columns([1, 3])
        c_h1.caption(f"**{row['Alışkanlık']}**")
        c_h2.progress(tik / 7)

# --- BAŞARILAR ---
elif menu in ["🏆 Başarılar", "🏆 Achievements"]:
    st.title(L["basliklar"]["basari"])
    c1, c2, c3 = st.columns(3)
    c1.metric("Toplam XP", u_info['xp'])
    c2.metric("Mevcut Seviye", u_info['level'])
    c3.metric("Pomodoro", u_info.get('pomo_count', 0))
    st.progress(min((u_info['xp'] % 500) / 500, 1.0), text=f"Sıradaki Seviye İçin {500 - (u_info['xp'] % 500)} XP")
    
    st.divider()
    bc1, bc2, bc3, bc4 = st.columns(4)
    badges = [
        {"name": "Yeni Başlayan", "req": u_info['xp'] >= 100, "icon": "🌱"},
        {"name": "Odak Ustası", "req": u_info.get('pomo_count', 0) >= 10, "icon": "🔥"},
        {"name": "Kararlı", "req": len(u_info.get('habits', [])) >= 3, "icon": "🛡️"},
        {"name": "Zirve Mimarı", "req": u_info['level'] >= 5, "icon": "🏔️"}
    ]
    for i, b in enumerate(badges):
        with [bc1, bc2, bc3, bc4][i]:
            if b["req"]: st.success(f"{b['icon']} {b['name']}")
            else: st.info(f"🔒 {b['name']}")

# --- ODAK ---
elif menu in ["⏱️ Odak", "⏱️ Focus"]:
    st.title(L["basliklar"]["pomo"])
    
    # Süreyi 180 dakikaya kadar seçeneklerle genişlettik
    dk_secenekleri = [15, 25, 45, 60, 90, 120, 150, 180]
    dk = st.select_slider("Dakika Seçin", options=dk_secenekleri, value=25)
    
    c1, c2, c3 = st.columns(3)
    
    # Başlat butonu: Kalan saniyeyi set eder ve çalışıyor durumuna getirir
    if c1.button(L["butonlar"]["baslat"]):
        st.session_state.pomo_kalan_saniye = dk * 60
        st.session_state.pomo_calisiyor = True
        st.session_state.son_guncelleme = time.time()
        st.rerun()

    # Durdur butonu
    if c2.button(L["butonlar"]["durdur"]):
        st.session_state.pomo_calisiyor = False
        st.rerun()

    # Sıfırla butonu
    if c3.button(L["butonlar"]["sifirla"]):
        st.session_state.pomo_calisiyor = False
        st.session_state.pomo_kalan_saniye = 25 * 60
        st.rerun()
    
    # Sayaç Mantığı
    if st.session_state.pomo_calisiyor:
        su_an = time.time()
        gecen_sure = su_an - st.session_state.son_guncelleme
        st.session_state.pomo_kalan_saniye -= gecen_sure
        st.session_state.son_guncelleme = su_an
        
        if st.session_state.pomo_kalan_saniye <= 0:
            st.session_state.pomo_calisiyor = False
            st.session_state.pomo_kalan_saniye = 0
            # Puan ve sayaç güncelleme
            u_info['xp'] += 100
            u_info['pomo_count'] = u_info.get('pomo_count', 0) + 1
            veritabanini_kaydet(st.session_state.db)
            st.balloons()
            st.rerun()
        
        # Her saniye ekranın yenilenmesi için (DİKKAT: rerun en sonda olmalı)
        time.sleep(0.1) # Daha akıcı bir görüntü için bekleme süresini düşürdük
        st.rerun()
    
    # Görsel Sayaç
    m, s = divmod(max(0, int(st.session_state.pomo_kalan_saniye)), 60)
    st.markdown(f"""
        <div style="display: flex; justify-content: center; align-items: center; background-color: #f0f2f6; border-radius: 20px; padding: 20px; margin: 20px 0;">
            <h1 style="font-size: 150px; color: {TEMA}; font-family: 'Courier New', Courier, monospace; margin: 0;">
                {m:02d}:{s:02d}
            </h1>
        </div>
    """, unsafe_allow_html=True)


# --- SINAVLAR ---
elif menu in ["📅 Sınavlar", "📅 Exams"]:
    st.title(L["basliklar"]["sinavlar"])
    
    # HATA ÖNLEYİCİ: Eğer 'sinavlar' anahtarı yoksa boş liste oluştur
    if 'sinavlar' not in u_info:
        u_info['sinavlar'] = []

    with st.form("ex_f", clear_on_submit=True):
        c1, c2 = st.columns(2)
        d_ad = c1.text_input("Ders Adı")
        d_tr = c2.date_input("Sınav Tarihi")
        if st.form_submit_button("Sınav Ekle"):
            if d_ad: # Boş ders eklenmesini engelle
                u_info['sinavlar'].append({"id": str(uuid.uuid4()), "ders": d_ad, "tarih": str(d_tr)})
                veritabanini_kaydet(st.session_state.db)
                st.rerun()
            else:
                st.warning("Lütfen bir ders adı girin.")

    # Listeleme kısmında enumerate kullanırken listeyi kontrol et
    for i, ex in enumerate(u_info['sinavlar']):
        with st.container(border=True):
            sc1, sc2, sc3 = st.columns([3, 2, 1])
            sc1.write(f"📖 **{ex.get('ders', 'Bilinmeyen Ders')}**")
            sc2.info(f"📅 {ex.get('tarih', '-')}")
            if sc3.button("Sil", key=f"ex_s_{i}"):
                u_info['sinavlar'].pop(i)
                veritabanini_kaydet(st.session_state.db)
                st.rerun()


# --- AKADEMİK ---
elif menu in ["🎓 Akademik", "🎓 Academic"]:
    st.title(L["basliklar"]["akademik"])
    tab1, tab2 = st.tabs(["📊 GNO Hesapla", "📉 Devamsızlık"])
    with tab1:
        st.subheader("📌 Mevcut Akademik Veriler")
        gc1, gc2 = st.columns(2)
        m_gno = gc1.number_input("Genel Ortalama (GNO)", 0.0, 4.0, float(u_info.get('mevcut_gno', 0.0)))
        m_kr = gc2.number_input("Toplam Kredi", 0, 300, int(u_info.get('toplam_kredi', 0)))
        
        st.subheader("📚 Dönem Dersleri")
        gpa_df = pd.DataFrame(u_info.get('gpa_list', []), columns=["Ders", "Kredi", "Not"])
        edited_gpa = st.data_editor(gpa_df, num_rows="dynamic", use_container_width=True)
        
        if st.button("Kaydet ve Hesapla"):
            u_info['mevcut_gno'], u_info['toplam_kredi'] = m_gno, m_kr
            u_info['gpa_list'] = edited_gpa.to_dict(orient='records')
            dk = edited_gpa['Kredi'].sum()
            dp = (edited_gpa['Kredi'] * edited_gpa['Not']).sum()
            y_gno = ((m_gno * m_kr) + dp) / (m_kr + dk) if (m_kr + dk) > 0 else 0
            st.success(f"Dönem Ortalaması: {dp/dk if dk > 0 else 0:.2f} | Yeni GNO: {y_gno:.2f}")
            veritabanini_kaydet(st.session_state.db)

    with tab2:
        att_df = pd.DataFrame(u_info.get('attendance', []), columns=["Ders", "Limit", "Kaçırılan"])
        edited_att = st.data_editor(att_df, num_rows="dynamic", use_container_width=True)
        if st.button("Kaydet"):
            u_info['attendance'] = edited_att.to_dict(orient='records'); veritabanini_kaydet(st.session_state.db)

# --- AYARLAR ---
elif menu in ["⚙️ Ayarlar", "⚙️ Settings"]:
    st.title("⚙️ Ayarlar")
    with st.form("set_f"):
        nl = st.selectbox("Dil", ["TR", "EN"], index=0 if u_info['dil'] == "TR" else 1)
        nh = st.text_input("Hedef Meslek / Bölüm", value=u_info.get('ana_hedef', ''))
        if st.form_submit_button("Ayarları Güncelle"):
            u_info.update({'dil': nl, 'ana_hedef': nh}); veritabanini_kaydet(st.session_state.db); st.rerun()
