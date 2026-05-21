import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("ZORE MASTER VERİ PANELİ")

# LİNK EŞLEŞTİRME:
# Buraya 5 linkini yaz. Hangi sekme hangi linke gidiyorsa yanına onu yaz.
# Eğer 6. sekme için özel bir linkin yoksa, onu içeren linki tekrar yaz.
URL_CONFIG = {
    "https://docs.google.com/spreadsheets/d/1j819WkX93CkCy3VgZkSff5C_zNX5Z98jfK-FwI4ZWUU/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1hVk6VgMFXWAukoQwMDIoOLrG8SD4UDLFFRH9VmDhXSE/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1S1kTptWUEf705cBLw9P9mL6rrqbVjbcp1xk_hgQ-Ny0/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1VKb6za4Fse5XrGawPG6qvrQZuFhDRGaAysmADGIC7Wc/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
}

# 6 SEKME ÇEŞİDİ
tabs = st.tabs(["has_air", "has_sea", "meh_air", "meh_sea", "ist_air", "ist_sea"])

def get_raw_data(url, tab_name):
    try:
        # Veriyi excel olarak çek, sheet_name ile o sekmeye odaklan
        # Eğer sheet_name bulunamazsa ValueError verir, except bloğu yakalar
        df = pd.read_excel(url, sheet_name=tab_name)
        return df
    except Exception:
        # Sekme yoksa veya dosya okunamıyorsa None döner
        return None

# Sekmeleri döngüye al
for i, tab in enumerate(tabs):
    with tab:
        tab_name = ["has_air", "has_sea", "meh_air", "meh_sea", "ist_air", "ist_sea"][i]
        url = URL_CONFIG[tab_name]
        
        if "BURAYA" in url:
            st.warning(f"Lütfen {tab_name} için linki URL_CONFIG kısmına ekle.")
        else:
            df = get_raw_data(url, tab_name)
            
            if df is not None:
                # Veriye ASLA dokunmuyoruz, ham haliyle basıyoruz
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.error(f"Bu dosyada '{tab_name}' sayfası bulunamadı veya link hatalı.")