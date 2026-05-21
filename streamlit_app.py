import streamlit as st
import pandas as pd
import plotly.express as px
import re

# Sayfa Yapılandırması
st.set_page_config(page_title="ZORE MASTER DATA V2.0", layout="wide")

# Sabit Linkler
URLS = [
    "https://docs.google.com/spreadsheets/d/1j819WkX93CkCy3VgZkSff5C_zNX5Z98jfK-FwI4ZWUU/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1hVk6VgMFXWAukoQwMDIoOLrG8SD4UDLFFRH9VmDhXSE/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1S1kTptWUEf705cBLw9P9mL6rrqbVjbcp1xk_hgQ-Ny0/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1VKb6za4Fse5XrGawPG6qvrQZuFhDRGaAysmADGIC7Wc/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
]

@st.cache_data(ttl=3600)
def load_data():
    all_dfs = []
    for url in URLS:
        try:
            df = pd.read_csv(url)
            all_dfs.append(df)
        except: continue
    
    df = pd.concat(all_dfs, ignore_index=True)
    df.columns = df.columns.str.strip()
    
    # Veri Temizleme
    df['SIPARIS_TARIHI'] = pd.to_datetime(df['SIPARIS_TARIHI'], dayfirst=True, errors='coerce')
    df['AY'] = df['SIPARIS_TARIHI'].dt.to_period('M').astype(str)
    df['ADET'] = pd.to_numeric(df['ADET'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
    
    # Kur ve Fiyat Motoru
    def get_clean_tutar(row):
        try:
            raw = str(row['FIYAT'])
            nums = re.sub(r'[^\d.]', '', raw.replace(',', '.'))
            val = float(nums) if nums else 0.0
            # ¥ sembolü varsa 0.14, yoksa dolar
            return (val * 0.14 * row['ADET']) if '¥' in raw else (val * row['ADET'])
        except: return 0.0

    df['TUTAR'] = df.apply(get_clean_tutar, axis=1)
    return df

df = load_data()

# --- SİDEBAR ---
st.sidebar.title("🔍 ZORE DASHBOARD")
page = st.sidebar.radio("Sayfa Seçimi", ["Genel Dashboard", "Firma Detay Analizi", "Ham Veri"])
selected_months = st.sidebar.multiselect("Ay Seçimi", sorted(df['AY'].dropna().unique(), reverse=True), default=sorted(df['AY'].dropna().unique(), reverse=True))

df_f = df[df['AY'].isin(selected_months)]

# --- GENEL DASHBOARD ---
if page == "Genel Dashboard":
    st.title("🚀 Yönetici Özet Paneli")
    
    # KPI Satırı
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Ciro (USD)", f"${df_f['TUTAR'].sum():,.2f}")
    c2.metric("Toplam Adet", f"{int(df_f['ADET'].sum()):,}")
    c3.metric("Aktif Firma", len(df_f['FIRMA'].unique()))
    c4.metric("Kategori", len(df_f['TUR'].unique()))
    
    st.markdown("---")
    
    # Grafikler
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📈 Aylık Ciro Trendi")
        trend = df_f.groupby('AY')['TUTAR'].sum().reset_index()
        fig1 = px.line(trend, x='AY', y='TUTAR', markers=True, template="plotly_dark")
        st.plotly_chart(fig1, use_container_width=True)
        
    with col2:
        st.subheader("🏢 En Çok Harcama Yapılan 10 Firma")
        top_firms = df_f.groupby('FIRMA')['TUTAR'].sum().nlargest(10).reset_index()
        fig2 = px.bar(top_firms, x='TUTAR', y='FIRMA', orientation='h', template="plotly_dark", color='TUTAR')
        st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("📦 En Çok Ciro Getiren 10 Ürün")
        top_products = df_f.groupby('MALIN CINSI')['TUTAR'].sum().nlargest(10).reset_index()
        fig3 = px.bar(top_products, x='TUTAR', y='MALIN CINSI', orientation='h', template="plotly_dark", color='TUTAR')
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        st.subheader("📂 Kategori Dağılımı")
        fig4 = px.pie(df_f, values='TUTAR', names='TUR', hole=0.5, template="plotly_dark")
        st.plotly_chart(fig4, use_container_width=True)

# --- FİRMA DETAY ---
elif page == "Firma Detay Analizi":
    st.title("🏢 Firma Detay Analizi")
    firm_sel = st.selectbox("Analiz edilecek firma:", sorted(df['FIRMA'].unique()))
    f_df = df_f[df_f['FIRMA'] == firm_sel]
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Firma Toplam Ciro", f"${f_df['TUTAR'].sum():,.2f}")
    k2.metric("Toplam Adet", int(f_df['ADET'].sum()))
    k3.metric("Ürün Çeşitliliği", len(f_df['MALIN CINSI'].unique()))
    
    st.subheader(f"{firm_sel} - Detaylı Ürün Analizi")
    st.dataframe(f_df[['AY', 'BARKOD', 'MALIN CINSI', 'TUR', 'ADET', 'TUTAR']], use_container_width=True)

# --- HAM VERİ ---
else:
    st.title("🗄️ Master Veri Seti")
    st.dataframe(df_f, use_container_width=True)