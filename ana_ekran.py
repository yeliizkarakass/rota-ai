# ================================
# ROTA AI - STABILIZED SINGLE FILE
# ================================

import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import json, os, time, uuid
import google.generativeai as genai

# ---------------- CONFIG ----------------
st.set_page_config(page_title="ROTA AI", page_icon="🚀", layout="wide")
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

# ---------------- HELPERS ----------------
def calc_level(xp):
    return max(1, xp // XP_LEVEL_BASE + 1)

def get_lakap(level):
    lakap = LAKAPLAR[1]
    for k in LAKAPLAR:
        if level >= k:
            lakap = LAKAPLAR[k]
    return lakap

def ai_call(prompt):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        return model.generate_content(prompt).text
    except:
        return "⚠️ AI şu anda meşgul."

# ---------------- DB ----------------
def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    for u in raw:
        raw[u].setdefault("xp", 0)
        raw[u]["level"] = calc_level(raw[u]["xp"])
        raw[u].setdefault("pomo_count", 0)
        raw[u].setdefault("chat_history", [])
        raw[u].setdefault("notes", [])
        raw[u].setdefault("habits", [])
        raw[u].setdefault("attendance", [])
        raw[u].setdefault("gpa_list", [])
        raw[u].setdefault("sinavlar", [])
        raw[u]["data"] = pd.DataFrame(
            raw[u].get("data", []),
            columns=["Gün", "Görev", "Hedef", "Birim", "Yapılan"]
        )
    return raw

def save_db(db):
    out = {}
    for u in db:
        out[u] = db[u].copy()
        out[u]["data"] = db[u]["data"].to_dict(orient="records")
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

# ---------------- LOGIN ----------------
if not st.session_state.user:
    st.title("🚀 ROTA AI")
    u = st.text_input("Kullanıcı")
    p = st.text_input("Şifre", type="password")
    if st.button("GİRİŞ"):
        if u in st.session_state.db and st.session_state.db[u]["password"] == p:
            st.session_state.user = u
            st.rerun()
        else:
            st.error("Hatalı giriş")
    st.stop()

u = st.session_state.user
u_info = st.session_state.db[u]

# ---------------- SIDEBAR ----------------
st.sidebar.title("🚀 ROTA AI")
st.sidebar.metric("Rütbe", get_lakap(u_info["level"]))
st.sidebar.metric("Seviye", u_info["level"])
st.sidebar.metric("XP", u_info["xp"])

menu = st.sidebar.radio(
    "Menü",
    ["🏠 Panel", "📅 Sınavlar", "⏱️ Odak", "🎓 Akademik", "🤖 AI Mentor", "🏆 Başarılar", "⚙️ Ayarlar"]
)

# ---------------- PANEL ----------------
if menu == "🏠 Panel":
    st.title(f"✨ {u.upper()}")
    df = u_info["data"]

    if not df.empty:
        fig = go.Figure()
        fig.add_bar(x=df["Görev"], y=df["Hedef"], name="Hedef")
        fig.add_bar(x=df["Görev"], y=df["Yapılan"], name="Yapılan")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Görevler")
    for i, row in df.iterrows():
        c1, c2 = st.columns([4, 1])
        val = c1.number_input(row["Görev"], value=int(row["Yapılan"]), key=f"t_{i}")
        if val != row["Yapılan"]:
            u_info["data"].at[i, "Yapılan"] = val
            u_info["xp"] += XP_PER_TASK
            u_info["level"] = calc_level(u_info["xp"])
            save_db(st.session_state.db)
            st.rerun()
        if c2.button("🗑️", key=f"d_{i}"):
            u_info["data"] = df.drop(i).reset_index(drop=True)
            save_db(st.session_state.db)
            st.rerun()

# ---------------- POMODORO ----------------
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
            u_info["level"] = calc_level(u_info["xp"])
            save_db(st.session_state.db)
            st.balloons()

        m, s = divmod(max(0, st.session_state.pomo_left), 60)
        st.markdown(f"<h1 style='text-align:center'>{m:02d}:{s:02d}</h1>", unsafe_allow_html=True)
        time.sleep(1)
        st.rerun()

# ---------------- AI MENTOR ----------------
elif menu == "🤖 AI Mentor":
    st.title("🤖 AI Mentor")
    if st.button("📊 Analiz"):
        st.info(ai_call(u_info["data"].to_string()))

    for m in u_info["chat_history"]:
        st.chat_message(m["role"]).write(m["text"])

    msg = st.chat_input("Yaz...")
    if msg:
        u_info["chat_history"].append({"role": "user", "text": msg})
        ans = ai_call(msg)
        u_info["chat_history"].append({"role": "assistant", "text": ans})
        save_db(st.session_state.db)
        st.rerun()

# ---------------- ACHIEVEMENTS ----------------
elif menu == "🏆 Başarılar":
    st.title("🏆 Başarılar")
    st.progress(min(u_info["xp"] / (u_info["level"] * XP_LEVEL_BASE), 1.0))
    if u_info["pomo_count"] >= 10:
        st.success("🔥 Odak Ustası")

# ---------------- SETTINGS ----------------
elif menu == "⚙️ Ayarlar":
    if st.button("ÇIKIŞ"):
        st.session_state.user = None
        st.rerun()
