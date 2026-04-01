import streamlit as st
import pandas as pd
from supabase import create_client, Client
import json
import os
from datetime import datetime
import io

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
    return {"company_name": "Emlak Ofisim", "supabase_url": "", "supabase_key": ""}

config = load_settings()

# Supabase Bağlantısı
if not config["supabase_url"] or not config["supabase_key"]:
    st.error("Lütfen önce bilgisayar uygulamasından Supabase URL ve Key ayarlarını yapın!")
    st.stop()

supabase: Client = create_client(config["supabase_url"], config["supabase_key"])

# Sayfa Yapılandırması
st.set_page_config(page_title=f"{config['company_name']} - Mobil Portal", page_icon="🏠", layout="wide")

st.title(f"🏠 {config['company_name']}")
st.subheader("Mobil Yönetim Paneli")

menu = ["Yeni Müşteri", "Müşteri Listesi", "Yeni Satılık Konut", "Yeni Kiralık Konut", "Yeni Satılık Arsa", "Portföy Listesi", "Akıllı Eşleştirme"]
choice = st.sidebar.selectbox("Menü", menu)

# --- YARDIMCI FONKSİYONLAR ---
def upload_image(file, ilan_no):
    try:
        if file:
            file_ext = file.name.split(".")[-1]
            file_name = f"{ilan_no}.{file_ext}"
            # portfolio_images bucket'ına yükle
            res = supabase.storage.from_("portfolio_images").upload(
                path=file_name,
                file=file.getvalue(),
                file_options={"content-type": f"image/{file_ext}", "upsert": "true"}
            )
            return file_name
    except Exception as e:
        st.error(f"Resim yükleme hatası: {e}")
    return None

def get_image_url(file_name):
    if file_name:
        return f"{config['supabase_url']}/storage/v1/object/public/portfolio_images/{file_name}"
    return None

def write_to_cloud(table_name, data, image_file=None):
    try:
        clean_data = {k.lower().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", ""): v for k, v in data.items()}
        
        # Eğer resim yüklendiyse
        if image_file and 'ilan_no' in clean_data:
            img_name = upload_image(image_file, clean_data['ilan_no'])
            if img_name:
                clean_data['resim_url'] = img_name
            
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
        
        if st.form_submit_button("Müşteriyi Kaydet"):
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

elif choice == "Müşteri Listesi":
    st.header("👥 Müşteri Listesi")
    res = supabase.table("customers").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        for _, row in df.iterrows():
            with st.expander(f"{row['ad_soyad']} - {row['talep_türü']}"):
                st.write(f"📞 Telefon: {row['telefon']}")
                st.write(f"💰 Bütçe: {row['bütçe']}")
                st.write(f"📍 Bölgeler: {row['bölge_1']}, {row['bölge_2']}, {row['bölge_3']}")
                st.write(f"📝 Notlar: {row['notlar']}")
                st.link_button("WhatsApp'tan Yaz", f"https://wa.me/{row['telefon']}", type="primary")
    else:
        st.info("Müşteri kaydı bulunamadı.")

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
        
        img = st.file_uploader("İlan Resmi Seç (Kamera veya Galeri)", type=["jpg", "png", "jpeg"])
        
        if st.form_submit_button("İlanı Kaydet"):
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
            write_to_cloud("satilik_konut", data, img)

elif choice == "Yeni Kiralık Konut":
    st.header("🔑 Yeni Kiralık Konut")
    with st.form("kk_form"):
        ilan_no = st.text_input("İlan No")
        tip = st.selectbox("Konut Tipi", ["Daire", "Villa", "Rezidans"])
        fiyat = st.text_input("Kira Bedeli")
        bolge = st.text_input("Bölge/Mahalle")
        oda = st.selectbox("Oda Sayısı", ["1+1", "2+1",
