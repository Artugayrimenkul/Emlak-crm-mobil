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

menu = ["Yeni İlan", "Portföy Yönetimi", "Yeni Müşteri", "Müşteri Yönetimi", "Akıllı Eşleştirme"]
choice = st.sidebar.selectbox("Menü", menu)

# --- YARDIMCI FONKSİYONLAR ---
def upload_images(files, ilan_no):
    urls = []
    for i, file in enumerate(files):
        try:
            file_ext = file.name.split(".")[-1]
            file_name = f"{ilan_no}_{int(datetime.now().timestamp())}_{i}.{file_ext}"
            supabase.storage.from_("portfolio_images").upload(
                path=file_name, file=file.getvalue(), file_options={"content-type": f"image/{file_ext}"}
            )
            urls.append(file_name)
        except Exception as e:
            st.error(f"Resim yükleme hatası ({file.name}): {e}")
    return urls

def get_image_url(file_name):
    if file_name:
        return f"{config['supabase_url']}/storage/v1/object/public/portfolio_images/{file_name}"
    return None

def delete_image(file_name):
    try:
        supabase.storage.from_("portfolio_images").remove([file_name])
        return True
    except Exception as e:
        st.error(f"Resim silme hatası: {e}")
        return False

# --- İLAN YÖNETİMİ ---
def portfolio_form(table_name, record_data=None):
    is_update = record_data is not None
    st.header(f"✍️ {record_data['ilan_no']} Düzenle" if is_update else f"➕ Yeni {table_name.replace('_', ' ').title()}")

    with st.form(key="portfolio_form"):
        ilan_no = st.text_input("İlan No", value=record_data.get('ilan_no', ''), disabled=is_update)
        fiyat = st.text_input("Fiyat", value=record_data.get('fiyat', ''))
        bolge = st.text_input("Bölge/Mahalle", value=record_data.get('bölge_mahalle', ''))
        sahibi = st.text_input("Mülk Sahibi", value=record_data.get('sahibi', ''))
        sahibi_tel = st.text_input("Sahibi Tel", value=record_data.get('sahibi_tel', ''))
        notlar = st.text_area("Notlar", value=record_data.get('notlar', ''))
        
        updates = {}
        if table_name in ["satilik_konut", "kiralik_konut"]:
            updates['konut_tipi'] = st.selectbox("Konut Tipi", ["Daire", "Villa", "Rezidans"], index=["Daire", "Villa", "Rezidans"].index(record_data.get('konut_tipi', 'Daire')))
            updates['oda_sayısı'] = st.selectbox("Oda Sayısı", ["1+1", "2+1", "3+1", "4+1", "5+1"], index=["1+1", "2+1", "3+1", "4+1", "5+1"].index(record_data.get('oda_sayısı', '1+1')))
            updates['kat'] = st.text_input("Kat", value=record_data.get('kat', ''))
        elif table_name == "satilik_arsa":
            updates['arsa_tipi'] = st.selectbox("Arsa Tipi", ["İmarlı", "Tarla", "Zeytinlik"], index=["İmarlı", "Tarla", "Zeytinlik"].index(record_data.get('arsa_tipi', 'İmarlı')))
            updates['ada'] = st.text_input("Ada", value=record_data.get('ada', ''))
            updates['parsel'] = st.text_input("Parsel", value=record_data.get('parsel', ''))

        new_images = st.file_uploader("Yeni Resimler Ekle", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        
        submitted = st.form_submit_button("Kaydet" if not is_update else "Güncelle")
        if submitted:
            if not is_update and not ilan_no:
                st.error("Yeni ilanlar için İlan No zorunludur!")
                return

            final_data = {"fiyat": fiyat, "bölge_mahalle": bolge, "sahibi": sahibi, "sahibi_tel": sahibi_tel, "notlar": notlar}
            final_data.update(updates)
            
            current_images = record_data.get('image_urls', []) if is_update else []
            
            if new_images:
                uploaded_urls = upload_images(new_images, ilan_no if not is_update else record_data['ilan_no'])
                current_images.extend(uploaded_urls)
            
            final_data['image_urls'] = current_images

            if is_update:
                supabase.table(table_name).update(final_data).eq("id", record_data['id']).execute()
                st.success("İlan güncellendi!")
            else:
                final_data['ilan_no'] = ilan_no
                supabase.table(table_name).insert(final_data).execute()
                st.success("İlan kaydedildi!")
            
            st.session_state.editing_portfolio = None
            st.rerun()

    if is_update:
        st.subheader("Mevcut Resimler")
        current_images = record_data.get('image_urls', [])
        if not current_images:
            st.info("Bu ilana ait resim bulunmuyor.")
        else:
            for img_name in current_images:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.image(get_image_url(img_name))
                with col2:
                    if st.button("🗑️ Sil", key=f"del_img_{img_name}"):
                        if delete_image(img_name):
                            current_images.remove(img_name)
                            supabase.table(table_name).update({'image_urls': current_images}).eq("id", record_data['id']).execute()
                            st.success("Resim silindi!")
                            st.rerun()
        if st.button("Geri Dön"):
            st.session_state.editing_portfolio = None
            st.rerun()

if choice == "Yeni İlan":
    ilan_tipi = st.selectbox("Hangi tip ilan eklemek istersiniz?", ["Satılık Konut", "Kiralık Konut", "Satılık Arsa"])
    table_map = {"Satılık Konut": "satilik_konut", "Kiralık Konut": "kiralik_konut", "Satılık Arsa": "satilik_arsa"}
    portfolio_form(table_map[ilan_tipi])

elif choice == "Portföy Yönetimi":
    if 'editing_portfolio' in st.session_state and st.session_state.editing_portfolio:
        portfolio_form(st.session_state.editing_portfolio['table'], st.session_state.editing_portfolio['data'])
    else:
        st.header("📋 Portföy Yönetimi")
        t1, t2, t3 = st.tabs(["Satılık Konut", "Kiralık Konut", "Satılık Arsa"])
        def show_portfolio(table_name):
            res = supabase.table(table_name).select("*").execute()
            if res.data:
                for row in res.data:
                    with st.container(border=True):
                        st.write(f"**İlan No: {row['ilan_no']}** | {row['bölge_mahalle']} | 💰 {row.get('fiyat', '')} TL")
                        
                        image_urls = row.get('image_urls', [])
                        if image_urls:
                            st.image(get_image_url(image_urls[0]), width=150)
                        
                        c1, c2 = st.columns(2)
                        with c1: 
                            if st.button("✍️ Yönet", key=f"edit_{table_name}_{row['id']}", use_container_width=True):
                                st.session_state.editing_portfolio = {'table': table_name, 'data': row}
                                st.rerun()
                        with c2:
                            if st.button("🗑️ Sil", key=f"del_{table_name}_{row['id']}", type="primary", use_container_width=True):
                                if row.get('image_urls'):
                                    for img in row['image_urls']: delete_image(img)
                                supabase.table(table_name).delete().eq("id", row['id']).execute()
                                st.success(f"{row['ilan_no']} nolu ilan silindi.")
                                st.rerun()
            else: st.info("Kayıt bulunamadı.")
        with t1: show_portfolio("satilik_konut")
        with t2: show_portfolio("kiralik_konut")
        with t3: show_portfolio("satilik_arsa")

elif choice == "Yeni Müşteri":
    st.header("👤 Yeni Müşteri Talebi")
    with st.form("customer_form"):
        name = st.text_input("Ad Soyad")
        phone = st.text_input("Telefon (90...)")
        email = st.text_input("E-posta")
        demand = st.selectbox("Talep Türü", ["Satılık Konut", "Kiralık Konut", "Satılık Arsa"])
        budget = st.text_input("Bütçe")
        region1 = st.text_input("Bölge 1"); region2 = st.text_input("Bölge 2"); region3 = st.text_input("Bölge 3")
        urgency = st.selectbox("Aciliyet", ["Acil", "Normal", "Belirtmedi"])
        notes = st.text_area("Notlar")
        if st.form_submit_button("Müşteriyi Kaydet"):
            data = {"tarih": datetime.now().strftime("%d.%m.%Y"), "ad_soyad": name, "telefon": phone, "e_posta": email, "talep_türü": demand, "bütçe": budget, "bölge_1": region1, "bölge_2": region2, "bölge_3": region3, "aciliyet": urgency, "notlar": notes}
            supabase.table("customers").insert(data).execute()
            st.success("Müşteri kaydedildi!")

elif choice == "Müşteri Yönetimi":
    st.header("👥 Müşteri Yönetimi")
    if 'editing_customer_id' in st.session_state and st.session_state.editing_customer_id:
        customer_id = st.session_state.editing_customer_id
        res = supabase.table("customers").select("*").eq("id", customer_id).single().execute()
        customer_data = res.data
        st.header(f"✍️ {customer_data['ad_soyad']} Düzenle")
        with st.form(key="edit_customer_form"):
            name = st.text_input("Ad Soyad", value=customer_data.get('ad_soyad', ''))
            phone = st.text_input("Telefon", value=customer_data.get('telefon', ''))
            email = st.text_input("E-posta", value=customer_data.get('e_posta', ''))
            demand = st.selectbox("Talep Türü", ["Satılık Konut", "Kiralık Konut", "Satılık Arsa"], index=["Satılık Konut", "Kiralık Konut", "Satılık Arsa"].index(customer_data.get('talep_türü', 'Satılık Konut')))
            budget = st.text_input("Bütçe", value=customer_data.get('bütçe', ''))
            region1 = st.text_input("Bölge 1", value=customer_data.get('bölge_1', '')); region2 = st.text_input("Bölge 2", value=customer_data.get('bölge_2', '')); region3 = st.text_input("Bölge 3", value=customer_data.get('bölge_3', ''))
            urgency = st.selectbox("Aciliyet", ["Acil", "Normal", "Belirtmedi"], index=["Acil", "Normal", "Belirtmedi"].index(customer_data.get('aciliyet', 'Normal')))
            notes = st.text_area("Notlar", value=customer_data.get('notlar', ''))
            if st.form_submit_button("Müşteriyi Güncelle"):
                updated_data = {"ad_soyad": name, "telefon": phone, "e_posta": email, "talep_türü": demand, "bütçe": budget, "bölge_1": region1, "bölge_2": region2, "bölge_3": region3, "aciliyet": urgency, "notlar": notes}
                supabase.table("customers").update(updated_data).eq("id", customer_id).execute()
                st.success("Müşteri güncellendi!")
                del st.session_state.editing_customer_id
                st.rerun()
        if st.button("İptal"):
            del st.session_state.editing_customer_id
            st.rerun()
    else:
        res = supabase.table("customers").select("*").execute()
        if res.data:
            for row in res.data:
                with st.expander(f"{row['ad_soyad']} - {row['talep_türü']}"):
                    st.write(f"📞 {row['telefon']} | 💰 {row['bütçe']} | 📍 {row['bölge_1']}")
                    c1, c2, c3 = st.columns(3)
                    with c1: st.link_button("WhatsApp'tan Yaz", f"https://wa.me/{row['telefon']}", use_container_width=True)
                    with c2: 
                        if st.button("✍️ Düzenle", key=f"edit_cust_{row['id']}", use_container_width=True):
                            st.session_state.editing_customer_id = row['id']
                            st.rerun()
                    with c3:
                        if st.button("🗑️ Sil", key=f"del_cust_{row['id']}", type="primary", use_container_width=True):
                            supabase.table("customers").delete().eq("id", row['id']).execute()
                            st.success(f"{row['ad_soyad']} silindi.")
                            st.rerun()
        else: st.info("Müşteri kaydı bulunamadı.")

elif choice == "Akıllı Eşleştirme":
    st.header("🎯 Akıllı Eşleştirme")
    cust_res = supabase.table("customers").select("*").execute()
    if cust_res.data:
        df_cust = pd.DataFrame(cust_res.data)
        selected = st.selectbox("Müşteri Seçin", df_cust["ad_soyad"].tolist())
        if selected:
            cust = df_cust[df_cust["ad_soyad"] == selected].iloc[0]
            table = {"Satılık Konut": "satilik_konut", "Kiralık Konut": "kiralik_konut", "Satılık Arsa": "satilik_arsa"}.get(cust["talep_türü"])
            if table:
                port_res = supabase.table(table).select("*").execute()
                if port_res.data:
                    regions = [str(cust[r]).lower().strip() for r in ["bölge_1", "bölge_2", "bölge_3"] if cust[r] and str(cust[r]).strip() != "-"]
                    matches = [p for p in port_res.data if any(r in str(p.get("bölge_mahalle", "")).lower() for r in regions)]
                    for p in matches:
                        with st.container(border=True):
                            st.write(f"**İlan: {p['ilan_no']}** | {p['bölge_mahalle']} | {p.get('fiyat')} TL")
                            image_urls = p.get('image_urls', [])
                            if image_urls:
                                st.image(get_image_url(image_urls[0]), width=100)
                            st.link_button("Müşteriye Gönder", f"https://wa.me/{cust['telefon']}?text=Sizin için uygun ilan: {p['ilan_no']}\nBölge: {p['bölge_mahalle']}\nFiyat: {p.get('fiyat')} TL")
    else: st.warning("Müşteri bulunamadı.")
