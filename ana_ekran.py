import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sqlite3, time
from datetime import datetime
import bcrypt
import google.generativeai as genai

# ---------------- CONFIG ----------------
st.set_page_config(page_title="ROTA AI PRO", page_icon="🚀", layout="wide")

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

# ---------------- DB ----------------
def get_db():
    # Veritabanı adını 'rota_final.db' yaparak temiz bir başlangıç sağlıyoruz
    return sqlite3.connect("rota_final.db", check_same_thread=False)

def init_db():
    db = get_db()
    c = db.cursor()
    # Tabloyu en baştan theme_color ile oluşturuyoruz
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password BLOB,
        xp INTEGER DEFAULT 0,
        pomo INTEGER DEFAULT 0,
        theme_color TEXT DEFAULT '#FF4B4B'
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        gun TEXT,
        gorev TEXT,
        hedef INTEGER,
        birim TEXT,
        yapilan INTEGER
    )
    """)
    db.commit()

init_db()

# ---------------- HELPERS ----------------
def hash_pw(pw): return bcrypt.hashpw(pw.encode(), bcrypt.gensalt())
def check_pw(pw, h): return bcrypt.checkpw(pw.encode(), h)
def calc_level(xp): return max(1, xp // XP_LEVEL_BASE + 1)

def get_lakap(level):
    out = LAKAPLAR[1]
    for k in sorted(LAKAPLAR.keys()):
        if level >= k: out = LAKAPLAR[k]
    return out

# GÜÇLENDİRİLMİŞ TEMA UYGULAYICI
def apply_theme(color):
    st.markdown(f"""
        <style>
        /* Ana Arka Plan ve Metin Renkleri */
        h1, h2, h3, .stMarkdown p {{ color: {color} !important; }}
        
        /* Butonlar */
        div.stButton > button:first-child {{
            background-color: {color} !important;
            color: white !important;
            border: none !important;
            border-radius: 10px !important;
        }}
        
        /* Sidebar */
        [data-testid="stSidebar"] {{
            background-color: #f0f2f6;
            border-right: 3px solid {color} !important;
        }}
        
        /* Progress Bar (Seviye Çubuğu) */
        .stProgress > div > div > div > div {{
            background-color: {color} !important;
        }}

        /* Giriş Alanları Odak Rengi */
        input:focus {{
            border-color: {color} !important;
            box-shadow: 0 0 0 1px {color} !important;
        }}
        </style>
        """, unsafe_allow_html=True)

def ai_call(prompt):
    model = genai.GenerativeModel("gemini-1.5-flash")
    return model.generate_content(prompt).text

# ---------------- SESSION ----------------
if "user" not in st.session_state:
    st.session_state.user = None

# ---------------- LOGIN ----------------
if not st.session_state.user:
    st.title("🚀 ROTA AI")
    t1, t2 = st.tabs(["Giriş", "Kayıt"])
    with t1:
        u = st.text_input("Kullanıcı")
        p = st.text_input("Şifre", type="password")
        if st.button("GİRİŞ"):
            db = get_db()
            c = db.cursor()
            c.execute("SELECT password FROM users WHERE username=?", (u,))
            r = c.fetchone()
            if r and check_pw(p, r[0]):
                st.session_state.user = u
                st.rerun()
            else: st.error("Hatalı giriş")
    with t2:
        nu = st.text_input("Yeni Kullanıcı")
        np = st.text_input("Yeni Şifre", type="password")
        if st.button("KAYIT"):
            db = get_db()
            c = db.cursor()
            try:
                c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (nu, hash_pw(np)))
                db.commit()
                st.success("Kayıt başarılı! Giriş yapabilirsiniz.")
            except: st.error("Bu kullanıcı adı zaten alınmış.")
    st.stop()

# ---------------- LOGGED IN ----------------
u = st.session_state.user
db = get_db()
c = db.cursor()

# Verileri ve Rengi Çek
c.execute("SELECT xp, pomo, theme_color FROM users WHERE username=?", (u,))
xp, pomo, user_color = c.fetchone()
apply_theme(user_color)

level = calc_level(xp)

# ---------------- SIDEBAR ----------------
st.sidebar.title("🚀 ROTA AI")
st.sidebar.metric("Rütbe", get_lakap(level))
st.sidebar.metric("Seviye", level)
st.sidebar.metric("XP", xp)

menu = st.sidebar.radio("Menü", ["🏠 Panel", "⏱️ Odak", "🤖 AI Mentor", "⚙️ Ayarlar"])

# ---------------- PANEL ----------------
if menu == "🏠 Panel":
    st.title("🏠 Görev Paneli")
    with st.form("gorev_ekle"):
        g = st.text_input("Yeni Görev")
        h = st.number_input("Hedef", 1)
        b = st.text_input("Birim", "Soru")
        if st.form_submit_button("Ekle"):
            c.execute("INSERT INTO tasks (username, gun, gorev, hedef, birim, yapilan) VALUES (?, ?, ?, ?, ?, 0)",
                      (u, datetime.now().strftime("%d/%m"), g, h, b))
            db.commit()
            st.rerun()

    df = pd.read_sql("SELECT * FROM tasks WHERE username=?", db, params=(u,))
    if not df.empty:
        fig = go.Figure()
        fig.add_bar(x=df["gorev"], y=df["hedef"], name="Hedef", marker_color="#DDDDDD")
        fig.add_bar(x=df["gorev"], y=df["yapilan"], name="Yapılan", marker_color=user_color)
        st.plotly_chart(fig, use_container_width=True)

        for _, r in df.iterrows():
            v = st.number_input(f"{r['gorev']} (Birim: {r['birim']})", value=r["yapilan"], key=f"task_{r['id']}")
            if v != r["yapilan"]:
                c.execute("UPDATE tasks SET yapilan=? WHERE id=?", (v, r["id"]))
                c.execute("UPDATE users SET xp=xp+? WHERE username=?", (XP_PER_TASK, u))
                db.commit()
                st.rerun()

# ---------------- POMODORO ----------------
elif menu == "⏱️ Odak":
    st.title("⏱️ Pomodoro Sayacı")
    if st.button("25 Dakikalık Odaklanma Başlat"):
        st.session_state.end = time.time() + 1500

    if "end" in st.session_state:
        left = int(st.session_state.end - time.time())
        if left <= 0:
            c.execute("UPDATE users SET xp=xp+?, pomo=pomo+1 WHERE username=?", (XP_PER_POMO, u))
            db.commit()
            del st.session_state.end
            st.balloons()
            st.rerun()
        else:
            m, s = divmod(left, 60)
            st.markdown(f"<h1 style='text-align:center; font-size: 100px;'>{m:02d}:{s:02d}</h1>", unsafe_allow_html=True)
            time.sleep(1)
            st.rerun()

# ---------------- AI MENTOR ----------------
elif menu == "🤖 AI Mentor":
    st.title("🤖 Akademik Koç")
    msg = st.chat_input("Gelişimini sormak için yaz...")
    if msg:
        tasks_df = pd.read_sql("SELECT gorev, hedef, yapilan FROM tasks WHERE username=?", db, params=(u,))
        prompt = f"Kullanıcı Seviyesi: {level}. Görevler: {tasks_df.to_string()}. Soru: {msg}"
        ans = ai_call(prompt)
        st.chat_message("assistant").write(ans)

# ---------------- SETTINGS ----------------
elif menu == "⚙️ Ayarlar":
    st.title("⚙️ Uygulama Ayarları")
    
    st.subheader("🎨 Tema Özelleştirme")
    # Renk seçici burada!
    picked_color = st.color_picker("Bir ana tema rengi belirleyin:", user_color)
    
    if st.button("Seçilen Rengi Kaydet"):
        c.execute("UPDATE users SET theme_color=? WHERE username=?", (picked_color, u))
        db.commit()
        st.success(f"Tema rengi {picked_color} olarak güncellendi! Lütfen bekleyin...")
        time.sleep(1)
        st.rerun()
        
    st.divider()
    if st.button("Sistemden Güvenli Çıkış Yap"):
        st.session_state.user = None
        st.rerun()
