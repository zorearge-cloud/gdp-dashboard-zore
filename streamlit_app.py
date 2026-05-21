import streamlit as st
import pandas as pd
import plotly.express as px
import re

# Sayfa Ayarları
st.set_page_config(page_title="ZORE GLOBAL ERP", layout="wide")

# CSS
st.markdown("""
    <style>
    div.stMetric { background-color: #1e293b; padding: 15px; border-radius: 10px; border: 1px solid #334155; }
    </style>
""", unsafe_allow_html=True)

# 1. KUR AYARLARI (Sidebar'dan güncellenebilir)
st.sidebar.title("💱 Kur Ayarları")
usd_rate = st.sidebar.number_input("1 USD (Baz Kur)", value=1.0, step=0.1)
cny_rate = st.sidebar.number_input("1 Yuan (USD Karşılığı)", value=0.14, step=0.01)

# Veri Yükleme
@st.cache_data(ttl=600)
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    
    # Kur dönüşüm fonksiyonu
    def calculate_usd(row):
        price_str = str(row['FIYAT'])
        adet = float(row['ADET'])
        
        # Sadece rakamları ve noktayı al
        numeric_val = float(re.sub(r'[^\d.]', '', price_str.replace(',', '.')))
        
        # Sembole göre kur belirle
        if '¥' in price_str:
            return numeric_val * cny_rate * adet
        else: # Varsayılan Dolar
            return numeric_val * usd_rate * adet

    df['ADET'] = pd.to_numeric(df['ADET'], errors='coerce').fillna(0)
    df['TUTAR_USD'] = df.apply(calculate_usd, axis=1) # Dolar bazlı gerçek tutar
    
    # Tarih İşleme
    df['SIPARIS_TARIHI'] = pd.to_datetime(df['SIPARIS_TARIHI'], dayfirst=True, errors='coerce')
    df['AY'] = df['SIPARIS_TARIHI'].dt.to_period('M').astype(str)
    
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Veri yükleme hatası: {e}")
    st.stop()

# Menü
page = st.sidebar.radio("Seçenekler", ["Dashboard", "Firma Detay Analizi", "Ham Veri"])

# --- DASHBOARD ---
if page == "Dashboard":
    st.title("📈 Genel Özet (USD Bazlı)")
    
    # Metrikler (Artık TUTAR_USD üzerinden çalışıyor)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Harcama (USD)", f"${df['TUTAR_USD'].sum():,.2f}")
    c2.metric("Toplam Adet", f"{int(df['ADET'].sum()):,}")
    c3.metric("Aktif Firma", len(df['FIRMA'].unique()))
    c4.metric("Ürün Çeşidi", len(df['MALIN CINSI'].unique()))
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("En Büyük 10 Harcama (USD)")
        fig1 = px.bar(df.groupby('FIRMA')['TUTAR_USD'].sum().nlargest(10).reset_index(), 
                      x='TUTAR_USD', y='FIRMA', orientation='h', template="plotly_dark", color='TUTAR_USD')
        st.plotly_chart(fig1, use_container_width=True)
        
    with col2:
        st.subheader("Aylık Ciro Trendi (USD)")
        fig2 = px.line(df.groupby('AY')['TUTAR_USD'].sum().reset_index(), 
                       x='AY', y='TUTAR_USD', markers=True, template="plotly_dark")
        st.plotly_chart(fig2, use_container_width=True)

# --- FİRMA DETAY ---
elif page == "Firma Detay Analizi":
    st.title("🏢 Firma Detay Analizi")
    selected_firm = st.selectbox("Analiz edilecek firmayı seçin:", sorted(df['FIRMA'].unique()))
    
    firm_df = df[df['FIRMA'] == selected_firm]
    
    k1, k2 = st.columns(2)
    k1.metric("Bu Firmaya Harcama (USD)", f"${firm_df['TUTAR_USD'].sum():,.2f}")
    k2.metric("Sipariş Adet", int(firm_df['ADET'].sum()))
    
    st.subheader(f"Sipariş Listesi ({selected_firm})")
    st.dataframe(firm_df[['SIPARIS_TARIHI', 'MALIN CINSI', 'ADET', 'FIYAT', 'TUTAR_USD']], use_container_width=True)

else:
    st.title("🗄️ Tüm Kayıtlar")
    st.dataframe(df, use_container_width=True)