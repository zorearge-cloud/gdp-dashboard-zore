import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("ZORE MERKEZİ VERİ HAVUZU")

LINKS = [
    "https://docs.google.com/spreadsheets/d/1j819WkX93CkCy3VgZkSff5C_zNX5Z98jfK-FwI4ZWUU/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1hVk6VgMFXWAukoQwMDIoOLrG8SD4UDLFFRH9VmDhXSE/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1S1kTptWUEf705cBLw9P9mL6rrqbVjbcp1xk_hgQ-Ny0/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1VKb6za4Fse5XrGawPG6qvrQZuFhDRGaAysmADGIC7Wc/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=xlsx"
]

TARGET_TABS = ["has_air", "has_sea", "meh_air", "meh_sea", "ist_air", "ist_sea"]

# SADECE İSTEDİĞİMİZ SÜTUNLAR (Whitelist)
EXPECTED_COLUMNS = ['SIPARIS_TARIHI', 'FIRMA', 'TUR', 'BARKOD', 'MALIN CINSI', 'ADET', 'FIYAT', 'YUKLEME_TARIHI']

def clean_data(df):
    # 1. Duplike (aynı isimli) sütunları temizle
    df = df.loc[:, ~df.columns.duplicated()]
    
    # 2. Tarihleri düzelt
    for col in ['SIPARIS_TARIHI', 'YUKLEME_TARIHI']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
    
    # 3. WHİTELİST YÖNTEMİ: Sadece listedekileri al, gerisini at
    # Mevcut dosyadaki sütunlar ile bizim beklediklerimizi karşılaştır
    available_cols = [c for c in EXPECTED_COLUMNS if c in df.columns]
    df = df[available_cols]
    
    # 4. Boş satırları at
    df = df.dropna(how='all')
    return df

# Veri toplama
data_pool = {tab: [] for tab in TARGET_TABS}

for link in LINKS:
    try:
        xl = pd.ExcelFile(link)
        for tab in TARGET_TABS:
            if tab in xl.sheet_names:
                df = pd.read_excel(xl, sheet_name=tab)
                df_clean = clean_data(df)
                if not df_clean.empty:
                    data_pool[tab].append(df_clean)
    except:
        pass

# Arayüz
tabs = st.tabs(TARGET_TABS)

for i, tab_ui in enumerate(tabs):
    with tab_ui:
        tab_name = TARGET_TABS[i]
        df_list = data_pool[tab_name]
        
        if df_list:
            combined_df = pd.concat(df_list, ignore_index=True)
            combined_df = combined_df.drop_duplicates()
            st.dataframe(combined_df, use_container_width=True, hide_index=True)
        else:
            st.warning(f"Bu sekme ({tab_name}) için veri bulunamadı.")