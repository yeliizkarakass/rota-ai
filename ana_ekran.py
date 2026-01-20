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
    return sqlite3.connect("rota.db", check_same_thread=False)

def init_db():
    db = get_db()
    c = db.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password BLOB,
        xp INTEGER DEFAULT 0,
        pomo INTEGER DEFAULT 0
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
    for k in LAKAPLAR:
        if level >= k: out = LAKAPLAR[k]
    return out

def mentor_prompt(df, soru, level):
    return f"""
Sen deneyimli bir akademik koçsun.

KULLANICI SEVİYESİ: {level}

VERİ:
{df}

İSTEK:
1. Güçlü yönler
2. Zayıf yönler
3. Haftalık net çalışma planı
4. Somut aksiyonlar
5. Soruya kısa ve net cevap

SORU:
{soru}
"""

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
            else:
                st.error("Hatalı giriş")

    with t2:
        nu = st.text_input("Yeni Kullanıcı")
        np = st.text_input("Yeni Şifre", type="password")
        if st.button("KAYIT"):
            db = get_db()
            c = db.cursor()
            try:
                c.execute("INSERT INTO users VALUES (?, ?, 0, 0)", (nu, hash_pw(np)))
                db.commit()
                st.success("Kayıt başarılı")
            except:
                st.error("Kullanıcı var")

    st.stop()

u = st.session_state.user
db = get_db()
c = db.cursor()

# ---------------- SIDEBAR ----------------
c.execute("SELECT xp, pomo FROM users WHERE username=?", (u,))
xp, pomo = c.fetchone()
level = calc_level(xp)

st.sidebar.title("🚀 ROTA AI")
st.sidebar.metric("Rütbe", get_lakap(level))
st.sidebar.metric("Seviye", level)
st.sidebar.metric("XP", xp)

menu = st.sidebar.radio(
    "Menü",
    ["🏠 Panel", "⏱️ Odak", "🤖 AI Mentor", "⚙️ Ayarlar"]
)

# ---------------- PANEL ----------------
if menu == "🏠 Panel":
    st.title("🏠 Görevler")

    with st.form("ekle"):
        g = st.text_input("Görev")
        h = st.number_input("Hedef", 1)
        b = st.text_input("Birim", "Soru")
        if st.form_submit_button("Ekle"):
            c.execute(
                "INSERT INTO tasks (username, gun, gorev, hedef, birim, yapilan) VALUES (?, ?, ?, ?, ?, 0)",
                (u, datetime.now().strftime("%d/%m"), g, h, b)
            )
            db.commit()
            st.rerun()

    df = pd.read_sql("SELECT * FROM tasks WHERE username=?", db, params=(u,))
    if not df.empty:
        fig = go.Figure()
        fig.add_bar(x=df["gorev"], y=df["hedef"], name="Hedef")
        fig.add_bar(x=df["gorev"], y=df["yapilan"], name="Yapılan")
        st.plotly_chart(fig, use_container_width=True)

        for _, r in df.iterrows():
            v = st.number_input(r["gorev"], value=r["yapilan"], key=r["id"])
            if v != r["yapilan"]:
                c.execute("UPDATE tasks SET yapilan=? WHERE id=?", (v, r["id"]))
                c.execute("UPDATE users SET xp=xp+? WHERE username=?", (XP_PER_TASK, u))
                db.commit()
                st.rerun()

# ---------------- POMODORO ----------------
elif menu == "⏱️ Odak":
    st.title("⏱️ Pomodoro")
    if st.button("25 dk Başlat"):
        st.session_state.end = time.time() + 1500

    if "end" in st.session_state:
        left = int(st.session_state.end - time.time())
        if left <= 0:
            c.execute("UPDATE users SET xp=xp+?, pomo=pomo+1 WHERE username=?", (XP_PER_POMO, u))
            db.commit()
            del st.session_state.end
            st.balloons()
        else:
            m, s = divmod(left, 60)
            st.markdown(f"<h1>{m:02d}:{s:02d}</h1>", unsafe_allow_html=True)
            time.sleep(1)
            st.rerun()

# ---------------- AI MENTOR ----------------
elif menu == "🤖 AI Mentor":
    st.title("🤖 Akademik Koç")
    msg = st.chat_input("Sorunu yaz")
    if msg:
        df = pd.read_sql("SELECT gorev, hedef, yapilan FROM tasks WHERE username=?", db, params=(u,))
        ans = ai_call(mentor_prompt(df.to_string(), msg, level))
        st.chat_message("assistant").write(ans)

# ---------------- SETTINGS ----------------
elif menu == "⚙️ Ayarlar":
    if st.button("ÇIKIŞ"):
        st.session_state.user = None
        st.rerun()
