import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("ZORE VERİ TESPİT PANELİ (DEBUG MODE)")

links = [
    "https://docs.google.com/spreadsheets/d/1j819WkX93CkCy3VgZkSff5C_zNX5Z98jfK-FwI4ZWUU/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1hVk6VgMFXWAukoQwMDIoOLrG8SD4UDLFFRH9VmDhXSE/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1S1kTptWUEf705cBLw9P9mL6rrqbVjbcp1xk_hgQ-Ny0/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1VKb6za4Fse5XrGawPG6qvrQZuFhDRGaAysmADGIC7Wc/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=xlsx"
]

target_tabs = ["has_air", "has_sea", "meh_air", "meh_sea", "ist_air", "ist_sea"]

st.write("---")
st.subheader("SİSTEMİN GÖRDÜĞÜ SEKME İSİMLERİ (DEBUG):")

for link in links:
    st.write(f"Link: {link[:40]}...")
    try:
        xl = pd.ExcelFile(link)
        found_sheets = xl.sheet_names
        st.success(f"Dosya açıldı. Bulunan sekmeler: {found_sheets}")
        
        # Sekmeleri kontrol et
        for target in target_tabs:
            if target not in found_sheets:
                st.warning(f"DİKKAT: '{target}' sekmesi bu dosyada YOK!")
    except Exception as e:
        st.error(f"Dosya AÇILAMADI! Hata: {e}")

st.write("---")
st.info("Eğer yukarıda 'Yok' yazısını görüyorsan, Google Sheets içindeki sekme isminin yazılışı kodunkiyle birebir aynı değildir (bir boşluk bile fark eder).")