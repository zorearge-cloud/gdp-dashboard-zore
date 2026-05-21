import streamlit as st
import pandas as pd
import plotly.express as px
import re

# Sayfa Ayarları
st.set_page_config(page_title="ZORE PRO MASTER", layout="wide")

# Link Listesi (Buraya 5 linkini de ekledim)
URLS = [
    "https://docs.google.com/spreadsheets/d/1j819WkX93CkCy3VgZkSff5C_zNX5Z98jfK-FwI4ZWUU/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1hVk6VgMFXWAukoQwMDIoOLrG8SD4UDLFFRH9VmDhXSE/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1S1kTptWUEf705cBLw9P9mL6rrqbVjbcp1xk_hgQ-Ny0/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1VKb6za4Fse5XrGawPG6qvrQZuFhDRGaAysmADGIC7Wc/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
]

@st.cache_data(ttl=600)
def load_master_data():
    all_dfs = []
    for url in URLS:
        try:
            temp_df = pd.read_csv(url)
            all_dfs.append(temp_df)
        except: continue
    
    if not all_dfs: return pd.DataFrame()
    
    df = pd.concat(all_dfs, ignore_index=True)
    df.columns = df.columns.str.strip()
    
    # 1. Tarih ve Adet Temizleme
    df['SIPARIS_TARIHI'] = pd.to_datetime(df['SIPARIS_TARIHI'], dayfirst=True, errors='coerce')
    df['ADET'] = pd.to_numeric(df['ADET'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
    
    # 2. Fiyat Motoru (Hata önleyici)
    def clean_price(row):
        val = str(row['FIYAT'])
        # Sadece sayı ve noktayı al
        nums = re.sub(r'[^\d.]', '', val.replace(',', '.'))
        try:
            price = float(nums) if nums else 0.0
        except:
            price = 0.0
        # Kur çarpımı
        if '¥' in val:
            price = price * 0.14
        return price * row['ADET']

    df['TUTAR'] = df.apply(clean_price, axis=1)
    return df

df = load_master_data()

# --- ALTIN ÜÇLÜ ---
st.sidebar.title("🚀 ZORE PANEL")
page = st.sidebar.radio("Sayfalar", ["Dashboard", "Firma Detay Analizi", "Ham Veri"])

# 1. DASHBOARD
if page == "Dashboard":
    st.title("📊 Genel Dashboard")
    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam Ciro (USD)", f"${df['TUTAR'].sum():,.2f}")
    col2.metric("Toplam Adet", f"{int(df['ADET'].sum()):,}")
    col3.metric("Firma Sayısı", len(df['FIRMA'].unique()))
    
    st.markdown("---")
    fig = px.bar(df.groupby('FIRMA')['TUTAR'].sum().reset_index(), x='FIRMA', y='TUTAR', template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

# 2. FİRMA DETAY
elif page == "Firma Detay Analizi":
    st.title("🏢 Firma Detay Analizi")
    f = st.selectbox("Firma Seçin:", sorted(df['FIRMA'].dropna().unique()))
    d = df[df['FIRMA'] == f]
    
    st.metric("Bu Firmanın Toplam Cirosu", f"${d['TUTAR'].sum():,.2f}")
    # Hata veren satırı tek bir 'use_container_width' ile düzelttim
    st.dataframe(d[['SIPARIS_TARIHI', 'FIRMA', 'MALIN CINSI', 'ADET', 'TUTAR']], use_container_width=True)

# 3. HAM VERİ
else:
    st.title("🗄️ Ham Veri")
    st.dataframe(df, use_container_width=True)