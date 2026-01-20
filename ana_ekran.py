import streamlit as st
import pandas as pd
import time
import json
import os
import plotly.graph_objects as go
import google.generativeai as genai

# ================== AYARLAR ==================
st.set_page_config(page_title="ROTA AI PRO", page_icon="🚀", layout="wide")

DB_FILE = "rota_database.json"
CONFIG_FILE = "user_config.json"

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# ================== LAKAPLAR ==================
LAKAPLAR = {
    1: {"TR": "Meraklı Yolcu 🚶", "EN": "Curious Traveler 🚶"},
    4: {"TR": "Disiplin Kurucu 🏗️", "EN": "Discipline Builder 🏗️"},
    8: {"TR": "Odak Ustası 🎯", "EN": "Focus Master 🎯"},
    13: {"TR": "Strateji Dehası 🧠", "EN": "Strategy Genius 🧠"},
    20: {"TR": "Vizyoner Lider 👑", "EN": "Visionary Leader 👑"},
}

# ================== DB ==================
def veritabanini_yukle():
    if not os.path.exists(DB_FILE):
        return {}

    with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    for u in data:
        defaults = {
            "password": "",
            "xp": 0,
            "level": 1,
            "dil": "TR",
            "tema_rengi": "#4FACFE",
            "habits": [],
            "data": [],
            "pomo_count": 0
        }

        for k, v in defaults.items():
            if k not in data[u]:
                data[u][k] = v

        if not isinstance(data[u]["data"], list):
            data[u]["data"] = []

        data[u]["data"] = pd.DataFrame(data[u]["data"])

    return data


def veritabanini_kaydet(db):
    out = {}
    for u in db:
        temp = db[u].copy()
        temp["data"] = temp["data"].to_dict(orient="records")
        out[u] = temp

    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=4)


def mevcut_lakap(level, dil):
    secili = LAKAPLAR[1][dil]
    for l in LAKAPLAR:
        if level >= l:
            secili = LAKAPLAR[l][dil]
    return secili

# ================== SESSION ==================
if "db" not in st.session_state:
    st.session_state.db = veritabanini_yukle()

if "user" not in st.session_state:
    st.session_state.user = None

if "pomo_aktif" not in st.session_state:
    st.session_state.pomo_aktif = False

if "pomo_bitis" not in st.session_state:
    st.session_state.pomo_bitis = None

# ================== AUTO LOGIN ==================
if st.session_state.user is None and os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
            if cfg.get("user") in st.session_state.db:
                st.session_state.user = cfg["user"]
    except:
        pass

# ================== LOGIN ==================
if st.session_state.user is None:
    st.title("🚀 ROTA AI")

    t1, t2 = st.tabs(["🔑 GİRİŞ", "📝 KAYIT"])

    with t1:
        u = st.text_input("Kullanıcı")
        p = st.text_input("Şifre", type="password")
        rem = st.checkbox("Beni Hatırla")

        if st.button("GİRİŞ"):
            if (
                u in st.session_state.db
                and "password" in st.session_state.db[u]
                and st.session_state.db[u]["password"] == p
            ):
                st.session_state.user = u
                if rem:
                    with open(CONFIG_FILE, "w") as f:
                        json.dump({"user": u}, f)
                st.rerun()
            else:
                st.error("Hatalı kullanıcı veya şifre")

    with t2:
        nu = st.text_input("Yeni Kullanıcı")
        np = st.text_input("Yeni Şifre", type="password")

        if st.button("KAYIT OL"):
            if nu and nu not in st.session_state.db:
                st.session_state.db[nu] = {
                    "password": np,
                    "xp": 0,
                    "level": 1,
                    "dil": "TR",
                    "tema_rengi": "#4FACFE",
                    "habits": [],
                    "data": pd.DataFrame(columns=["Görev", "Hedef", "Yapılan"]),
                    "pomo_count": 0
                }
                veritabanini_kaydet(st.session_state.db)
                st.success("Hesap oluşturuldu")

    st.stop()

# ================== ANA ==================
u_info = st.session_state.db[st.session_state.user]

st.markdown(
    f"<style>h1,h2,h3{{color:{u_info['tema_rengi']}}}.stButton>button{{background:{u_info['tema_rengi']};color:white}}</style>",
    unsafe_allow_html=True
)

# ================== SIDEBAR ==================
st.sidebar.title("🚀 ROTA AI")
st.sidebar.metric("Rütbe", mevcut_lakap(u_info["level"], u_info["dil"]))

# -------- POMODORO --------
with st.sidebar.container(border=True):
    st.write("⏱️ **POMODORO**")

    if st.session_state.pomo_aktif:
        kalan = int(st.session_state.pomo_bitis - time.time())
        if kalan <= 0:
            st.session_state.pomo_aktif = False
            st.session_state.pomo_bitis = None
            u_info["xp"] += 50
            u_info["pomo_count"] += 1
            veritabanini_kaydet(st.session_state.db)
            st.toast("🎉 Pomodoro tamamlandı (+50 XP)")
        else:
            m, s = divmod(kalan, 60)
            st.subheader(f"`{m:02d}:{s:02d}`")
    else:
        st.subheader("`25:00`")

    c1, c2 = st.columns(2)
    if c1.button("▶️ BAŞLAT"):
        st.session_state.pomo_aktif = True
        st.session_state.pomo_bitis = time.time() + 25 * 60
        st.rerun()

    if c2.button("⏸️ DURDUR"):
        st.session_state.pomo_aktif = False
        st.session_state.pomo_bitis = None
        st.rerun()

# ================== MENÜ ==================
menu = st.sidebar.radio("MENÜ", ["🏠 Panel", "🤖 AI Mentor", "⚙️ Ayarlar"])

if st.sidebar.button("🚪 ÇIKIŞ"):
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
    st.session_state.user = None
    st.rerun()

# ================== SAYFALAR ==================
if menu == "🏠 Panel":
    st.title(f"Hoş geldin {st.session_state.user}")

    if not u_info["data"].empty:
        st.plotly_chart(
            go.Figure([
                go.Bar(x=u_info["data"]["Görev"], y=u_info["data"]["Hedef"], name="Hedef"),
                go.Bar(x=u_info["data"]["Görev"], y=u_info["data"]["Yapılan"], name="Yapılan"),
            ]),
            use_container_width=True
        )

elif menu == "🤖 AI Mentor":
    st.title("🤖 AI Mentor")
    q = st.chat_input("Sor...")
    if q:
        res = genai.GenerativeModel("gemini-1.5-flash").generate_content(q).text
        st.write(res)

elif menu == "⚙️ Ayarlar":
    st.title("⚙️ Ayarlar")
    renk = st.color_picker("Tema Rengi", u_info["tema_rengi"])
    if st.button("Kaydet"):
        u_info["tema_rengi"] = renk
        veritabanini_kaydet(st.session_state.db)
        st.rerun()