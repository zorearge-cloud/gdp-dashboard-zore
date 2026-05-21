import streamlit as st
import pandas as pd
import plotly.express as px
import re
from typing import Dict

# ==============================================================================
# 1. AYARLAR
# ==============================================================================
st.set_page_config(page_title="ZORE GLOBAL ERP", layout="wide")

# Sadece linklerini buraya yapıştırman yeterli. 
# Artık tarihleri dosya içinden (SIPARIS_TARIHI) otomatik çekecek.
SOURCE_MAPPING = {
    "https://docs.google.com/spreadsheets/d/1j819WkX93CkCy3VgZkSff5C_zNX5Z98jfK-FwI4ZWUU/edit?gid=0#gid=0": {"ENTITY": "IST", "MODE": "AIR"},
    "https://docs.google.com/spreadsheets/d/1hVk6VgMFXWAukoQwMDIoOLrG8SD4UDLFFRH9VmDhXSE/edit?gid=0#gid=0": {"ENTITY": "IST", "MODE": "SEA"},
    "https://docs.google.com/spreadsheets/d/1S1kTptWUEf705cBLw9P9mL6rrqbVjbcp1xk_hgQ-Ny0/edit?gid=0#gid=0": {"ENTITY": "HAS", "MODE": "AIR"},
    "https://docs.google.com/spreadsheets/d/1VKb6za4Fse5XrGawPG6qvrQZuFhDRGaAysmADGIC7Wc/edit?gid=0#gid=0": {"ENTITY": "HAS", "MODE": "SEA"},
    "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/edit?gid=0#gid=0": {"ENTITY": "ANA", "MODE": "GENEL"}
}

# ==============================================================================
# 2. VERİ MOTORU (ETL)
# ==============================================================================
@st.cache_data(ttl=600)
def fetch_master_data(sources: Dict):
    compiled_df = []
    for url, meta in sources.items():
        try:
            export_url = url.replace('/edit?gid=', '/export?format=csv&gid=')
            df = pd.read_csv(export_url)
            df.columns = df.columns.str.strip()
            
            # Sütunları standartlaştır
            df['ENTITY'] = meta['ENTITY']
            df['MODE'] = meta['MODE']
            
            # TARİH İŞLEME (SIPARIS_TARIHI'ni gerçek tarihe çevir)
            df['SIPARIS_TARIHI'] = pd.to_datetime(df['SIPARIS_TARIHI'], dayfirst=True, errors='coerce')
            df['AY_YIL'] = df['SIPARIS_TARIHI'].dt.to_period('M').astype(str) # Gruplama için
            
            # Sayısal ve Fiyat Temizleme
            df['ADET'] = pd.to_numeric(df['ADET'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
            
            def clean_currency(val):
                clean_str = re.sub(r'[^\d.]', '', str(val).replace(',', '.'))
                try: return float(clean_str)
                except: return 0.0
            
            df['FIYAT_NUM'] = df['FIYAT'].apply(clean_currency)
            df['TUTAR'] = df['ADET'] * df['FIYAT_NUM']
            
            compiled_df.append(df)
        except Exception as e:
            st.warning(f"Bir dosya yüklenemedi: {e}")
            
    return pd.concat(compiled_df, ignore_index=True) if compiled_df else pd.DataFrame()

# ==============================================================================
# 3. ANALİZ
# ==============================================================================
def render_dashboard(df):
    st.title("🚀 ZORE MASTER DATA CONTROL CENTER")
    
    # Sidebar Filtreleme (Ay Seçimi)
    st.sidebar.header("📊 Filtreleme")
    all_months = sorted(df['AY_YIL'].dropna().unique(), reverse=True)
    selected_months = st.sidebar.multiselect("Ay Seçimi", all_months, default=all_months)
    
    # Veri Filtreleme
    filtered_df = df[df['AY_YIL'].isin(selected_months)]
    
    # KPI Satırı
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Ciro", f"¥{filtered_df['TUTAR'].sum():,.0f}")
    c2.metric("Toplam Adet", f"{int(filtered_df['ADET'].sum()):,}")
    c3.metric("Firma Sayısı", filtered_df['FIRMA'].nunique())
    c4.metric("Seçilen Ay Sayısı", len(selected_months))
    
    st.markdown("---")
    
    # Görseller
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Firma Bazlı Harcama")
        fig1 = px.bar(filtered_df.groupby('FIRMA')['TUTAR'].sum().nlargest(10).reset_index(), 
                      x='TUTAR', y='FIRMA', orientation='h', template="plotly_dark", color='TUTAR')
        st.plotly_chart(fig1, use_container_width=True)
        
    with col2:
        st.subheader("Aylık Ciro Trendi")
        fig2 = px.line(filtered_df.groupby('AY_YIL')['TUTAR'].sum().reset_index(), 
                       x='AY_YIL', y='TUTAR', markers=True, template="plotly_dark")
        st.plotly_chart(fig2, use_container_width=True)

    # Detay Tablosu
    st.subheader("İşlem Detayları")
    st.dataframe(filtered_df, use_container_width=True)

# ==============================================================================
# 4. MAIN
# ==============================================================================
def main():
    master_df = fetch_master_data(SOURCE_MAPPING)
    
    if master_df.empty:
        st.error("Veri alınamadı. Google Sheets linklerinin erişime açık olduğundan emin olun.")
        return

    tab1, tab2 = st.tabs(["Dashboard", "Ham Veri Analizi"])
    
    with tab1:
        render_dashboard(master_df)
    with tab2:
        st.header("Veri Envanteri")
        st.dataframe(master_df, use_container_width=True)

if __name__ == "__main__":
    main()