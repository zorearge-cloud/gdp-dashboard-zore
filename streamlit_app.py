import streamlit as st
import pandas as pd
import plotly.express as px
import re

# Sayfa Ayarları
st.set_page_config(page_title="ZORE PRO PANEL", layout="wide")

# Veri Motoru (Arka planda otomatik hesaplar)
@st.cache_data(ttl=600)
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    
    # Tarih İşleme
    df['SIPARIS_TARIHI'] = pd.to_datetime(df['SIPARIS_TARIHI'], dayfirst=True, errors='coerce')
    df['AY'] = df['SIPARIS_TARIHI'].dt.to_period('M').astype(str)
    
    # Adet Temizleme
    df['ADET'] = pd.to_numeric(df['ADET'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
    
    # Fiyat ve Kur Hesaplama (Otomatik)
    def calculate_usd(row):
        val_str = str(row['FIYAT'])
        clean_val = re.sub(r'[^\d.]', '', val_str.replace(',', '.'))
        price = float(clean_val) if clean_val else 0.0
        
        # Otomatik Kur: ¥ ise 0.14 ile çarp, değilse direkt al
        if '¥' in val_str:
            return price * 0.14 * row['ADET']
        return price * row['ADET']

    df['TUTAR'] = df.apply(calculate_usd, axis=1)
    return df

# Veriyi Yükle
try:
    df = load_data()
except Exception as e:
    st.error(f"Veri yüklenemedi: {e}")
    st.stop()

# --- SİDEBAR ---
st.sidebar.title("🔍 ZORE KONTROL")
page = st.sidebar.radio("Sayfalar", ["Dashboard", "Firma Detay Analizi", "Ham Veri"])

# Global Ay Filtresi
all_months = sorted(df['AY'].dropna().unique(), reverse=True)
selected_months = st.sidebar.multiselect("Ay Seçimi", all_months, default=all_months)
df_filtered = df[df['AY'].isin(selected_months)]

# 1. DASHBOARD
if page == "Dashboard":
    st.title("📈 Genel Özet Paneli")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Harcama (USD)", f"${df_filtered['TUTAR'].sum():,.2f}")
    c2.metric("Toplam Adet", f"{int(df_filtered['ADET'].sum()):,}")
    c3.metric("Aktif Firma", len(df_filtered['FIRMA'].unique()))
    c4.metric("Seçilen Ay", len(selected_months))
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Firma Bazlı Harcama Trendi")
        fig1 = px.bar(df_filtered.groupby('FIRMA')['TUTAR'].sum().nlargest(10).reset_index(), 
                      x='TUTAR', y='FIRMA', orientation='h', template="plotly_dark", color='TUTAR')
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        st.subheader("Aylık Ciro Trendi")
        fig2 = px.line(df_filtered.groupby('AY')['TUTAR'].sum().reset_index(), 
                       x='AY', y='TUTAR', markers=True, template="plotly_dark")
        st.plotly_chart(fig2, use_container_width=True)

# 2. FİRMA DETAY
elif page == "Firma Detay Analizi":
    st.title("🏢 Firma Detay Analizi")
    selected_firm = st.selectbox("Analiz edilecek firmayı seçin:", sorted(df['FIRMA'].unique()))
    firm_df = df_filtered[df_filtered['FIRMA'] == selected_firm]
    
    k1, k2 = st.columns(2)
    k1.metric("Bu Firmaya Harcama", f"${firm_df['TUTAR'].sum():,.2f}")
    k2.metric("Sipariş Adet", int(firm_df['ADET'].sum()))
    
    st.markdown("---")
    st.subheader(f"Sipariş Kalemleri ({selected_firm})")
    # Barkod eklendi
    st.dataframe(firm_df[['SIPARIS_TARIHI', 'BARKOD', 'MALIN CINSI', 'ADET', 'TUTAR']], use_container_width=True)

# 3. HAM VERİ
else:
    st.title("🗄️ Tüm Kayıtlar")
    st.dataframe(df_filtered, use_container_width=True)