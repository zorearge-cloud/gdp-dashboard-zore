import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("ZORE MERKEZİ VERİ HAVUZU")

# Linkleri otomatik olarak xlsx formatına çevirerek listeye aldım
links = [
    "https://docs.google.com/spreadsheets/d/1j819WkX93CkCy3VgZkSff5C_zNX5Z98jfK-FwI4ZWUU/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1hVk6VgMFXWAukoQwMDIoOLrG8SD4UDLFFRH9VmDhXSE/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1S1kTptWUEf705cBLw9P9mL6rrqbVjbcp1xk_hgQ-Ny0/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1VKb6za4Fse5XrGawPG6qvrQZuFhDRGaAysmADGIC7Wc/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=xlsx"
]

target_tabs = ["has_air", "has_sea", "meh_air", "meh_sea", "ist_air", "ist_sea"]
data_pool = {tab: [] for tab in target_tabs}

# Linkleri tara, sekmeleri bul, havuza at
for link in links:
    try:
        xl = pd.ExcelFile(link)
        for sheet_name in xl.sheet_names:
            if sheet_name in target_tabs:
                df = pd.read_excel(xl, sheet_name=sheet_name)
                data_pool[sheet_name].append(df)
    except:
        continue

# Arayüzü oluştur ve verileri göster
tabs = st.tabs(target_tabs)

for i, tab in enumerate(tabs):
    with tab:
        current_tab = target_tabs[i]
        if data_pool[current_tab]:
            # Tüm linklerden gelen veriyi alt alta birleştir
            combined_df = pd.concat(data_pool[current_tab], ignore_index=True)
            st.dataframe(combined_df, use_container_width=True, hide_index=True)
        else:
            st.write(f"Bu sekme için veri bulunamadı.")