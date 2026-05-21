import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import numpy as np
from typing import Dict

# ==============================================================================
# 1. CONFIGURATION & ENTERPRISE THEME
# ==============================================================================
st.set_page_config(page_title="ZORE GLOBAL ERP BI", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #0c0f14; color: #e2e8f0; }
    .css-1r6slp0 { background-color: #1a2234; }
    .metric-card { background: #1e293b; padding: 20px; border-radius: 12px; border: 1px solid #334155; }
    h1, h2, h3 { color: #f8fafc !important; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. MASTER SOURCE CONFIGURATION
# ==============================================================================
# Buraya eklediğin her link otomatik olarak sisteme dahil olur.
SOURCE_MAPPING = {
    "https://docs.google.com/spreadsheets/d/1j819WkX93CkCy3VgZkSff5C_zNX5Z98jfK-FwI4ZWUU/edit?gid=0#gid=0": {"ENTITY": "IST", "MODE": "AIR"},
    "https://docs.google.com/spreadsheets/d/1hVk6VgMFXWAukoQwMDIoOLrG8SD4UDLFFRH9VmDhXSE/edit?gid=0#gid=0": {"ENTITY": "IST", "MODE": "SEA"},
    "https://docs.google.com/spreadsheets/d/1S1kTptWUEf705cBLw9P9mL6rrqbVjbcp1xk_hgQ-Ny0/edit?gid=0#gid=0": {"ENTITY": "HAS", "MODE": "AIR"},
    "https://docs.google.com/spreadsheets/d/1VKb6za4Fse5XrGawPG6qvrQZuFhDRGaAysmADGIC7Wc/edit?gid=0#gid=0": {"ENTITY": "HAS", "MODE": "SEA"},
    # Senin orijinal dosyanı da buraya ekledim:
    "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/edit?gid=0#gid=0": {"ENTITY": "ANA", "MODE": "GENEL"}
}

# ==============================================================================
# 3. DATA ENGINE (ETL PROCESS)
# ==============================================================================
@st.cache_data(ttl=600)
def fetch_master_data(sources: Dict):
    compiled_df = []
    
    for url, meta in sources.items():
        try:
            # GSheets export trick
            export_url = url.replace('/edit?gid=', '/export?format=csv&gid=')
            df = pd.read_csv(export_url)
            df.columns = df.columns.str.strip()
            
            # Metadata injection
            df['ENTITY'] = meta['ENTITY']
            df['MODE'] = meta['MODE']
            
            # Sanitization
            df['ADET'] = pd.to_numeric(df['ADET'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
            
            def clean_currency(val):
                val = str(val).replace('¥', '').replace('$', '').replace(',', '.')
                val = re.sub(r'[^\d.]', '', val)
                try: return float(val)
                except: return 0.0
            
            df['FIYAT_NUM'] = df['FIYAT'].apply(clean_currency)
            df['TUTAR'] = df['ADET'] * df['FIYAT_NUM']
            
            compiled_df.append(df)
        except Exception as e:
            st.error(f"Hata ({meta['ENTITY']}_{meta['MODE']}): {e}")
            
    return pd.concat(compiled_df, ignore_index=True) if compiled_df else pd.DataFrame()

# ==============================================================================
# 4. ANALYSIS ENGINE (BI LOGIC)
# ==============================================================================
def render_detailed_analysis(df, entity, mode):
    subset = df[(df['ENTITY'] == entity) & (df['MODE'] == mode)]
    
    if subset.empty:
        st.warning(f"Bu kategoride ({entity}-{mode}) veri yok.")
        return

    # KPI ROW
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Ciro", f"¥{subset['TUTAR'].sum():,.0f}")
    c2.metric("Toplam Adet", f"{int(subset['ADET'].sum()):,}")
    c3.metric("Firma Sayısı", subset['FIRMA'].nunique())
    c4.metric("Ortalama Fiyat", f"¥{subset['FIYAT_NUM'].mean():,.2f}")
    
    st.markdown("---")
    
    # 2x2 GRID
    row1, row2 = st.columns(2), st.columns(2)
    
    # Bar Chart: Top Firms
    with row1[0]:
        st.subheader("Firma Bazlı Harcama")
        fig1 = px.bar(subset.groupby('FIRMA')['TUTAR'].sum().nlargest(10).reset_index(), 
                      x='TUTAR', y='FIRMA', orientation='h', template="plotly_dark", color='TUTAR')
        st.plotly_chart(fig1, use_container_width=True)
        
    # Pie Chart: Product Mix
    with row1[1]:
        st.subheader("Ürün Payı")
        fig2 = px.pie(subset.groupby('MALIN CINSI')['TUTAR'].sum().nlargest(10).reset_index(), 
                      names='MALIN CINSI', values='TUTAR', hole=0.5, template="plotly_dark")
        st.plotly_chart(fig2, use_container_width=True)

    # Detailed Table
    st.subheader("Detaylı İşlem Listesi")
    st.dataframe(subset[['FIRMA', 'MALIN CINSI', 'ADET', 'FIYAT', 'TUTAR']], use_container_width=True, use_container_width=True)

# ==============================================================================
# 5. MAIN APPLICATION
# ==============================================================================
def main():
    st.title("🚀 ZORE MASTER DATA CONTROL CENTER")
    
    # Veri Çekme
    with st.spinner('Tüm kanallar (IST, HAS, MEH, ANA) senkronize ediliyor...'):
        master_df = fetch_master_data(SOURCE_MAPPING)
    
    if master_df.empty:
        st.error("Veri alınamadı. Linkleri kontrol et.")
        return

    # DİNAMİK SEKMELER
    # SOURCE_MAPPING içindeki tüm unique kombinasyonları al ve sekme yap
    tab_list = ["MASTER_VIEW"]
    for url, meta in SOURCE_MAPPING.items():
        tab_list.append(f"{meta['ENTITY']}_{meta['MODE']}")
    
    tabs = st.tabs(tab_list)
    
    # MASTER VIEW (TÜM VERİ)
    with tabs[0]:
        st.header("Genel Master Veri Havuzu")
        st.metric("Toplam Operasyonel Ciro", f"¥{master_df['TUTAR'].sum():,.0f}")
        st.dataframe(master_df, use_container_width=True)
    
    # KATEGORİK GÖRÜNÜM
    for i, (url, meta) in enumerate(SOURCE_MAPPING.items()):
        with tabs[i+1]:
            render_detailed_analysis(master_df, meta['ENTITY'], meta['MODE'])

if __name__ == "__main__":
    main()