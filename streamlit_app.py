import streamlit as st
import pandas as pd
import plotly.express as px
import re

# Sayfa Ayarları
st.set_page_config(page_title="ZORE PRO MASTER", layout="wide")

URLS = [
    "https://docs.google.com/spreadsheets/d/1j819WkX93CkCy3VgZkSff5C_zNX5Z98jfK-FwI4ZWUU/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1hVk6VgMFXWAukoQwMDIoOLrG8SD4UDLFFRH9VmDhXSE/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1S1kTptWUEf705cBLw9P9mL6rrqbVjbcp1xk_hgQ-Ny0/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1VKb6za4Fse5XrGawPG6qvrQZuFhDRGaAysmADGIC7Wc/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
]

@st.cache_data(ttl=3600)
def load_and_process():
    all_dfs = []
    for url in URLS:
        try:
            df = pd.read_csv(url)
            all_dfs.append(df)
        except: continue
    
    df = pd.concat(all_dfs, ignore_index=True)
    df.columns = df.columns.str.strip()
    
    # 1. TEMİZLEME: Tarih ve Adet (En sağlam yöntem)
    df['SIPARIS_TARIHI'] = pd.to_datetime(df['SIPARIS_TARIHI'], dayfirst=True, errors='coerce')
    df['AY'] = df['SIPARIS_TARIHI'].dt.to_period('M').astype(str)
    df['ADET'] = pd.to_numeric(df['ADET'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
    
    # 2. FİYAT İŞLEME (Kritik nokta burası)
    def clean_currency_and_calc(row):
        try:
            val_str = str(row['FIYAT'])
            # Sayısal olmayan her şeyi temizle, sadece sayı ve noktayı tut
            # Virgülü noktaya çevir
            clean_str = re.sub(r'[^\d.,]', '', val_str.replace(',', '.'))
            
            price = float(clean_str) if clean_str else 0.0
            
            # Kur hesabı: ¥ varsa 0.14, yoksa 1 (dolar)
            multiplier = 0.14 if '¥' in val_str else 1.0
            return price * multiplier * row['ADET']
        except:
            return 0.0 # Hata durumunda asla çökme, 0 dön.

    df['TUTAR'] = df.apply(clean_currency_and_calc, axis=1)
    return df

# Veriyi yükle
df = load_and_process()

# --- DASHBOARD ---
st.title("🚀 ZORE MASTER DATA")
page = st.sidebar.radio("Sayfalar", ["Dashboard", "Firma Detay Analizi", "Ham Veri"])

# Filtre
selected_months = st.sidebar.multiselect("Ay Seçimi", sorted(df['AY'].dropna().unique(), reverse=True), default=sorted(df['AY'].dropna().unique(), reverse=True))
df_f = df[df['AY'].isin(selected_months)]

if page == "Dashboard":
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Ciro (USD)", f"${df_f['TUTAR'].sum():,.2f}")
    c2.metric("Toplam Adet", f"{int(df_f['ADET'].sum()):,}")
    c3.metric("Firma Sayısı", len(df_f['FIRMA'].unique()))
    c4.metric("Kategori Sayısı", len(df_f['TUR'].unique()))
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Firma Bazlı Harcama")
        fig1 = px.bar(df_f.groupby('FIRMA')['TUTAR'].sum().nlargest(10).reset_index(), x='TUTAR', y='FIRMA', orientation='h', template="plotly_dark")
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        st.subheader("Kategori Dağılımı")
        fig2 = px.pie(df_f, values='TUTAR', names='TUR', hole=0.5, template="plotly_dark")
        st.plotly_chart(fig2, use_container_width=True)

elif page == "Firma Detay Analizi":
    firm = st.selectbox("Firma Seçin:", sorted(df['FIRMA'].dropna().unique()))
    f_df = df_f[df_f['FIRMA'] == firm]
    
    # Hata yapmayan güvenli DataFrame gösterimi
    st.dataframe(f_df[['AY', 'MALIN CINSI', 'ADET', 'TUTAR']], use_container_width=True)

else:
    st.dataframe(df_f, use_container_width=True)