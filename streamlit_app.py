import streamlit as st
import pandas as pd
import plotly.express as px

# Sayfa Yapılandırması
st.set_page_config(page_title="ZORE PANEL", layout="wide")

# Veri Yükleme ve Temizleme
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip().str.upper() # Sütun isimlerini sabitle
    
    # 1. ADET sütununu sayıya çevir
    df['ADET'] = pd.to_numeric(df['ADET'], errors='coerce').fillna(0)
    
    # 2. FIYAT sütununu temizle (¥ işaretini kaldır, virgülü noktaya çevir)
    df['FIYAT_NUM'] = df['FIYAT'].astype(str).str.replace('¥', '', regex=True).str.replace(',', '.', regex=True)
    df['FIYAT_NUM'] = pd.to_numeric(df['FIYAT_NUM'], errors='coerce').fillna(0)
    
    # 3. TUTAR'ı hesapla (Adet * Fiyat)
    df['TUTAR'] = df['ADET'] * df['FIYAT_NUM']
    
    return df

# Veriyi çek
df = load_data()

# --- PANEL BAŞLIĞI ---
st.title("📊 ZORE SİPARİŞ KONTROL MERKEZİ")

# --- KPI KARTLARI ---
c1, c2, c3 = st.columns(3)
c1.metric("Toplam Harcama (Hesaplanan)", f"{df['TUTAR'].sum():,.2f}")
c2.metric("Toplam Adet", f"{int(df['ADET'].sum()):,}")
c3.metric("Firma Sayısı", len(df['FIRMA'].unique()))

st.markdown("---")

# --- GRAFİKLER ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Firma Bazlı Harcama Dağılımı")
    fig1 = px.bar(df.groupby('FIRMA')['TUTAR'].sum().reset_index().nlargest(10, 'TUTAR'), 
                  x='FIRMA', y='TUTAR', template="plotly_dark", color_discrete_sequence=['#3b82f6'])
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("En Çok Sipariş Edilen Ürünler (Adet)")
    fig2 = px.bar(df.groupby('MALIN_CINSI')['ADET'].sum().reset_index().nlargest(10, 'ADET'), 
                  x='MALIN_CINSI', y='ADET', template="plotly_dark", color_discrete_sequence=['#a855f7'])
    st.plotly_chart(fig2, use_container_width=True)

# --- ALT TABLO ---
st.subheader("Tüm Sipariş Listesi")
st.dataframe(df, use_container_width=True)