import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

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
            # Sütunlara dokunmuyoruz
            df = pd.read_csv(url)
            all_dfs.append(df)
        except Exception as e:
            continue
    
    # Hepsi birleştiriliyor
    master_df = pd.concat(all_dfs, ignore_index=True)
    
    # Tarihe göre sıralama yapmak için geçici format düzeltme
    # (Hatalı tarih formatı olursa diye errors='coerce' ekledim, çökme yaşanmasın diye)
    master_df['SIPARIS_TARIHI'] = pd.to_datetime(master_df['SIPARIS_TARIHI'], dayfirst=True, errors='coerce')
    
    # Tarihe göre sırala (Eskiden yeniye)
    master_df = master_df.sort_values(by='SIPARIS_TARIHI', ascending=True)
    
    return master_df

# Veriyi çek
df = get_data()

# Ekrana bas
st.title("Master Veri Tablosu")
st.dataframe(df, use_container_width=True, height=800)