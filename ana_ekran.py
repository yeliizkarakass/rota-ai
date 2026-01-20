import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
import json, os, time
import google.generativeai as genai

# ----------------- AYAR -----------------
st.set_page_config("ROTA AI PRO", "🚀", layout="wide")
DB_FILE = "rota_database.json"
CONFIG_FILE = "user_config.json"

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# ----------------- DİL -----------------
DIL = {
    "TR": {
        "menu": ["🏠 Panel","📊 Alışkanlıklar","📅 Sınavlar","⏱️ Odak","🎓 Akademik","🤖 AI Mentor","🏆 Başarılar","⚙️ Ayarlar"]
    },
    "EN": {
        "menu": ["🏠 Dashboard","📊 Habits","📅 Exams","⏱️ Focus","🎓 Academic","🤖 AI Mentor","🏆 Achievements","⚙️ Settings"]
    }
}

# ----------------- DB -----------------
def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE,"r",encoding="utf-8") as f:
        db = json.load(f)
    for u in db:
        db[u].setdefault("password","")
        db[u].setdefault("xp",0)
        db[u].setdefault("level",1)
        db[u].setdefault("dil","TR")
        db[u].setdefault("tema","#4FACFE")
        db[u].setdefault("habits",[])
        db[u].setdefault("sinavlar",[])
        db[u].setdefault("mevcut_gano",0.0)
        db[u].setdefault("pomo",0)
        db[u].setdefault("data",[])
        db[u]["data"] = pd.DataFrame(db[u]["data"])
    return db

def save_db(db):
    out={}
    for u in db:
        t=db[u].copy()
        t["data"]=t["data"].to_dict("records")
        out[u]=t
    with open(DB_FILE,"w",encoding="utf-8") as f:
        json.dump(out,f,ensure_ascii=False,indent=2)

# ----------------- SESSION -----------------
if "db" not in st.session_state:
    st.session_state.db = load_db()
if "user" not in st.session_state:
    st.session_state.user = None
if "pomo_on" not in st.session_state:
    st.session_state.pomo_on = False
if "pomo_end" not in st.session_state:
    st.session_state.pomo_end = None

# ----------------- AUTO LOGIN -----------------
if st.session_state.user is None and os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE) as f:
            u=json.load(f).get("user")
            if u in st.session_state.db:
                st.session_state.user=u
    except: pass

# ----------------- LOGIN -----------------
if st.session_state.user is None:
    st.title("🚀 ROTA AI")
    t1,t2=st.tabs(["GİRİŞ","KAYIT"])

    with t1:
        u=st.text_input("Kullanıcı")
        p=st.text_input("Şifre",type="password")
        rem=st.checkbox("Beni Hatırla")
        if st.button("GİR"):
            if u in st.session_state.db and st.session_state.db[u]["password"]==p:
                st.session_state.user=u
                if rem:
                    with open(CONFIG_FILE,"w") as f:
                        json.dump({"user":u},f)
                st.rerun()
            else:
                st.error("Hatalı")

    with t2:
        nu=st.text_input("Yeni Kullanıcı")
        np=st.text_input("Yeni Şifre",type="password")
        if st.button("OLUŞTUR"):
            if nu and np and nu not in st.session_state.db:
                st.session_state.db[nu]={
                    "password":np,
                    "xp":0,"level":1,"dil":"TR","tema":"#4FACFE",
                    "habits":[],"sinavlar":[],"mevcut_gano":0.0,
                    "pomo":0,"data":pd.DataFrame(columns=["Gün","Görev","Hedef","Yapılan"])
                }
                save_db(st.session_state.db)
                st.success("Oluşturuldu")

    st.stop()

# ----------------- APP -----------------
uinfo = st.session_state.db[st.session_state.user]
L = DIL[uinfo["dil"]]

st.markdown(
    f"<style>h1,h2,h3{{color:{uinfo['tema']}}}.stButton>button{{background:{uinfo['tema']};color:white}}</style>",
    unsafe_allow_html=True
)

# ----------------- SIDEBAR -----------------
st.sidebar.title("🚀 ROTA AI")

