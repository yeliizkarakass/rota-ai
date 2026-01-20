import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import json, os, time, hashlib
import google.generativeai as genai

# ---------------- CONFIG ----------------
st.set_page_config(page_title="ROTA AI - FULL", page_icon="🚀", layout="wide")
DB_FILE = "rota_database.json"

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# ---------------- CONSTANTS ----------------
XP_PER_TASK = 10
XP_PER_POMO = 30
XP_LEVEL_BASE = 200

LAKAPLAR = {
    1: "Meraklı Yolcu 🚶",
    4: "Disiplin Kurucu 🏗️",
    8: "Odak Ustası 🎯",
    13: "Strateji Dehası 🧠",
    20: "Vizyoner Lider 👑",
    36: "Zirve Mimarı 🏔️",
    50: "Efsane 🌟"
}

# ---------------- HELPERS (GÜVENLİK EKLENDİ) ----------------
def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

def calc_level(xp):
    return max(1, xp // XP_LEVEL_BASE + 1)

def get_lakap(level):
    lakap = LAKAPLAR[1]
    for k in sorted(LAKAPLAR.keys()):
        if level >= k: lakap = LAKAPLAR[k]
    return lakap

def ai_call(prompt):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        return model.generate_content(prompt).text
    except:
        return "⚠️ AI şu anda meşgul."

# ---------------- DATABASE (TAMAMEN SENİN YAPIN) ----------------
def load_db():
    if not os.path.exists(DB_FILE): return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    for u in raw:
        # Eksik anahtarları tamamla (Veri kaybını önler)
        defaults = {
            "xp": 0, "pomo_count": 0, "chat_history": [], 
            "notes": [], "habits": [], "attendance": [], 
            "gpa_list": [], "sinavlar": [], "tasks": []
        }
        for key, val in defaults.items():
            raw[u].setdefault(key, val)
        
        # Pandas DF dönüşümü (Senin orijinal mantığın)
        raw[u]["data"] = pd.DataFrame(
            raw[u].get("tasks", []),
            columns=["Gün", "Görev", "Hedef", "Birim", "Yapılan"]
        )
    return raw

def save_db(db):
    out = {}
    for user_key in db:
        temp = db[user_key].copy()
        # DataFrame'i tekrar listeye çeviriyoruz ki JSON'a yazılsın
        if isinstance(temp["data"], pd.DataFrame):
            temp["tasks"] = temp["data"].to_dict(orient="records")
            del temp["data"]
        out[user_key] = temp
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

# ---------------- SESSION ----------------
if "db" not in st.session_state:
    st.session_state.db = load_db()
if "user" not in st.session_state:
    st.session_state.user = None
if "pomo_run" not in st.session_state:
    st.session_state.pomo_run = False
    st.session_state.pomo_left = 25 * 60
    st.session_state.pomo_last = time.time()

# ---------------- LOGIN / REGISTER ----------------
if not st.session_state.user:
    st.title("🚀 ROTA AI")
    t1, t2 = st.tabs(["Giriş", "Kayıt"])
    with t1:
        u = st.text_input("Kullanıcı")
        p = st.text_input("Şifre", type="password")
        if st.button("GİRİŞ"):
            # Hem normal hem hashli kontrol (Eski kullanıcılar için)
            if u in st.session_state.db and (st.session_state.db[u]["password"] == p or st.session_state.db[u]["password"] == hash_pw(p)):
                st.session_state.user = u
                st.rerun()
            else: st.error("Hatalı giriş")
    with t2:
        nu = st.text_input("Yeni Kullanıcı")
        np = st.text_input("Yeni Şifre", type="password")
        if st.button("KAYIT"):
            if nu not in st.session_state.db:
                st.session_state.db[nu] = {"password": hash_pw(np), "xp": 0}
                save_db(st.session_state.db)
                st.success("Kayıt başarılı!")
            else: st.error("Kullanıcı mevcut")
    st.stop()

u = st.session_state.user
u_info = st.session_state.db[u]

# ---------------- SIDEBAR ----------------
st.sidebar.title("🚀 ROTA AI")
level = calc_level(u_info["xp"])
st.sidebar.metric("Rütbe", get_lakap(level))
st.sidebar.metric("Seviye", level)
st.sidebar.metric("XP", u_info["xp"])

menu = st.sidebar.radio(
    "Menü",
    ["🏠 Panel", "📅 Sınavlar", "⏱️ Odak", "🎓 Akademik", "🤖 AI Mentor", "🏆 Başarılar", "⚙️ Ayarlar"]
)

# ---------------- 🏠 PANEL (GÖREV EKLEME DAHİL) ----------------
if menu == "🏠 Panel":
    st.title(f"✨ {u.upper()} PANELİ")
    
    with st.expander("➕ Yeni Görev Ekle"):
        with st.form("yeni_gorev"):
            g_ad = st.text_input("Görev Adı")
            g_hd = st.number_input("Hedef", 1)
            g_br = st.text_input("Birim", "Soru")
            if st.form_submit_button("Ekle"):
                new_row = {"Gün": datetime.now().strftime("%d/%m"), "Görev": g_ad, "Hedef": g_hd, "Birim": g_br, "Yapılan": 0}
                u_info["data"] = pd.concat([u_info["data"], pd.DataFrame([new_row])], ignore_index=True)
                save_db(st.session_state.db)
                st.rerun()

    df = u_info["data"]
    if not df.empty:
        fig = go.Figure()
        fig.add_bar(x=df["Görev"], y=df["Hedef"], name="Hedef")
        fig.add_bar(x=df["Görev"], y=df["Yapılan"], name="Yapılan")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📋 Görevler")
        for i, row in df.iterrows():
            c1, c2, c3 = st.columns([4, 1, 1])
            val = c1.number_input(f"{row['Görev']} ({row['Birim']})", value=int(row["Yapılan"]), key=f"t_{i}")
            if val != row["Yapılan"]:
                u_info["data"].at[i, "Yapılan"] = val
                u_info["xp"] += XP_PER_TASK
                save_db(st.session_state.db)
                st.rerun()
            if c3.button("🗑️", key=f"d_{i}"):
                u_info["data"] = df.drop(i).reset_index(drop=True)
                save_db(st.session_state.db)
                st.rerun()

# ---------------- ⏱️ ODAK (POMODORO) ----------------
elif menu == "⏱️ Odak":
    st.title("⏱️ Odak")
    mins = st.selectbox("Dakika", [15, 25, 45, 60], index=1)
    if st.button("Başlat"):
        st.session_state.pomo_left = mins * 60
        st.session_state.pomo_run = True
        st.session_state.pomo_last = time.time()

    if st.session_state.pomo_run:
        now = time.time()
        st.session_state.pomo_left -= int(now - st.session_state.pomo_last)
        st.session_state.pomo_last = now
        if st.session_state.pomo_left <= 0:
            st.session_state.pomo_run = False
            u_info["xp"] += XP_PER_POMO
            u_info["pomo_count"] += 1
            save_db(st.session_state.db)
            st.balloons()
        m, s = divmod(max(0, st.session_state.pomo_left), 60)
        st.markdown(f"<h1 style='text-align:center'>{m:02d}:{s:02d}</h1>", unsafe_allow_html=True)
        time.sleep(1)
        st.rerun()

# ---------------- 🎓 AKADEMİK (GPA) ----------------
elif menu == "🎓 Akademik":
    st.title("🎓 Akademik Takip")
    # Not Ekleme
    with st.form("not_ekle"):
        d_ad = st.text_input("Ders")
        d_nt = st.number_input("Not", 0, 100)
        d_kr = st.number_input("Kredi", 1, 10)
        if st.form_submit_button("Kaydet"):
            u_info["gpa_list"].append({"ders": d_ad, "not": d_nt, "kredi": d_kr})
            save_db(st.session_state.db)
    
    if u_info["gpa_list"]:
        st.table(pd.DataFrame(u_info["gpa_list"]))

# ---------------- 🤖 AI MENTOR ----------------
elif menu == "🤖 AI Mentor":
    st.title("🤖 AI Mentor")
    msg = st.chat_input("Mesajın...")
    if msg:
        u_info["chat_history"].append({"role": "user", "text": msg})
        ans = ai_call(f"Sen bir akademik koçsun. Kullanıcı verisi: {u_info['data'].to_string()}. Soru: {msg}")
        u_info["chat_history"].append({"role": "assistant", "text": ans})
        save_db(st.session_state.db)
        st.rerun()
    for m in u_info["chat_history"][-10:]: # Son 10 mesaj
        st.chat_message(m["role"]).write(m["text"])

# ---------------- ⚙️ AYARLAR ----------------
elif menu == "⚙️ Ayarlar":
    if st.button("ÇIKIŞ"):
        st.session_state.user = None
        st.rerun()
