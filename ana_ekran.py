# --- 1. VERİ YÖNETİMİ GÜNCELLEME ---
def veritabanini_yukle():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for u in data:
                    # Mevcut verileri koru, eksikleri tamamla
                    defaults = {
                        'password': '', 'xp': 0, 'level': 1, 'ana_hedef': 'Öğrenci', 
                        'egitim_duzeyi': 'Lisans', 'sinavlar': [], 'notes': [], 
                        'pomo_count': 0, 'dil': 'TR', 'habits': [], 'attendance': [], 
                        'gpa_list': [], 'tema_rengi': '#4FACFE', 'mevcut_gno': 0.0, 'toplam_kredi': 0
                    }
                    for k, v in defaults.items():
                        if k not in data[u]: data[u][k] = v
                    
                    # DataFrame dönüşümünü sağla
                    if not isinstance(data[u]['data'], pd.DataFrame):
                        data[u]['data'] = pd.DataFrame(data[u]['data'])
                return data
        except: return {}
    return {}

def veritabanini_kaydet(db):
    to_save = {}
    for u in db:
        user_data = db[u].copy()
        # Seviye hesaplama
        user_data['level'] = (user_data.get('xp', 0) // 500) + 1
        # DataFrame'i JSON için listeye çevir
        if isinstance(user_data['data'], pd.DataFrame):
            user_data['data'] = user_data['data'].to_dict(orient='records')
        to_save[u] = user_data
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=4)

# --- GİRİŞ & KAYIT SİSTEMİ ---
if 'db' not in st.session_state: st.session_state.db = veritabanini_yukle()

# Uygulama açıldığında otomatik hatırlama kontrolü
if 'aktif_kullanici' not in st.session_state:
    st.session_state.aktif_kullanici = None

if st.session_state.aktif_kullanici is None:
    st.title("🚀 ROTA AI")
    t1, t2 = st.tabs(["🔑 GİRİŞ", "📝 KAYIT"])
    
    with t1:
        u = st.text_input("Kullanıcı Adı", key="login_user")
        p = st.text_input("Şifre", type="password", key="login_pass")
        beni_hatirla = st.checkbox("Beni Hatırla")
        
        if st.button("GİRİŞ YAP"):
            if u in st.session_state.db and st.session_state.db[u]['password'] == p:
                st.session_state.aktif_kullanici = u
                # Not: Beni hatırla seçilirse session aktif kalır. 
                # Kalıcı çerezler Streamlit'te ekstra kütüphane gerektirir ancak bu yapı tarayıcı açıkken seni tutar.
                st.success(f"Hoş geldin {u}!")
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı!")

    with t2:
        with st.form("kayit_formu"):
            nu = st.text_input("Kullanıcı Adı oluştur")
            np = st.text_input("Şifre belirle", type="password")
            n_meslek = st.text_input("Meslek / Bölüm (Örn: Elektrik Müh.)")
            n_seviye = st.selectbox("Eğitim Seviyesi", ["Lise", "Önlisans", "Lisans", "Yüksek Lisans", "Doktora"])
            
            submit_kayit = st.form_submit_button("HESAP OLUŞTUR")
            
            if submit_kayit:
                if nu and np and n_meslek:
                    if nu not in st.session_state.db:
                        st.session_state.db[nu] = {
                            'password': np,
                            'xp': 0,
                            'level': 1,
                            'ana_hedef': n_meslek,
                            'egitim_duzeyi': n_seviye,
                            'data': pd.DataFrame(columns=['Gün', 'Görev', 'Hedef', 'Birim', 'Yapılan']),
                            'dil': 'TR',
                            'tema_rengi': '#4FACFE',
                            'habits': [],
                            'notes': [],
                            'sinavlar': [],
                            'mevcut_gno': 0.0,
                            'toplam_kredi': 0,
                            'pomo_count': 0
                        }
                        veritabanini_kaydet(st.session_state.db)
                        st.success("Hesabın başarıyla oluşturuldu! Giriş sekmesine geçebilirsin.")
                    else:
                        st.warning("Bu kullanıcı adı zaten mevcut.")
                else:
                    st.error("Lütfen tüm alanları doldur.")
    st.stop()


