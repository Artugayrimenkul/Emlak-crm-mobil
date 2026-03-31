import streamlit as st
import pandas as pd
from supabase import create_client, Client
import json
import os
from datetime import datetime

# Ayarları yükle
def load_settings():
    # Önce Streamlit Secrets kontrol et (Cloud için)
    if "supabase_url" in st.secrets:
        return {
            "company_name": st.secrets.get("company_name", "Emlak Ofisim"),
            "supabase_url": st.secrets["supabase_url"],
            "supabase_key": st.secrets["supabase_key"]
        }
    # Yerel dosya kontrolü (Local için)
    if os.path.exists("settings.json"):
        with open("settings.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "company_name": "Emlak Ofisim",
        "supabase_url": "",
        "supabase_key": ""
    }

config = load_settings()

# Supabase Bağlantısı
if not config["supabase_url"] or not config["supabase_key"]:
    st.error("Lütfen önce bilgisayar uygulamasından Supabase URL ve Key ayarlarını yapın!")
    st.stop()

supabase: Client = create_client(config["supabase_url"], config["supabase_key"])

# Sayfa Yapılandırması
st.set_page_config(page_title=f"{config['company_name']} - Mobil Portal", page_icon="🏠")

st.title(f"🏠 {config['company_name']}")
st.subheader("Mobil İlan ve Müşteri Girişi")

menu = ["Yeni Müşteri", "Yeni Satılık Konut", "Yeni Kiralık Konut", "Yeni Satılık Arsa", "Portföy Listesi"]
choice = st.sidebar.selectbox("Menü", menu)

