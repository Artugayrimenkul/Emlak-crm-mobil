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
            # Mevcut dosyayı sil (varsa) ve yenisini yükle
            try:
                supabase.storage.from_("portfolio_images").remove([file_name])
            except Exception:
                pass # Dosya yoksa hata vermesini engelle
            
            supabase.storage.from_("portfolio_images").upload(
                path=file_name, file=file.getvalue(), file_options={"content-type": f"image/{file_ext}"}
            )
            return file_name
    except Exception as e:
        st.error(f"Resim yükleme hatası: {e}")
    return None

def get_image_url(file_name):
    if file_name:
        # URL'ye zaman damgası ekleyerek cache sorununu önle
        return f"{config['supabase_url']}/storage/v1/object/public/portfolio_images/{file_name}?t={datetime.now().timestamp()}"
    return None

def write_to_cloud(table_name, data, image_file=None, is_update=False, record_id=None):
    try:
        clean_data = {k.lower().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", ""): v for k, v in data.items()}
        
        ilan_no_for_image = data.get('ilan_no') # Orjinal dict'ten al
        if image_file and ilan_no_for_image:
            img_name = upload_image(image_file, ilan_no_for_image)
            if img_name:
                clean_data['resim_url'] = img_name
        
        if is_update:
            if 'ilan_no' in clean_data: del clean_data['ilan_no']
            supabase.table(table_name).update(clean_data).eq("id", record_id).execute()
            st.success("Kayıt başarıyla güncellendi!")
        else:
            if 'id' in clean_data: del clean_data['id']
            supabase.table(table_name).insert(clean_data).execute()
            st.success("Buluta başarıyla kaydedildi!")
        st.rerun()
    except Exception as e:
        st.error(f"Kayıt hatası: {e}")

# --- MENÜ İÇERİKLERİ ---
# (Diğer menü içerikleri önceki kodla aynı, buraya eklenmedi)
# ...

# Portföy Listesi ve Düzenleme
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
            img = st.file_uploader("Yeni Resim Yükle", type=["jpg", "png", "jpeg"])
            
            updates = {}
            if table_name in ["satilik_konut", "kiralik_konut"]:
                updates['konut_tipi'] = st.selectbox("Konut Tipi", ["Daire", "Villa", "Rezidans"], index=["Daire", "Villa", "Rezidans"].index(record_data.get('konut_tipi', 'Daire')))
                updates['oda_sayısı'] = st.selectbox("Oda Sayısı", ["1+1", "2+1", "3+1", "4+1", "5+1"], index=["1+1", "2+1", "3+1", "4+1", "5+1"].index(record_data.get('oda_sayısı', '1+1')))
                updates['kat'] = st.text_input("Kat", value=record_data.get('kat', ''))
            elif table_name == "satilik_arsa":
                updates['arsa_tipi'] = st.selectbox("Arsa Tipi", ["İmarlı", "Tarla", "Zeytinlik"], index=["İmarlı", "Tarla", "Zeytinlik"].index(record_data.get('arsa_tipi', 'İmarlı')))
                updates['ada'] = st.text_input("Ada", value=record_data.get('ada', ''))
                updates['parsel'] = st.text_input("Parsel", value=record_data.get('parsel', ''))

            if st.form_submit_button("İlanı Güncelle"):
                final_data = {"fiyat": fiyat, "bölge_mahalle": bolge, "sahibi": sahibi, "sahibi_tel": sahibi_tel, "notlar": notlar, "ilan_no": record_data['ilan_no']}
                final_data.update(updates)
                write_to_cloud(table_name, final_data, image_file=img, is_update=True, record_id=record_id)
                del st.session_state.editing_portfolio
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

# Diğer menüler (Akıllı Eşleştirme vb.) buraya eklenebilir...
