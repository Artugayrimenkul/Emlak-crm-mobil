import streamlit as st
import pandas as pd
from supabase import create_client, Client
import json
import os
from datetime import datetime
import io

# Ayarları yükle
def load_settings():
    if "supabase_url" in st.secrets:
        return {
            "company_name": st.secrets.get("company_name", "Emlak Ofisim"),
            "supabase_url": st.secrets["supabase_url"],
            "supabase_key": st.secrets["supabase_key"]
        }
    if os.path.exists("settings.json"):
        with open("settings.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {"company_name": "Emlak Ofisim", "supabase_url": "", "supabase_key": ""}

config = load_settings()
supabase: Client = create_client(config["supabase_url"], config["supabase_key"])

# Sayfa Yapılandırması
st.set_page_config(page_title=f"{config.get('company_name', 'Emlak Ofisim')} - Mobil Portal", page_icon="🏠", layout="wide")

st.title(f"🏠 {config.get('company_name', 'Emlak Ofisim')}")
st.subheader("Mobil Yönetim Paneli")

menu = ["Yeni Müşteri", "Müşteri Listesi", "Yeni Satılık Konut", "Yeni Kiralık Konut", "Yeni Satılık Arsa", "Portföy Listesi", "Akıllı Eşleştirme"]
choice = st.sidebar.selectbox("Menü", menu)

# --- YARDIMCI FONKSİYONLAR ---
def upload_image(file, ilan_no):
    try:
        if file:
            file_ext = file.name.split(".")[-1]
            file_name = f"{ilan_no}.{file_ext}"
            supabase.storage.from_("portfolio_images").upload(
                path=file_name, file=file.getvalue(), file_options={"content-type": f"image/{file_ext}", "upsert": "true"}
            )
            return file_name
    except Exception as e:
        st.error(f"Resim yükleme hatası: {e}")
    return None

def get_image_url(file_name):
    if file_name:
        return f"{config['supabase_url']}/storage/v1/object/public/portfolio_images/{file_name}"
    return None

def write_to_cloud(table_name, data, image_file=None, is_update=False, record_id=None):
    try:
        clean_data = {k.lower().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", ""): v for k, v in data.items()}
        if image_file and 'ilan_no' in clean_data:
            img_name = upload_image(image_file, clean_data['ilan_no'])
            if img_name: clean_data['resim_url'] = img_name
        
        if is_update:
            supabase.table(table_name).update(clean_data).eq("id", record_id).execute()
            st.success("Kayıt başarıyla güncellendi!")
        else:
            if 'id' in clean_data: del clean_data['id']
            supabase.table(table_name).insert(clean_data).execute()
            st.success("Buluta başarıyla kaydedildi!")
    except Exception as e:
        st.error(f"Kayıt hatası: {e}")

# --- MENÜ İÇERİKLERİ ---

if choice == "Yeni Müşteri":
    st.header("👤 Yeni Müşteri Talebi")
    with st.form("customer_form"):
        # ... (Müşteri formu aynı kalabilir)
        name = st.text_input("Ad Soyad")
        phone = st.text_input("Telefon (90...)")
        # ...
        if st.form_submit_button("Müşteriyi Kaydet"):
            # ...
            pass

elif choice == "Müşteri Listesi":
    st.header("👥 Müşteri Yönetimi")
    # ... (Müşteri listesi ve düzenleme aynı kalabilir)
    pass

elif choice == "Yeni Satılık Konut":
    st.header("💰 Yeni Satılık Konut")
    with st.form("sk_form"):
        # ... (İlan formu aynı kalabilir)
        ilan_no = st.text_input("İlan No")
        # ...
        img = st.file_uploader("İlan Resmi Seç", type=["jpg", "png", "jpeg"])
        if st.form_submit_button("İlanı Kaydet"):
            # ...
            pass

# Diğer ilan ekleme formları (Kiralık, Arsa) buraya eklenebilir...

elif choice == "Portföy Listesi":
    st.header("📋 Portföy Yönetimi")
    if 'editing_portfolio' in st.session_state and st.session_state.editing_portfolio is not None:
        edit_info = st.session_state.editing_portfolio
        table_name = edit_info['table']
        record_id = edit_info['id']
        res = supabase.table(table_name).select("*").eq("id", record_id).single().execute()
        record_data = res.data
        st.header(f"✍️ {record_data['ilan_no']} Nolu İlanı Düzenle")
        with st.form(key="edit_portfolio_form"):
            fiyat = st.text_input("Fiyat", value=record_data.get('fiyat', ''))
            bolge = st.text_input("Bölge/Mahalle", value=record_data.get('bölge_mahalle', ''))
            sahibi = st.text_input("Mülk Sahibi", value=record_data.get('sahibi', ''))
            sahibi_tel = st.text_input("Sahibi Tel", value=record_data.get('sahibi_tel', ''))
            notlar = st.text_area("Notlar", value=record_data.get('notlar', ''))
            
            # Resim yükleme alanı
            img = st.file_uploader("Yeni Resim Yükle (Mevcut resmi değiştirir)", type=["jpg", "png", "jpeg"])

            if table_name in ["satilik_konut", "kiralik_konut"]:
                tip = st.selectbox("Konut Tipi", ["Daire", "Villa", "Rezidans"], index=["Daire", "Villa", "Rezidans"].index(record_data.get('konut_tipi', 'Daire')))
                oda = st.selectbox("Oda Sayısı", ["1+1", "2+1", "3+1", "4+1", "5+1"], index=["1+1", "2+1", "3+1", "4+1", "5+1"].index(record_data.get('oda_sayısı', '1+1')))
                kat = st.text_input("Kat", value=record_data.get('kat', ''))
            
            if st.form_submit_button("İlanı Güncelle"):
                updated_data = {"fiyat": fiyat, "bölge_mahalle": bolge, "sahibi": sahibi, "sahibi_tel": sahibi_tel, "notlar": notlar, "ilan_no": record_data['ilan_no']}
                if table_name in ["satilik_konut", "kiralik_konut"]: updated_data.update({"konut_tipi": tip, "oda_sayısı": oda, "kat": kat})
                
                write_to_cloud(table_name, updated_data, image_file=img, is_update=True, record_id=record_id)
                
                del st.session_state.editing_portfolio
                st.rerun()
        if st.button("İptal"):
            del st.session_state.editing_portfolio
            st.rerun()
    else:
        t1, t2, t3 = st.tabs(["Satılık Konut", "Kiralık Konut", "Satılık Arsa"])
        def show_portfolio(table_name):
            res = supabase.table(table_name).select("*").execute()
            if res.data:
                for row in res.data:
                    with st.container(border=True):
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            img_url = get_image_url(row.get('resim_url'))
                            if img_url: st.image(img_url, use_container_width=True)
                            else: st.info("Resim yok")
                        with col2:
                            st.write(f"**İlan No: {row['ilan_no']}** | {row['bölge_mahalle']}")
                            st.write(f"💰 {row.get('fiyat', '')} TL")
                            c1, c2 = st.columns(2)
                            with c1: 
                                if st.button("✍️ Düzenle", key=f"edit_port_{table_name}_{row['id']}", use_container_width=True):
                                    st.session_state.editing_portfolio = {'table': table_name, 'id': row['id']}
                                    st.rerun()
                            with c2:
                                if st.button("🗑️ Sil", key=f"del_port_{table_name}_{row['id']}", type="primary", use_container_width=True):
                                    supabase.table(table_name).delete().eq("id", row['id']).execute()
                                    st.success(f"{row['ilan_no']} nolu ilan silindi.")
                                    st.rerun()
            else: st.info("Kayıt bulunamadı.")
        with t1: show_portfolio("satilik_konut")
        with t2: show_portfolio("kiralik_konut")
        with t3: show_portfolio("satilik_arsa")

elif choice == "Akıllı Eşleştirme":
    st.header("🎯 Akıllı Eşleştirme")
    # ... (Mevcut kod aynı kalabilir)