# POMODORO
with st.sidebar.container(border=True):
    if st.session_state.pomo_on:
        kalan=int(st.session_state.pomo_end-time.time())
        if kalan<=0:
            st.session_state.pomo_on=False
            uinfo["xp"]+=50
            uinfo["pomo"]+=1
            save_db(st.session_state.db)
            st.toast("Pomodoro bitti")
        else:
            m,s=divmod(kalan,60)
            st.write(f"⏱️ {m:02d}:{s:02d}")
    else:
        st.write("⏱️ 25:00")

    if st.button("▶️"):
        st.session_state.pomo_on=True
        st.session_state.pomo_end=time.time()+25*60
        st.rerun()
    if st.button("⏸️"):
        st.session_state.pomo_on=False
        st.rerun()

menu = st.sidebar.radio("MENÜ",L["menu"])

if st.sidebar.button("🚪 ÇIKIŞ"):
    if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)
    st.session_state.user=None
    st.rerun()

# ----------------- SAYFALAR -----------------
if menu in ["🏠 Panel","🏠 Dashboard"]:
    st.title("🏠 PANEL")
    if not uinfo["data"].empty:
        st.plotly_chart(go.Figure([
            go.Bar(x=uinfo["data"]["Görev"],y=uinfo["data"]["Hedef"],name="Hedef"),
            go.Bar(x=uinfo["data"]["Görev"],y=uinfo["data"]["Yapılan"],name="Yapılan")
        ]),use_container_width=True)

    with st.form("add"):
        g=st.text_input("Görev")
        h=st.number_input("Hedef",1)
        d=st.selectbox("Gün",["Pzt","Sal","Çar","Per","Cum","Cmt","Paz"])
        if st.form_submit_button("Ekle"):
            uinfo["data"]=pd.concat([uinfo["data"],pd.DataFrame([{
                "Gün":d,"Görev":g,"Hedef":h,"Yapılan":0
            }])],ignore_index=True)
            save_db(st.session_state.db)
            st.rerun()

elif menu in ["📊 Alışkanlıklar","📊 Habits"]:
    df=pd.DataFrame(uinfo["habits"],columns=["Alışkanlık","Pzt","Sal","Çar","Per","Cum","Cmt","Paz"])
    ed=st.data_editor(df,num_rows="dynamic",use_container_width=True)
    if not df.equals(ed):
        uinfo["habits"]=ed.to_dict("records")
        save_db(st.session_state.db)

elif menu in ["📅 Sınavlar","📅 Exams"]:
    with st.form("sinav"):
        ad=st.text_input("Ders")
        tar=st.date_input("Tarih")
        if st.form_submit_button("Ekle"):
            uinfo["sinavlar"].append({"ders":ad,"tarih":str(tar)})
            save_db(st.session_state.db)
    for s in uinfo["sinavlar"]:
        kalan=(datetime.fromisoformat(s["tarih"])-datetime.now()).days
        st.info(f"{s['ders']} → {kalan} gün")

elif menu in ["🎓 Akademik","🎓 Academic"]:
    g=st.number_input("Mevcut GNO",0.0,4.0,value=float(uinfo["mevcut_gano"]))
    if st.button("Kaydet"):
        uinfo["mevcut_gano"]=g
        save_db(st.session_state.db)

elif menu=="🤖 AI Mentor":
    if st.button("Analiz"):
        r=genai.GenerativeModel("gemini-1.5-flash").generate_content(
            uinfo["data"].to_string()
        ).text
        st.markdown(r)
    q=st.chat_input("Sor")
    if q:
        st.write(genai.GenerativeModel("gemini-1.5-flash").generate_content(q).text)

elif menu in ["🏆 Başarılar","🏆 Achievements"]:
    st.metric("XP",uinfo["xp"])
    st.metric("Pomodoro",uinfo["pomo"])

elif menu in ["⚙️ Ayarlar","⚙️ Settings"]:
    c=st.color_picker("Tema",uinfo["tema"])
    if st.button("Uygula"):
        uinfo["tema"]=c
        save_db(st.session_state.db)
        st.rerun()