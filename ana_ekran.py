import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
import json
import os
import google.generativeai as genai
import time
import uuid
import extra_streamlit_components as stx  # Yeni kütüphane

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
        "basliklar": {"takip": "📝 GÜNLÜK TAKİP", "onizleme": "🗓️ Haftalık Önizleme", "sinavlar": "📅 SINAV TAKVİMİ", "pomo": "⏱️ ODAK", "akademik": "🎓 AKADEMİK YÖNETİM", "aliskanlik": "📊 ALIŞKANLIK TAKİPÇİSİ", "basari": "🏆 BAŞARI KÜRSÜSÜ", "mentor": "🤖 AI AKADEMİK DANIŞMAN"},
        "labels": {"hedef": "Hedef", "yapilan": "Yapılan", "birim": "Birim", "gorev": "Görev", "rutbe": "Rütbe", "tema": "Hızlı Tema"}
    },
    "EN": {
        "menu": ["🏠 Dashboard", "📅 Exams", "⏱️ Focus", "🎓 Academic", "🏆 Achievements", "🤖 AI Mentor", "⚙️ Settings"],
        "butonlar": {"baslat": "🚀 START", "durdur": "⏸️ PAUSE", "sifirla": "🔄 RESET", "ekle": "Add", "kaydet": "Save", "cikis": "🚪 LOGOUT"},
        "basliklar": {"takip": "📝 DAILY TRACKING", "onizleme": "🗓️ Weekly Preview", "sinavlar": "📅 EXAM SCHEDULE", "pomo": "⏱️ FOCUS", "akademik": "🎓 ACADEMIC MANAGEMENT", "aliskanlik": "📊 HABIT TRACKER", "basari": "🏆 HALL OF FAME", "mentor": "🤖 AI ACADEMIC ADVISOR"},
        "labels": {"hedef": "Target", "yapilan": "Done", "birim": "Unit", "gorev": "Task", "rank": "Rank", "tema": "Quick Theme"}
    }
}

def veritabanini_yukle():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for u in data:
                    defaults = {'password': '123', 'xp': 0, 'level': 1, 'ana_hedef': 'Öğrenci', 'sinavlar': [], 'notes': [], 'pomo_count': 0, 'dil': 'TR', 'habits': [], 'attendance': [], 'gpa_list': [], 'tema_rengi': '#4FACFE', 'egitim_duzeyi': 'Lisans', 'mevcut_gno': 0.0, 'toplam_kredi': 0}
                    for k, v in defaults.items():
                        if k not in data[u]: data[u][k] = v
                    if isinstance(data[u]['data'], list):
                        data[u]['data'] = pd.DataFrame(data[u]['data'])
                    elif not isinstance(data[u]['data'], pd.DataFrame):
                        data[u]['data'] = pd.DataFrame(columns=['Gün', 'Görev', 'Hedef', 'Birim', 'Yapılan'])
                return data
        except Exception: return {}
    return {}

def veritabanini_kaydet(db):
    to_save = {}
    for u in db:
        db[u]['level'] = (db[u].get('xp', 0) // 500) + 1
        temp_user = db[u].copy()
        if isinstance(temp_user['data'], pd.DataFrame):
            temp_user['data'] = temp_user['data'].to_dict(orient='records')
        to_save[u] = temp_user
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=4)

if 'db' not in st.session_state: st.session_state.db = veritabanini_yukle()
if 'pomo_kalan_saniye' not in st.session_state: st.session_state.pomo_kalan_saniye = 25 * 60
if 'pomo_calisiyor' not in st.session_state: st.session_state.pomo_calisiyor = False
if 'son_guncelleme' not in st.session_state: st.session_state.son_guncelleme = time.time()
if 'aktif_kullanici' not in st.session_state: st.session_state.aktif_kullanici = None

# --- COOKIE YÖNETİMİ ---
cookie_manager = stx.CookieManager()

