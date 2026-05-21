import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

# Linklerini bu sözlüğe doğru şekilde yerleştir
data_sources = {
    "HAS": {"SEA": "URL_HAS_SEA", "AIR": "URL_HAS_AIR"},
    "IST": {"SEA": "URL_IST_SEA", "AIR": "URL_IST_AIR"},
    "MEH": {"SEA": "URL_MEH_SEA", "AIR": "URL_MEH_AIR"}
}

@st.cache_data
def load_clean_data(url):
    try:
        df = pd.read_csv(url)
        # Sütun isimlerini düzelt
        df.columns = df.columns.str.strip()
        
        # Tarih formatı: Saati at, sadece tarih kalsın
        if 'SIPARIS_TARIHI' in df.columns:
            df['SIPARIS_TARIHI'] = pd.to_datetime(df['SIPARIS_TARIHI'], errors='coerce').dt.date
            
        # Sayısal değerleri temizle (None veya boşluk varsa 0 yap)
        for col in ['ADET', 'FIYAT']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame()

# ARAYÜZ
st.title("ZORE MASTER DATA CONTROL CENTER")

# Ana sekmeler (HAS, IST, MEH)
main_tabs = st.tabs(list(data_sources.keys()))

for i, main_tab_name in enumerate(data_sources.keys()):
    with main_tabs[i]:
        # Alt kırılım (SEA, AIR)
        sub_tabs = st.tabs(list(data_sources[main_tab_name].keys()))
        
        for j, sub_tab_name in enumerate(data_sources[main_tab_name].keys()):
            with sub_tabs[j]:
                url = data_sources[main_tab_name][sub_tab_name]
                
                # Veriyi çek ve göster
                df = load_clean_data(url)
                
                if not df.empty:
                    # Index'i gizle, temiz tabloyu bas
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info(f"{main_tab_name} - {sub_tab_name} verisi yüklenemedi veya boş.")