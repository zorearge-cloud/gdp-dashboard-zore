import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

# 5 linkin sabit
URLS = [
    "https://docs.google.com/spreadsheets/d/1j819WkX93CkCy3VgZkSff5C_zNX5Z98jfK-FwI4ZWUU/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1hVk6VgMFXWAukoQwMDIoOLrG8SD4UDLFFRH9VmDhXSE/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1S1kTptWUEf705cBLw9P9mL6rrqbVjbcp1xk_hgQ-Ny0/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1VKb6za4Fse5XrGawPG6qvrQZuFhDRGaAysmADGIC7Wc/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
]

@st.cache_data
def get_data():
    all_dfs = []
    for url in URLS:
        try:
            df = pd.read_csv(url)
            all_dfs.append(df)
        except Exception as e:
            st.warning(f"Bir link okunamadı: {url}")
    return pd.concat(all_dfs, ignore_index=True)

df = get_data()

# Sütun adlarına hiç dokunmuyoruz. 
# 'TUR' sütununu kategori olarak baz alarak sekmeleri oluşturuyoruz.
# Eğer kategori sütununun adı 'TUR' değilse, lütfen söyle, burayı ona göre düzelteyim.
kategoriler = df['TUR'].dropna().unique()
tabs = st.tabs([str(k) for k in kategoriler])

for i, kategori in enumerate(kategoriler):
    with tabs[i]:
        st.write(f"### {kategori}")
        st.dataframe(df[df['TUR'] == kategori], use_container_width=True)