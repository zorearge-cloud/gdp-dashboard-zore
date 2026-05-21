import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("ZORE 5'Lİ VERİ PANELİ")

# Linklerini buraya 5 tane olacak şekilde diz
# Linklerin sonunun /export?format=xlsx olduğundan emin ol
URLS = [
    "https://docs.google.com/spreadsheets/d/1j819WkX93CkCy3VgZkSff5C_zNX5Z98jfK-FwI4ZWUU/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1hVk6VgMFXWAukoQwMDIoOLrG8SD4UDLFFRH9VmDhXSE/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1S1kTptWUEf705cBLw9P9mL6rrqbVjbcp1xk_hgQ-Ny0/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1VKb6za4Fse5XrGawPG6qvrQZuFhDRGaAysmADGIC7Wc/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=xlsx"
]

# Sekme isimlerini buraya yaz
tab_names = ["has_sea", "has_air", "ist_sea", "ist_air", "meh_sea", "meh_air"]

# 5 sekme oluştur
tabs = st.tabs(tab_names)

@st.cache_data
def load_data(url):
    try:
        return pd.read_excel(url)
    except Exception as e:
        return None

# Sekmeleri döngüye al
for i, tab in enumerate(tabs):
    with tab:
        df = load_data(URLS[i])
        if df is not None:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.error("Veri yüklenemedi. Linki ve paylaşım ayarlarını kontrol et.")