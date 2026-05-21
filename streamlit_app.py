import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("🔍 VERİ YAPISI KONTROL PANELİ")

LINKS = [
    "https://docs.google.com/spreadsheets/d/1j819WkX93CkCy3VgZkSff5C_zNX5Z98jfK-FwI4ZWUU/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1hVk6VgMFXWAukoQwMDIoOLrG8SD4UDLFFRH9VmDhXSE/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1S1kTptWUEf705cBLw9P9mL6rrqbVjbcp1xk_hgQ-Ny0/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1VKb6za4Fse5XrGawPG6qvrQZuFhDRGaAysmADGIC7Wc/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=xlsx"
]

TARGET_TABS = ["has_air", "has_sea", "meh_air", "meh_sea", "ist_air", "ist_sea"]

for link in LINKS:
    st.markdown(f"---")
    st.write(f"**Dosya:** {link.split('/')[-2]}")
    try:
        xl = pd.ExcelFile(link)
        for tab in TARGET_TABS:
            if tab in xl.sheet_names:
                df = pd.read_excel(xl, sheet_name=tab)
                
                # Sütunları listele
                cols = df.columns.tolist()
                
                # Tekrar eden sütun var mı?
                duplicates = [c for c in cols if cols.count(c) > 1]
                
                st.write(f"▶ **Sekme:** `{tab}`")
                st.write(f"Sütun Sayısı: {len(cols)}")
                st.write(f"Sütun İsimleri:", cols)
                
                if duplicates:
                    st.error(f"⚠️ DİKKAT! Bu sütunlar birden fazla var: {list(set(duplicates))}")
                
                # İlk 2 satırı göster (Veri kaymış mı?)
                st.dataframe(df.head(2), use_container_width=True)
                
    except Exception as e:
        st.error(f"Hata: {e}")