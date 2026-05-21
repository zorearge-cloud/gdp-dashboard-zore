import streamlit as st
import pandas as pd
import plotly.express as px
import re
from typing import Dict

# ==============================================================================
# 1. KONFİGÜRASYON (Tarih Bilgilerini Buraya Ekliyoruz)
# ==============================================================================
st.set_page_config(page_title="ZORE GLOBAL ERP", layout="wide")

# SOURCE_MAPPING: Her dosyanın tarihini (YYYY-MM formatında) ekledim.
SOURCE_MAPPING = {
    "https://docs.google.com/spreadsheets/d/1j819WkX93CkCy3VgZkSff5C_zNX5Z98jfK-FwI4ZWUU/edit?gid=0#gid=0": {"ENTITY": "IST", "MODE": "AIR", "DATE": "2026-01"},
    "https://docs.google.com/spreadsheets/d/1hVk6VgMFXWAukoQwMDIoOLrG8SD4UDLFFRH9VmDhXSE/edit?gid=0#gid=0": {"ENTITY": "IST", "MODE": "SEA", "DATE": "2026-02"},
    "https://docs.google.com/spreadsheets/d/1S1kTptWUEf705cBLw9P9mL6rrqbVjbcp1xk_hgQ-Ny0/edit?gid=0#gid=0": {"ENTITY": "HAS", "MODE": "AIR", "DATE": "2026-03"},
    "https://docs.google.com/spreadsheets/d/1VKb6za4Fse5XrGawPG6qvrQZuFhDRGaAysmADGIC7Wc/edit?gid=0#gid=0": {"ENTITY": "HAS", "MODE": "SEA", "DATE": "2026-04"},
    "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/edit?gid=0#gid=0": {"ENTITY": "ANA", "MODE": "GENEL", "DATE": "2026-05"}
}

# ==============================================================================
# 2. DATA ENGINE (ETL)
# ==============================================================================
@st.cache_data(ttl=600)
def fetch_master_data(sources: Dict):
    compiled_df = []
    for url, meta in sources.items():
        try:
            export_url = url.replace('/edit?gid=', '/export?format=csv&gid=')
            df = pd.read_csv(export_url)
            df.columns = df.columns.str.strip()
            
            # Metadata Ekleme
            df['ENTITY'] = meta['ENTITY']
            df['MODE'] = meta['MODE']
            df['DATE'] = meta['DATE'] # Tarih sütunu artık burada
            
            # Temizleme
            df['ADET'] = pd.to_numeric(df['ADET'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
            
            def clean_currency(val):
                clean_str = re.sub(r'[^\d.]', '', str(val).replace(',', '.'))
                try: return float(clean_str)
                except: return 0.0
            
            df['FIYAT_NUM'] = df['FIYAT'].apply(clean_currency)
            df['TUTAR'] = df['ADET'] * df['FIYAT_NUM']
            
            compiled_df.append(df)
        except Exception: continue
            
    return pd.concat(compiled_df, ignore_index=True) if compiled_df else pd.DataFrame()

# ==============================================================================
# 3. ANALYSIS ENGINE
# ==============================================================================
def render_dashboard(df):
    st.title("🚀 ZORE MASTER DATA CONTROL CENTER")
    
    # Sidebar Filtreleme
    st.sidebar.header("Filtreleme")
    all_dates = sorted(df['DATE'].unique(), reverse=True)
    selected_dates = st.sidebar.multiselect("Ay Seçimi (Çoklu Seçilebilir)", all_dates, default=all_dates)
    
    # Filtrelenmiş Veri
    filtered_df = df[df['DATE'].isin(selected_dates)]
    
    # KPI Satırı
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Ciro", f"¥{filtered_df['TUTAR'].sum():,.0f}")
    c2.metric("Toplam Adet", f"{int(filtered_df['ADET'].sum()):,}")
    c3.metric("Firma Sayısı", filtered_df['FIRMA'].nunique())
    c4.metric("Seçili Ay Sayısı", len(selected_dates))
    
    st.markdown("---")
    
    # Görseller
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Firma Bazlı Harcama")
        fig1 = px.bar(filtered_df.groupby('FIRMA')['TUTAR'].sum().nlargest(10).reset_index(), 
                      x='TUTAR', y='FIRMA', orientation='h', template="plotly_dark", color='TUTAR')
        st.plotly_chart(fig1, use_container_width=True)
        
    with col2:
        st.subheader("Aylık Trend")
        fig2 = px.line(filtered_df.groupby('DATE')['TUTAR'].sum().reset_index(), 
                       x='DATE', y='TUTAR', markers=True, template="plotly_dark")
        st.plotly_chart(fig2, use_container_width=True)

    # Detay Tablosu
    st.subheader("İşlem Detayları")
    st.dataframe(filtered_df, use_container_width=True)

# ==============================================================================
# 4. MAIN
# ==============================================================================
def main():
    with st.spinner('Veriler senkronize ediliyor...'):
        master_df = fetch_master_data(SOURCE_MAPPING)
    
    if master_df.empty:
        st.error("Veri alınamadı.")
        return

    # Sekmeler
    tab1, tab2 = st.tabs(["Dashboard", "Ham Veri Analizi"])
    
    with tab1:
        render_dashboard(master_df)
    with tab2:
        st.header("Veri Envanteri")
        st.dataframe(master_df, use_container_width=True)

if __name__ == "__main__":
    main()