# --- GİRİŞ & KAYIT ---
if st.session_state.aktif_kullanici is None:
    # Önce Cookie'den kullanıcıyı kontrol et
    saved_user = cookie_manager.get(cookie="remember_rota_ai")
    
    if saved_user and saved_user in st.session_state.db:
        st.session_state.aktif_kullanici = saved_user
        st.rerun()

    st.title("🚀 ROTA AI")
    t1, t2 = st.tabs(["🔑 GİRİŞ", "📝 KAYIT"])
    
    with t1:
        u = st.text_input("Kullanıcı Adı")
        p = st.text_input("Şifre", type="password")
        remember_me = st.checkbox("Beni Hatırla") 
        
        if st.button("GİRİŞ YAP"):
            if u in st.session_state.db and st.session_state.db[u]['password'] == p:
                st.session_state.aktif_kullanici = u
                if remember_me:
                    # Cookie'yi 30 gün boyunca hatırla
                    cookie_manager.set("remember_rota_ai", u, expires_at=datetime.now() + timedelta(days=30))
                st.rerun()
            else: 
                st.error("Kullanıcı adı veya şifre hatalı!")
                
    with t2:
        nu = st.text_input("Yeni Kullanıcı Adı")
        np = st.text_input("Şifre Belirle", type="password")
        c1, c2 = st.columns(2)
        edu_level = c1.selectbox("Eğitim Seviyesi", ["Lise", "Önlisans", "Lisans", "Yüksek Lisans / Doktora"])
        job_goal = c2.text_input("Meslek Hedefi (Örn: Elektrik Mühendisi)")
        
        if st.button("HESAP OLUŞTUR"):
            if nu and np:
                if nu not in st.session_state.db:
                    st.session_state.db[nu] = {
                        'password': np, 'xp': 0, 'level': 1, 
                        'ana_hedef': job_goal if job_goal else "Öğrenci", 
                        'egitim_duzeyi': edu_level,
                        'data': pd.DataFrame(columns=['Gün', 'Görev', 'Hedef', 'Birim', 'Yapılan']), 
                        'dil': 'TR', 'tema_rengi': '#4FACFE', 'habits': [], 'notes': [], 
                        'mevcut_gno': 0.0, 'toplam_kredi': 0, 'pomo_count': 0, 'sinavlar': []
                    }
                    veritabanini_kaydet(st.session_state.db)
                    st.success("Hesap oluşturuldu! Giriş yapabilirsiniz.")
                else: st.warning("Bu kullanıcı adı alınmış.")
    st.stop()

# --- ANA UYGULAMA DEĞİŞKENLERİ ---
u_id = st.session_state.aktif_kullanici
u_info = st.session_state.db[u_id]
L = DIL_PAKETI.get(u_info.get('dil', 'TR'), DIL_PAKETI["TR"])
TEMA = u_info.get('tema_rengi', '#4FACFE')

