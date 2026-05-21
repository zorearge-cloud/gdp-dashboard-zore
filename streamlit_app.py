import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("ZORE MERKEZİ VERİ HAVUZU (AKILLI MOD)")

links = [
    "https://docs.google.com/spreadsheets/d/1j819WkX93CkCy3VgZkSff5C_zNX5Z98jfK-FwI4ZWUU/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1hVk6VgMFXWAukoQwMDIoOLrG8SD4UDLFFRH9VmDhXSE/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1S1kTptWUEf705cBLw9P9mL6rrqbVjbcp1xk_hgQ-Ny0/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1VKb6za4Fse5XrGawPG6qvrQZuFhDRGaAysmADGIC7Wc/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=xlsx"
]

target_tabs = ["has_air", "has_sea", "meh_air", "meh_sea", "ist_air", "ist_sea"]

# Verileri depolamak için bir havuz (Sözlük)
data_pool = {tab: [] for tab in target_tabs}

# 1. Aşama: Dosyaları tara, sadece var olan sekmeleri al
for link in links:
    try:
        xl = pd.ExcelFile(link)
        for tab in target_tabs:
            if tab in xl.sheet_names:
                df = pd.read_excel(xl, sheet_name=tab)
                data_pool[tab].append(df)
    except Exception as e:
        st.error(f"Bir dosya okunamadı: {e}")

# 2. Aşama: Arayüzü oluştur
tabs = st.tabs(target_tabs)

for i, tab_ui in enumerate(tabs):
    with tab_ui:
        tab_name = target_tabs[i]
        df_list = data_pool[tab_name]
        
        if df_list:
            # Tüm dosyalardan gelen veriyi alt alta birleştir
            combined_df = pd.concat(df_list, ignore_index=True)
            st.write(f"Toplam {len(combined_df)} satır veri bulundu.")
            st.dataframe(combined_df, use_container_width=True)
        else:
            st.warning(f"Bu sekme ({tab_name}) hiçbir dosyada bulunamadı.")