# --- YARDIMCI FONKSİYONLAR ---
def write_to_cloud(table_name, data):
    try:
        clean_data = {k.lower().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", ""): v for k, v in data.items()}
        if 'id' in clean_data: del clean_data['id']
        supabase.table(table_name).insert(clean_data).execute()
        st.success("Buluta başarıyla kaydedildi!")
    except Exception as e:
        st.error(f"Kayıt hatası: {e}")

# --- MENÜ İÇERİKLERİ ---

if choice == "Yeni Müşteri":
    st.header("👤 Yeni Müşteri Talebi")
    with st.form("customer_form"):
        name = st.text_input("Ad Soyad")
        phone = st.text_input("Telefon (90...)")
        email = st.text_input("E-posta")
        demand = st.selectbox("Talep Türü", ["Satılık Konut", "Kiralık Konut", "Satılık Arsa"])
        budget = st.text_input("Bütçe")
        region1 = st.text_input("Bölge 1")
        region2 = st.text_input("Bölge 2")
        region3 = st.text_input("Bölge 3")
        urgency = st.selectbox("Aciliyet", ["Acil", "Normal", "Belirtmedi"])
        notes = st.text_area("Notlar")
        
        if st.form_submit_button("Kaydet"):
            data = {
                "tarih": datetime.now().strftime("%d.%m.%Y"),
                "ad_soyad": name,
                "telefon": phone,
                "e_posta": email,
                "talep_türü": demand,
                "bütçe": budget,
                "bölge_1": region1,
                "bölge_2": region2,
                "bölge_3": region3,
                "aciliyet": urgency,
                "notlar": notes
            }
            write_to_cloud("customers", data)

elif choice == "Yeni Satılık Konut":
    st.header("💰 Yeni Satılık Konut")
    with st.form("sk_form"):
        ilan_no = st.text_input("İlan No")
        tip = st.selectbox("Konut Tipi", ["Daire", "Villa", "Rezidans"])
        fiyat = st.text_input("Fiyat")
        bolge = st.text_input("Bölge/Mahalle")
        oda = st.selectbox("Oda Sayısı", ["1+1", "2+1", "3+1", "4+1", "5+1"])
        kat = st.text_input("Kat")
        sahibi = st.text_input("Mülk Sahibi")
        sahibi_tel = st.text_input("Sahibi Tel")
        notlar = st.text_area("Notlar")
        
        if st.form_submit_button("Kaydet"):
            data = {
                "tarih": datetime.now().strftime("%d.%m.%Y"),
                "ilan_no": ilan_no,
                "konut_tipi": tip,
                "fiyat": fiyat,
                "bölge_mahalle": bolge,
                "oda_sayısı": oda,
                "kat": kat,
                "sahibi": sahibi,
                "sahibi_tel": sahibi_tel,
                "notlar": notlar
            }
            write_to_cloud("satilik_konut", data)

elif choice == "Yeni Kiralık Konut":
    st.header("🔑 Yeni Kiralık Konut")
    with st.form("kk_form"):
        ilan_no = st.text_input("İlan No")
        tip = st.selectbox("Konut Tipi", ["Daire", "Villa", "Rezidans"])
        fiyat = st.text_input("Kira Bedeli")
        bolge = st.text_input("Bölge/Mahalle")
        oda = st.selectbox("Oda Sayısı", ["1+1", "2+1", "3+1", "4+1", "5+1"])
        kat = st.text_input("Kat")
        sahibi = st.text_input("Mülk Sahibi")
        sahibi_tel = st.text_input("Sahibi Tel")
        notlar = st.text_area("Notlar")
        
        if st.form_submit_button("Kaydet"):
            data = {
                "tarih": datetime.now().strftime("%d.%m.%Y"),
                "ilan_no": ilan_no,
                "konut_tipi": tip,
                "fiyat": fiyat,
                "bölge_mahalle": bolge,
                "oda_sayısı": oda,
                "kat": kat,
                "sahibi": sahibi,
                "sahibi_tel": sahibi_tel,
                "notlar": notlar
            }
            write_to_cloud("kiralik_konut", data)

elif choice == "Yeni Satılık Arsa":
    st.header("🌳 Yeni Satılık Arsa")
    with st.form("sa_form"):
        ilan_no = st.text_input("İlan No")
        tip = st.selectbox("Arsa Tipi", ["İmarlı", "Tarla", "Zeytinlik"])
        ada = st.text_input("Ada")
        parsel = st.text_input("Parsel")
        fiyat = st.text_input("Fiyat")
        bolge = st.text_input("Bölge/Mahalle")
        sahibi = st.text_input("Mülk Sahibi")
        sahibi_tel = st.text_input("Sahibi Tel")
        notlar = st.text_area("Notlar")
        
        if st.form_submit_button("Kaydet"):
            data = {
                "tarih": datetime.now().strftime("%d.%m.%Y"),
                "ilan_no": ilan_no,
                "arsa_tipi": tip,
                "ada": ada,
                "parsel": parsel,
                "fiyat": fiyat,
                "bölge_mahalle": bolge,
                "sahibi": sahibi,
                "sahibi_tel": sahibi_tel,
                "notlar": notlar
            }
            write_to_cloud("satilik_arsa", data)

elif choice == "Portföy Listesi":
    st.header("📋 Güncel Portföyler")
    tab1, tab2, tab3 = st.tabs(["Satılık Konut", "Kiralık Konut", "Satılık Arsa"])
    
    with tab1:
        res = supabase.table("satilik_konut").select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            st.dataframe(df[["ilan_no", "bölge_mahalle", "fiyat", "oda_sayısı"]])
        else: st.info("Kayıt bulunamadı.")
            
    with tab2:
        res = supabase.table("kiralik_konut").select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            st.dataframe(df[["ilan_no", "bölge_mahalle", "fiyat", "oda_sayısı"]])
        else: st.info("Kayıt bulunamadı.")
            
    with tab3:
        res = supabase.table("satilik_arsa").select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            st.dataframe(df[["ilan_no", "bölge_mahalle", "fiyat", "ada", "parsel"]])
        else: st.info("Kayıt bulunamadı.")
