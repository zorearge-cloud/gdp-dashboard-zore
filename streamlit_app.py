import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Sayfa Yapısı ve Başlık Ayarları
st.set_page_config(page_title="Zore Sipariş Takip Paneli", layout="wide")

st.title("📊 ZORE SİPARİŞ KONTROL MERKEZ CENTER")
st.write("---")

# 2. GOOGLE SHEETS ENTEGRASYONU
# Buraya senin az önce güncellediğin ve herkese açık yaptığın Google Sheets linkini koyduk
SHEETS_URL = "https://docs.google.com/spreadsheets/d/1XgX0mN2Gz1_Wc-8gGj997pYqZ_GgO_L9S06I76yC50s/export?format=csv"

@st.cache_data(ttl=30) # Veriyi 30 saniyede bir arkada otomatik tazeler
def load_data():
    df = pd.read_csv(SHEETS_URL)
    df.columns = df.columns.str.strip() # Sütun isimlerindeki boşlukları temizler
    return df

try:
    df = load_data()

    # 3. Üst Özet Kartları (Metrikler) - Streamlit'in orijinal güvenli yapısı
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Total Sipariş Kalemi", value=f"{len(df)} Satır")
    with col2:
        toplam_adet = int(df['ADET'].sum()) if 'ADET' in df.columns else 0
        st.metric(label="Toplam Ürün Adeti", value=f"{toplam_adet:,}")
    with col3:
        tur_counts = df['TUR'].value_counts() if 'TUR' in df.columns else {}
        hava_count = tur_counts.get('HAVA', 0) + tur_counts.get('UÇAK', 0)
        st.metric(label="Hava / Uçak Sevkiyatı", value=f"{hava_count} Hat")
    with col4:
        deniz_count = tur_counts.get('GEMİ', 0) + tur_counts.get('DENİZ', 0)
        st.metric(label="Gemi / Deniz Sevkiyatı", value=f"{deniz_count} Hat")

    st.write("---")

    # 4. Grafikler
    left_chart, right_chart = st.columns(2)

    with left_chart:
        if 'FIRMA' in df.columns and 'ADET' in df.columns:
            st.subheader("📈 Firma Bazlı Yükleme Hacimleri (Adet)")
            fig1 = px.bar(
                df, x='FIRMA', y='ADET', 
                color='TUR' if 'TUR' in df.columns else None,
                template='plotly_dark',
                barmode='stack'
            )
            st.plotly_chart(fig1, use_container_width=True)

    with right_chart:
        if 'MALIN CINSI' in df.columns and 'ADET' in df.columns:
            st.subheader("📦 En Çok Sipariş Edilen Ürün Tipleri")
            top_products = df.groupby('MALIN CINSI')['ADET'].sum().reset_index().sort_values(by='ADET', ascending=False).head(10)
            fig2 = px.bar(
                top_products, x='ADET', y='MALIN CINSI', 
                orientation='h', template='plotly_dark'
            )
            st.plotly_chart(fig2, use_container_width=True)

    # 5. Alt Kısım Detaylı Tablo
    st.write("---")
    st.subheader("📋 Tüm Siparişlerin Güncel Listesi")
    st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"Veri çekilirken hata oluştu: {e}")
    st.info("Lütfen tablonuzdaki sütun isimlerinin büyük harflerle FIRMA, ADET, TUR, MALIN CINSI olduğunu kontrol edin.")