u_id = st.session_state.aktif_kullanici
u_info = st.session_state.db[u_id]
L = DIL_PAKETI.get(u_info.get('dil', 'TR'), DIL_PAKETI["TR"])
TEMA = u_info.get('tema_rengi', '#4FACFE')

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

    # --- ALIŞKANLIKLAR BÖLÜMÜ ---
    st.divider()
    st.subheader(L["basliklar"]["aliskanlik"])
    h_df = pd.DataFrame(u_info.get('habits', []), columns=["Alışkanlık", "Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"])
    if h_df.empty: 
        h_df = pd.DataFrame([{"Alışkanlık": "Kitap Okuma 📖", "Pzt": False, "Sal": False, "Çar": False, "Per": False, "Cum": False, "Cmt": False, "Paz": False}])
    
    edited_h = st.data_editor(h_df, num_rows="dynamic", use_container_width=True, hide_index=True, key="habit_editor")
    
    if not h_df.equals(edited_h):
        u_info['habits'] = edited_h.to_dict(orient='records')
        veritabanini_kaydet(st.session_state.db)
        # Progress bar'ların güncellenmesi için rerun yerine sadece görselleştirme yeterli ama stabilite için:
    
    for _, row in edited_h.iterrows():
        tik = sum([1 for gun in ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"] if row.get(gun, False) is True])
        c_h1, c_h2 = st.columns([1, 3])
        c_h1.caption(f"**{row['Alışkanlık']}**")
        c_h2.progress(tik / 7, text=f"%{int((tik/7)*100)}")

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
# --- BAŞARILAR ---
elif menu in ["🏆 Başarılar", "🏆 Achievements"]:
    st.title(L["basliklar"]["basari"])
    
    # Üst Bilgi Kartları
    c1, c2, c3 = st.columns(3)
    current_xp = u_info.get('xp', 0)
    current_level = u_info.get('level', 1)
    pomo_total = u_info.get('pomo_count', 0)
    
    with c1:
        st.metric("✨ Toplam XP", f"{current_xp}")
    with c2:
        st.metric("🆙 Seviye", f"{current_level}")
    with c3:
        st.metric("🔥 Odak Seansları", f"{pomo_total}")

    # Seviye İlerleme Çubuğu
    xp_for_next_level = 500
    progress_val = (current_xp % xp_for_next_level) / xp_for_next_level
    st.write(f"**Sonraki Seviye İlerlemesi:** {current_xp % xp_for_next_level} / {xp_for_next_level} XP")
    st.progress(progress_val)
    
    st.divider()
    
    # Rozetler (Achievements) Bölümü
    st.subheader("🏅 Kazanılan Rozetler")
    
    # Rozet kriterlerini belirleyelim
    rozetler = [
        {"isim": "Yolun Başında", "sart": current_xp >= 100, "ikon": "🌱", "mesaj": "100 XP Barajını Aştın!"},
        {"isim": "Odak Ustası", "sart": pomo_total >= 5, "ikon": "🎯", "mesaj": "5 Başarılı Odak Seansı!"},
        {"isim": "Disiplinli", "sart": current_level >= 3, "ikon": "📜", "mesaj": "3. Seviyeye Ulaştın!"},
        {"isim": "Gece Kuşu", "sart": current_xp >= 1000, "ikon": "🦉", "mesaj": "1000 XP Topladın!"},
        {"isim": "Zirve Mimarı", "sart": pomo_total >= 20, "ikon": "🏔️", "mesaj": "20 Odak Seansı Tamamlandı!"},
        {"isim": "Efsane", "sart": current_level >= 10, "ikon": "🌟", "mesaj": "10. Seviyeye Ulaştın!"}
    ]
    
    # Rozetleri 3'lü sütunlar halinde gösterelim
    cols = st.columns(3)
    for i, r in enumerate(rozetler):
        with cols[i % 3]:
            if r["sart"]:
                st.success(f"### {r['ikon']}\n**{r['isim']}**\n\n{r['mesaj']}")
            else:
                st.info(f"### 🔒\n**{r['isim']}**\n\n*Kilitli*")

    st.divider()
    
    # İstatistiksel Özet
    with st.expander("📊 Detaylı XP İstatistikleri"):
        st.write(f"Tamamlanan Görevlerden Gelen Tahmini XP: {len(u_info.get('data', [])) * 20}")
        st.write(f"Odak Seanslarından Gelen XP: {pomo_total * 100}")
        st.info("İpucu: Her görev tamamlama 20 XP, her odak seansı (Pomodoro) 100 XP kazandırır!")

# --- AI MENTOR ---
elif menu in ["🤖 AI Mentor"]:
    st.title(L["basliklar"]["mentor"])
    st.info("Merhaba! Ben senin akademik yolculuğunda yanındayım. Mühendislik derslerin, diferansiyel denklemler veya devre analizi hakkında bana sorular sorabilirsin.")
    prompt = st.chat_input("Derslerin hakkında bir şey sor...")
    if prompt:
        with st.chat_message("user"): st.write(prompt)
        with st.chat_message("assistant"):
            st.write(f"'{prompt}' konulu sorunu aldım. Şu an mühendislik veri tabanımı tarıyorum.")

# --- AYARLAR ---
elif menu in ["⚙️ Ayarlar", "⚙️ Settings"]:
    st.title("⚙️ Hesap ve Tercihler")
    with st.form("set_full"):
        st.subheader("👤 Profil Düzenle")
        new_u_id = st.text_input("Kullanıcı Adı (Giriş ID)", value=u_id)
        new_pass = st.text_input("Yeni Şifre", value=u_info['password'], type="password")
        new_goal = st.text_input("Hedef Meslek / Bölüm", value=u_info.get('ana_hedef', ''))
        st.subheader("🌍 Sistem")
        new_lang = st.selectbox("Dil", ["TR", "EN"], index=0 if u_info['dil'] == "TR" else 1)
        if st.form_submit_button("Değişiklikleri Kaydet"):
            if new_u_id != u_id:
                st.session_state.db[new_u_id] = st.session_state.db.pop(u_id)
                st.session_state.aktif_kullanici = new_u_id
            u_info = st.session_state.db[st.session_state.aktif_kullanici]
            u_info.update({'password': new_pass, 'ana_hedef': new_goal, 'dil': new_lang})
            veritabanini_kaydet(st.session_state.db)
            st.success("Bilgiler güncellendi!")
            st.rerun()

# --- ÇIKIŞ ---
if st.sidebar.button(L["butonlar"]["cikis"]):
    st.session_state.aktif_kullanici = None
    st.rerun()
