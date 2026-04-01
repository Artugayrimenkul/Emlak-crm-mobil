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
            # Upsert true sayesinde aynı isimli dosyanın üzerine yazabiliriz
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
        
        # Resim işlemi
        ilan_no_val = clean_data.get('ilan_no')
        if image_file and ilan_no_val:
            img_name = upload_image(image_file, ilan_no_val)
            if img_name:
                clean_data['resim_url'] = img_name
        
        if is_update:
            # Güncellemede ilan_no ve tarih alanlarını değiştirmeyelim
            if 'ilan_no' in clean_data: del clean_data['ilan_no']
            if 'tarih' in clean_data: del clean_data['tarih']
            res = supabase.table(table_name).update(clean_data).eq("id", record_id).execute()
            st.success("Kayıt başarıyla güncellendi!")
        else:
            if 'id' in clean_data: del clean_data['id']
            res = supabase.table(table_name).insert(clean_data).execute()
            st.success("Buluta başarıyla kaydedildi!")
    except Exception as e:
        st.error(f"Kayıt hatası detayı: {e}")

# --- MENÜ İÇERİKLERİ ---

if choice == "Yeni Müşteri":
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
            write_to_cloud("customers", data)

elif choice == "Müşteri Listesi":
    st.header("👥 Müşteri Yönetimi")
    if 'editing_customer_id' in st.session_state and st.session_state.editing_customer_id is not None:
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

elif choice == "Yeni Satılık Konut":
    st.header("💰 Yeni Satılık Konut")
    with st.form("sk_form"):
        ilan_no = st.text_input("İlan No")
        tip = st.selectbox("Konut Tipi", ["Daire", "Villa", "Rezidans"])
        fiyat = st.text_input("Fiyat")
        bolge = st.text_input("Bölge/Mahalle")
        oda = st.selectbox("Oda Sayısı", ["1+1", "2+1", "3+1", "4+1", "5+1"])
        kat = st.text_input("Kat")
        sahibi = st.text_input("Mülk Sahibi"); sahibi_tel = st.text_input("Sahibi Tel")
        notlar = st.text_area("Notlar")
        img = st.file_uploader("İlan Resmi Seç", type=["jpg", "png", "jpeg"])
        if st.form_submit_button("İlanı Kaydet"):
            data = {"tarih": datetime.now().strftime("%d.%m.%Y"), "ilan_no": ilan_no, "konut_tipi": tip, "fiyat": fiyat, "bölge_mahalle": bolge, "oda_sayısı": oda, "kat": kat, "sahibi": sahibi, "sahibi_tel": sahibi_tel, "notlar": notlar}
            write_to_cloud("satilik_konut", data, img)

elif choice == "Yeni Kiralık Konut":
    st.header("🔑 Yeni Kiralık Konut")
    with st.form("kk_form"):
        ilan_no = st.text_input("İlan No")
        tip = st.selectbox("Konut Tipi", ["Daire", "Villa", "Rezidans"])
        fiyat = st.text_input("Kira Bedeli")
        bolge = st.text_input("Bölge/Mahalle")
        oda = st.selectbox("Oda Sayısı", ["1+1", "2+1", "3+1", "4+1", "5+1"])
        kat = st.text_input("Kat")
        sahibi = st.text_input("Mülk Sahibi"); sahibi_tel = st.text_input("Sahibi Tel")
        notlar = st.text_area("Notlar")
        img = st.file_uploader("Resim Seç", type=["jpg", "png", "jpeg"])
        if st.form_submit_button("İlanı Kaydet"):
            data = {"tarih": datetime.now().strftime("%d.%m.%Y"), "ilan_no": ilan_no, "konut_tipi": tip, "fiyat": fiyat, "bölge_mahalle": bolge, "oda_sayısı": oda, "kat": kat, "sahibi": sahibi, "sahibi_tel": sahibi_tel, "notlar": notlar}
            write_to_cloud("kiralik_konut", data, img)

elif choice == "Yeni Satılık Arsa":
    st.header("🌳 Yeni Satılık Arsa")
    with st.form("sa_form"):
        ilan_no = st.text_input("İlan No")
        tip = st.selectbox("Arsa Tipi", ["İmarlı", "Tarla", "Zeytinlik"])
        ada = st.text_input("Ada"); parsel = st.text_input("Parsel")
        fiyat = st.text_input("Fiyat")
        bolge = st.text_input("Bölge/Mahalle")
        sahibi = st.text_input("Mülk Sahibi"); sahibi_tel = st.text_input("Sahibi Tel")
        notlar = st.text_area("Notlar")
        img = st.file_uploader("Arsa Resmi Seç", type=["jpg", "png", "jpeg"])
        if st.form_submit_button("Arsayı Kaydet"):
            data = {"tarih": datetime.now().strftime("%d.%m.%Y"), "ilan_no": ilan_no, "arsa_tipi": tip, "ada": ada, "parsel": parsel, "fiyat": fiyat, "bölge_mahalle": bolge, "sahibi": sahibi, "sahibi_tel": sahibi_tel, "notlar": notlar}
            write_to_cloud("satilik_arsa", data, img)

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
                            c1, c2 = st.columns([1, 3])
                            with c1:
                                url = get_image_url(p.get('resim_url'))
                                if url: st.image(url, width=100)
                            with c2:
                                st.write(f"**İlan: {p['ilan_no']}** | {p['bölge_mahalle']} | {p.get('fiyat')} TL")
                                st.link_button("Müşteriye Gönder", f"https://wa.me/{cust['telefon']}?text=Sizin için uygun ilan: {p['ilan_no']}\nBölge: {p['bölge_mahalle']}\nFiyat: {p.get('fiyat')} TL")
    else: st.warning("Müşteri bulunamadı.")
