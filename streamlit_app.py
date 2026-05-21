import streamlit as st
import pandas as pd
import plotly.express as px
import re

# 1. Sayfa Ayarları
st.set_page_config(page_title="ZORE ANALİZ", layout="wide")

# 2. Veri Yükleme ve Gelişmiş Temizleme
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
    df = pd.read_csv(url)
    
    # Sütun isimlerini temizle (baş ve sondaki boşlukları sil)
    df.columns = df.columns.str.strip()
    
    # ADET temizleme (Sadece sayıları al)
    df['ADET'] = pd.to_numeric(df['ADET'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
    
    # FIYAT temizleme (Sembolleri at, virgülü noktaya çevir)
    # Bu satır, $6.41 veya ¥1,48 gibi tüm formatları float sayıya çevirir
    def clean_currency(val):
        val = str(val).replace('¥', '').replace('$', '').replace(',', '.')
        # Sadece sayı ve nokta kalsın
        val = re.sub(r'[^\d.]', '', val)
        try:
            return float(val)
        except:
            return 0.0

    df['FIYAT_NUM'] = df['FIYAT'].apply(clean_currency)
    
    # TUTAR hesaplama
    df['TUTAR'] = df['ADET'] * df['FIYAT_NUM']
    return df

# 3. Ana Uygulama
try:
    df = load_data()
    
    st.title("🚀 ZORE YÖNETİM PANELİ")
    
    # KPI Kartları
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Toplam Harcama", f"¥{df['TUTAR'].sum():,.2f}")
    col2.metric("Toplam Adet", f"{int(df['ADET'].sum()):,}")
    col3.metric("Aktif Firma Sayısı", df['FIRMA'].nunique())
    col4.metric("Ürün Çeşidi", df['MALIN CINSI'].nunique())
    
    st.markdown("---")
    
    # Grafiklerin çizimi
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Firma Bazlı Harcama")
        fig1 = px.bar(df.groupby('FIRMA')['TUTAR'].sum().nlargest(10).reset_index(), 
                      x='TUTAR', y='FIRMA', orientation='h', template="plotly_dark")
        st.plotly_chart(fig1, use_container_width=True)
        
    with c2:
        st.subheader("En Çok Sipariş Edilen Ürünler (Adet)")
        fig2 = px.bar(df.groupby('MALIN CINSI')['ADET'].sum().nlargest(10).reset_index(), 
                      x='ADET', y='MALIN CINSI', orientation='h', template="plotly_dark")
        st.plotly_chart(fig2, use_container_width=True)

except Exception as e:
    st.error(f"Sistem hatası: {e}")
    st.write("Lütfen Google Sheets dosyanızda 'FIRMA', 'MALIN CINSI', 'ADET', 'FIYAT' sütunlarının olduğundan emin olun.")