# --- TASARIM (CSS) ---
st.markdown(f"<style>.stButton>button {{ background-color: {TEMA}; color: white; border-radius:8px; font-weight: bold; }} h1, h2, h3 {{ color: {TEMA}; }} .stProgress > div > div > div > div {{ background-color: {TEMA}; }} [data-testid='stExpander'] {{ border: 1px solid {TEMA}; }} </style>", unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.title("🚀 ROTA AI")
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

# --- ÇIKIŞ BUTONU (GÜNCELLENDİ) ---
if st.sidebar.button(L["butonlar"]["cikis"]):
    cookie_manager.delete("remember_rota_ai")
    st.session_state.aktif_kullanici = None
    st.rerun()

# --- PANEL ---
if menu in ["🏠 Panel", "🏠 Dashboard"]:
    st.title(f"✨ {u_info.get('ana_hedef', 'Öğrenci').upper()}")
    
    # Veritabanı Kontrolü ve Sütun Sabitleme
    if not isinstance(u_info['data'], pd.DataFrame) or u_info['data'].empty:
        u_info['data'] = pd.DataFrame(columns=['Gün', 'Görev', 'Hedef', 'Birim', 'Yapılan'])
    
    for col in ['Gün', 'Görev', 'Hedef', 'Birim', 'Yapılan']:
        if col not in u_info['data'].columns:
            u_info['data'][col] = "" if col != 'Yapılan' else 0

    # --- ÜST GRAFİKLER (BAŞARI ANALİZİ) ---
    if not u_info['data'].empty:
        c1, c2 = st.columns([2, 1])
        with c1:
            # Görev bazlı kıyaslama grafiği
            fig = go.Figure([
                go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Hedef'], name="Hedef", marker_color='#E9ECEF'),
                go.Bar(x=u_info['data']['Görev'], y=u_info['data']['Yapılan'], name="Yapılan", marker_color=TEMA)
            ])
            fig.update_layout(height=300, barmode='group', title="Görev Kıyaslama", margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)
        
        with c2:
            # Genel doluluk oranı (Pasta Grafik)
            done_total = u_info['data']['Yapılan'].astype(float).sum()
            todo_total = u_info['data']['Hedef'].astype(float).sum()
            success_rate = (done_total / todo_total * 100) if todo_total > 0 else 0
            
            fig_pie = go.Figure(go.Pie(
                labels=['Tamamlanan', 'Kalan'], 
                values=[done_total, max(0, todo_total - done_total)], 
                hole=.6, 
                marker_colors=[TEMA, '#FF4B4B']
            ))
            fig_pie.update_layout(height=300, showlegend=False, title=f"Genel Başarı: %{int(success_rate)}")
            st.plotly_chart(fig_pie, use_container_width=True)

    # --- HAFTALIK ÖNİZLEME (YENİ EKLEME) ---
    st.subheader("🗓️ HAFTALIK ÖNİZLEME")
    preview_cols = st.columns(7)
    gunler_liste = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
    
    for i, g in enumerate(gunler_liste):
        with preview_cols[i]:
            st.caption(f"**{g[:3]}**") # Günün ilk 3 harfi (Paz, Sal...)
            day_tasks = u_info['data'][u_info['data']['Gün'] == g]
            if not day_tasks.empty:
                for _, t in day_tasks.iterrows():
                    # Görev yapıldıysa üstünü çiz veya ikon ekle
                    status_icon = "✅" if t['Yapılan'] >= t['Hedef'] else "⏳"
                    st.markdown(f"<p style='font-size:11px; margin-bottom:2px;'>{status_icon} {t['Görev']}</p>", unsafe_allow_html=True)
            else:
                st.markdown("<p style='font-size:10px; color:gray;'>Plan yok</p>", unsafe_allow_html=True)

    st.divider()

    # --- GÜNLÜK TAKİP VE VERİ GİRİŞİ ---
    st.subheader(L["basliklar"]["takip"])
    for g in gunler_liste:
        with st.expander(f"📅 {g.upper()}"):
            temp_df = u_info['data'][u_info['data']['Gün'] == g]
            
            for idx, row in temp_df.iterrows():
                cc1, cc2, cc3 = st.columns([3, 2, 1])
                cc1.write(f"**{row['Görev']}**")
                # Kullanıcı burada yaptığı miktarı günceller
                y_v = cc2.number_input(f"{row['Birim']}", value=int(row['Yapılan']), key=f"inp_{idx}", min_value=0)
                
                if y_v != row['Yapılan']:
                    u_info['data'].at[idx, 'Yapılan'] = y_v
                    u_info['xp'] += 10 # Her güncellemede küçük XP ödülü
                    veritabanini_kaydet(st.session_state.db)
                    st.rerun()
                
                if cc3.button("🗑️", key=f"del_{idx}"):
                    u_info['data'] = u_info['data'].drop(idx).reset_index(drop=True)
                    veritabanini_kaydet(st.session_state.db)
                    st.rerun()
            
            # Yeni Görev Ekleme Formu
            with st.form(f"form_add_{g}", clear_on_submit=True):
                ca, cb, cc = st.columns([2, 1, 1])
                new_task = ca.text_input("Görev Adı")
                new_target = cb.number_input("Hedef Miktar", min_value=1, value=1)
                new_unit = cc.selectbox("Birim", ["Soru", "Saat", "Konu", "Sayfa"])
                if st.form_submit_button("Listeye Ekle"):
                    if new_task:
                        new_row = pd.DataFrame([{'Gün': g, 'Görev': new_task, 'Hedef': new_target, 'Birim': new_unit, 'Yapılan': 0}])
                        u_info['data'] = pd.concat([u_info['data'], new_row], ignore_index=True)
                        veritabanini_kaydet(st.session_state.db)
                        st.rerun()

    st.divider()

    # --- ALIŞKANLIK TAKİPÇİSİ ---
    st.subheader(L["basliklar"]["aliskanlik"])
    habits_data = u_info.get('habits', [])
    h_df = pd.DataFrame(habits_data)
    
    if h_df.empty:
        h_df = pd.DataFrame(columns=["Alışkanlık", "Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"])

    # Veri Editörü: Kullanıcı buradan tik atar
    edited_h = st.data_editor(h_df, num_rows="dynamic", use_container_width=True, hide_index=True, key="h_editor")
    
    if not h_df.equals(edited_h):
        u_info['habits'] = edited_h.to_dict(orient='records')
        veritabanini_kaydet(st.session_state.db)
        st.rerun()
    
    # Yüzde Hesaplama ve İlerleme Çubukları
    for _, row in edited_h.iterrows():
        if row['Alışkanlık']:
            # Sadece gün sütunlarındaki True değerlerini say
            days_checked = sum([1 for day in ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"] if row.get(day) is True])
            weekly_percent = int((days_checked / 7) * 100)
            
            ch1, ch2 = st.columns([1, 4])
            ch1.markdown(f"<p style='font-size:14px; padding-top:10px;'>{row['Alışkanlık']}</p>", unsafe_allow_html=True)
            # İlerleme çubuğunun rengini başarıya göre değiştiriyoruz
            bar_color = TEMA if weekly_percent > 50 else "#FFBB00"
            ch2.progress(days_checked / 7, text=f"Haftalık Performans: %{weekly_percent}")


# --- ODAK ---
elif menu in ["⏱️ Odak", "⏱️ Focus"]:
    st.title(L["basliklar"]["pomo"])
    dk_secenekleri = [15, 25, 45, 60, 90, 120, 150, 180]
    dk = st.select_slider("Dakika Seçin", options=dk_secenekleri, value=25)
    c1, c2, c3 = st.columns(3)
    if c1.button(L["butonlar"]["baslat"]):
        st.session_state.pomo_kalan_saniye, st.session_state.pomo_calisiyor, st.session_state.son_guncelleme = dk * 60, True, time.time()
        st.rerun()
    if c2.button(L["butonlar"]["durdur"]): st.session_state.pomo_calisiyor = False; st.rerun()
    if c3.button(L["butonlar"]["sifirla"]): st.session_state.pomo_calisiyor, st.session_state.pomo_kalan_saniye = False, 25 * 60; st.rerun()
    
    sayac_alani = st.empty()
    sidebar_sayac = st.sidebar.empty()
    if st.session_state.pomo_calisiyor:
        while st.session_state.pomo_kalan_saniye > 0 and st.session_state.pomo_calisiyor:
            st.session_state.pomo_kalan_saniye -= (time.time() - st.session_state.son_guncelleme)
            st.session_state.son_guncelleme = time.time()
            m, s = divmod(max(0, int(st.session_state.pomo_kalan_saniye)), 60)
            zaman_str = f"{m:02d}:{s:02d}"
            sayac_alani.markdown(f"<div style='text-align:center; background:#f0f2f6; border-radius:20px; padding:20px; border:3px solid {TEMA};'><h1 style='font-size:120px; color:{TEMA};'>{zaman_str}</h1></div>", unsafe_allow_html=True)
            sidebar_sayac.info(f"⏱️ Kalan: {zaman_str}")
            if st.session_state.pomo_kalan_saniye <= 0:
                st.session_state.pomo_calisiyor = False; u_info['xp'] += 100; u_info['pomo_count'] += 1
                veritabanini_kaydet(st.session_state.db); st.balloons(); st.rerun()
            time.sleep(1)
    else:
        m, s = divmod(max(0, int(st.session_state.pomo_kalan_saniye)), 60)
        sayac_alani.markdown(f"<div style='text-align:center; background:#f0f2f6; border-radius:20px; padding:20px;'><h1 style='font-size:120px; color:grey;'>{m:02d}:{s:02d}</h1></div>", unsafe_allow_html=True)

# --- SINAVLAR ---
elif menu in ["📅 Sınavlar", "📅 Exams"]:
    st.title(L["basliklar"]["sinavlar"])
    if 'sinavlar' not in u_info: u_info['sinavlar'] = []
    with st.form("ex_f", clear_on_submit=True):
        c1, c2 = st.columns(2)
        d_ad, d_tr = c1.text_input("Ders Adı"), c2.date_input("Sınav Tarihi")
        if st.form_submit_button("Sınav Ekle"):
            if d_ad:
                u_info['sinavlar'].append({"id": str(uuid.uuid4()), "ders": d_ad, "tarih": str(d_tr)})
                veritabanini_kaydet(st.session_state.db); st.rerun()
    for i, ex in enumerate(u_info['sinavlar']):
        with st.container(border=True):
            sc1, sc2, sc3 = st.columns([3, 2, 1])
            sc1.write(f"📖 **{ex['ders']}**"); sc2.info(f"📅 {ex['tarih']}")
            if sc3.button("Sil", key=f"ex_s_{i}"):
                u_info['sinavlar'].pop(i); veritabanini_kaydet(st.session_state.db); st.rerun()

# --- AKADEMİK ---
elif menu in ["🎓 Akademik", "🎓 Academic"]:
    st.title(L["basliklar"]["akademik"])
    
    HARF_KATSY = {
        "AA": 4.0, "BA": 3.5, "BB": 3.0, "CB": 2.5, 
        "CC": 2.0, "DC": 1.5, "DD": 1.0, "FD": 0.5, "FF": 0.0
    }

    tab1, tab2 = st.tabs(["📊 GNO Hesapla", "📉 Devamsızlık"])
    
    with tab1:
        st.subheader("📌 Geçmiş Akademik Başarı (Opsiyonel)")
        st.caption("Eğer önceki dönemlerden gelen ortalamanız varsa giriniz. Yoksa 0 bırakabilirsiniz.")
        
        gc1, gc2 = st.columns(2)
        # Veriyi güvenli çekme
        m_gno_val = u_info.get('mevcut_gno', 0.0)
        m_kr_val = u_info.get('toplam_kredi', 0)
        
        # Scalar (tekil sayı) kontrolü
        safe_gno = float(m_gno_val.iloc[0] if isinstance(m_gno_val, pd.Series) else m_gno_val)
        safe_kr = int(m_kr_val.iloc[0] if isinstance(m_kr_val, pd.Series) else m_kr_val)
        
        m_gno_input = gc1.number_input("Eski Genel Ortalama", 0.0, 4.0, safe_gno, step=0.01)
        m_kr_input = gc2.number_input("Eski Toplam Kredi", 0, 500, safe_kr, step=1)
        
        st.divider()
        st.subheader("📚 Bu Dönemki Dersler")
        
        # Mevcut ders listesini yükle
        gpa_df = pd.DataFrame(u_info.get('gpa_list', []), columns=["Ders", "Kredi", "Harf Notu"])
        
        # Ders tablosu editörü
        edited_gpa = st.data_editor(
            gpa_df, 
            num_rows="dynamic", 
            use_container_width=True,
            column_config={
                "Kredi": st.column_config.NumberColumn("Kredi", min_value=1, max_value=20, step=1),
                "Harf Notu": st.column_config.SelectboxColumn(
                    "Harf Notu",
                    options=list(HARF_KATSY.keys()),
                    required=True,
                )
            }
        )
        
        if st.button("Kaydet ve Genel Ortalamayı Hesapla"):
            # Boş olmayan dersleri filtrele
            clean_df = edited_gpa.dropna(subset=["Ders", "Kredi", "Harf Notu"])
            
            # Bu dönemki toplam kredi ve puan
            donem_kredisi = clean_df["Kredi"].sum()
            donem_puani = sum(row["Kredi"] * HARF_KATSY[row["Harf Notu"]] for _, row in clean_df.iterrows())
            
            # Genel Hesaplama Mantığı:
            # ((Eski GNO * Eski Kredi) + Bu Dönem Puanı) / (Eski Kredi + Bu Dönem Kredisi)
            toplam_genel_kredi = m_kr_input + donem_kredisi
            toplam_genel_puan = (m_gno_input * m_kr_input) + donem_puani
            
            yeni_gno = toplam_genel_puan / toplam_genel_kredi if toplam_genel_kredi > 0 else 0
            donem_ort = donem_puani / donem_kredisi if donem_kredisi > 0 else 0
            
            # Veritabanına Yazma
            u_info['mevcut_gno'] = m_gno_input
            u_info['toplam_kredi'] = m_kr_input
            u_info['gpa_list'] = clean_df.to_dict(orient='records')
            veritabanini_kaydet(st.session_state.db)
            
            # Sonuçları Göster
            res1, res2 = st.columns(2)
            res1.metric("Dönem Ortalaması", f"{donem_ort:.2f}")
            res2.metric("Yeni Genel Ortalama (GNO)", f"{yeni_gno:.2f}", delta=round(yeni_gno - m_gno_input, 3))
            
            if yeni_gno >= 3.0: st.balloons()

    with tab2:
        # Devamsızlık Takibi (Değişmedi, orijinal kodun)
        st.subheader("📉 Devamsızlık Takibi")
        with st.expander("➕ Yeni Ders Ekle"):
            with st.form("yeni_ders_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                yeni_ders_ad = c1.text_input("Ders Adı")
                yeni_ders_limit = c2.number_input("Devamsızlık Hakkı", min_value=1, value=4)
                if st.form_submit_button("Listeye Ekle"):
                    if 'attendance' not in u_info: u_info['attendance'] = []
                    u_info['attendance'].append({"Ders": yeni_ders_ad, "Limit": yeni_ders_limit, "Kaçırılan": 0})
                    veritabanini_kaydet(st.session_state.db)
                    st.rerun()

        if 'attendance' in u_info and u_info['attendance']:
            for idx, item in enumerate(u_info['attendance']):
                with st.container(border=True):
                    col_ad, col_durum, col_islem = st.columns([3, 4, 2])
                    kalan = item['Limit'] - item['Kaçırılan']
                    renk = "red" if kalan <= 0 else "orange" if kalan <= 1 else "green"
                    col_ad.markdown(f"### {item['Ders']}")
                    col_ad.caption(f"Toplam Limit: {item['Limit']}")
                    col_durum.markdown(f"<p style='color:{renk}; font-weight:bold; margin-bottom:0;'>Durum: {item['Kaçırılan']} / {item['Limit']}</p>", unsafe_allow_html=True)
                    col_durum.progress(min(item['Kaçırılan'] / item['Limit'], 1.0))
                    if col_islem.button("➕ Gitmedim", key=f"add_att_{idx}"):
                        u_info['attendance'][idx]['Kaçırılan'] += 1
                        veritabanini_kaydet(st.session_state.db)
                        st.rerun()
                    if col_islem.button("🗑️ Sil", key=f"del_att_{idx}"):
                        u_info['attendance'].pop(idx)
                        veritabanini_kaydet(st.session_state.db)
                        st.rerun()


# --- BAŞARILAR ---
elif menu in ["🏆 Başarılar", "🏆 Achievements"]:
    st.title(L["basliklar"]["basari"])
    c1, c2, c3 = st.columns(3)
    curr_xp = u_info.get('xp', 0)
    curr_level = u_info.get('level', 1)
    pomo_total = u_info.get('pomo_count', 0)
    with c1: st.metric("✨ Toplam XP", f"{curr_xp}")
    with c2: st.metric("🆙 Seviye", f"{curr_level}")
    with c3: st.metric("🔥 Odak Seansları", f"{pomo_total}")
    st.progress((curr_xp % 500) / 500)
    st.divider()
    st.subheader("🏅 Kazanılan Rozetler")
    rozetler = [
        {"isim": "Yolun Başında", "sart": curr_xp >= 100, "ikon": "🌱", "mesaj": "100 XP Barajını Aştın!"},
        {"isim": "Odak Ustası", "sart": pomo_total >= 5, "ikon": "🎯", "mesaj": "5 Başarılı Odak Seansı!"},
        {"isim": "Disiplinli", "sart": curr_level >= 3, "ikon": "📜", "mesaj": "3. Seviyeye Ulaştın!"},
        {"isim": "Gece Kuşu", "sart": curr_xp >= 1000, "ikon": "🦉", "mesaj": "1000 XP Topladın!"}
    ]
    cols = st.columns(4)
    for i, r in enumerate(rozetler):
        with cols[i]:
            if r["sart"]: st.success(f"### {r['ikon']}\n**{r['isim']}**")
            else: st.info(f"### 🔒\n**{r['isim']}**")

# --- AI MENTOR ---
elif menu in ["🤖 AI Mentor"]:
    st.title(L["basliklar"]["mentor"])
    st.info("Merhaba! Ben senin akademik yolculuğunda yanındayım.")
    prompt = st.chat_input("Derslerin hakkında bir şey sor...")
    if prompt:
        with st.chat_message("user"): st.write(prompt)
        with st.chat_message("assistant"): st.write(f"'{prompt}' konulu sorunu aldım.")

# --- AYARLAR ---
elif menu in ["⚙️ Ayarlar", "⚙️ Settings"]:
    st.title("⚙️ Hesap ve Tercihler")
    with st.form("set_full"):
        new_u_id = st.text_input("Kullanıcı Adı", value=u_id)
        new_pass = st.text_input("Yeni Şifre", value=u_info['password'], type="password")
        new_goal = st.text_input("Hedef", value=u_info.get('ana_hedef', ''))
        if st.form_submit_button("Kaydet"):
            if new_u_id != u_id:
                st.session_state.db[new_u_id] = st.session_state.db.pop(u_id)
                st.session_state.aktif_kullanici = new_u_id
            u_info = st.session_state.db[st.session_state.aktif_kullanici]
            u_info.update({'password': new_pass, 'ana_hedef': new_goal})
            veritabanini_kaydet(st.session_state.db)
            st.rerun()

# --- ÇIKIŞ ---
if st.sidebar.button(L["butonlar"]["cikis"]):
    st.session_state.aktif_kullanici = None
    st.rerun()
