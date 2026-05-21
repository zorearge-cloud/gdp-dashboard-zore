import streamlit as st
import pandas as pd
import plotly.express as px
import re

# 1. Sayfa Ayarları
st.set_page_config(page_title="ZORE PRO YÖNETİM", layout="wide")

# 2. Veri Temizleme ve Yükleme
@st.cache_data(ttl=600)
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
    df = pd.read_csv(url)
    
    # Sütun isimlerindeki boşlukları temizle
    df.columns = df.columns.str.strip()
    
    # Adet sütununu sayıya çevir (Hata varsa 0 yap)
    df['ADET'] = pd.to_numeric(df['ADET'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
    
    # Fiyat sütununu temizle (Sembolleri at, virgülü noktaya çevir)
    def clean_currency(val):
        s = str(val).replace('¥', '').replace('$', '').replace(',', '.')
        s = re.sub(r'[^\d.]', '', s)
        try: return float(s)
        except: return 0.0

    df['FIYAT_NUM'] = df['FIYAT'].apply(clean_currency)
    df['TUTAR'] = df['ADET'] * df['FIYAT_NUM']
    return df

# 3. Ana Uygulama
try:
    df = load_data()
    
    st.title("🚀 ZORE GLOBAL KONTROL MERKEZİ")
    
    # Özet Metrikler
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Toplam Harcama", f"¥{df['TUTAR'].sum():,.0f}")
    col2.metric("Toplam Adet", f"{int(df['ADET'].sum()):,}")
    col3.metric("Aktif Firma", df['FIRMA'].nunique())
    col4.metric("Ürün Çeşidi", df['MALIN CINSI'].nunique())
    
    st.markdown("---")
    
    # 4 Grafikli Grid Yapısı
    row1_c1, row1_c2 = st.columns(2)
    row2_c1, row2_c2 = st.columns(2)
    
    # 1. Grafik: En Çok Harcama Yapılan Firmalar (Top 10)
    with row1_c1:
        st.subheader("Top 10: En Çok Harcama Yapılan Firma")
        fig1 = px.bar(df.groupby('FIRMA')['TUTAR'].sum().nlargest(10).reset_index(), 
                      x='TUTAR', y='FIRMA', orientation='h', template="plotly_dark", color='TUTAR', color_continuous_scale='Blues')
        fig1.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig1, use_container_width=True)
        
    # 2. Grafik: En Çok Harcama Yapılan Ürünler (Top 10)
    with row1_c2:
        st.subheader("Top 10: En Çok Harcama Yapılan Ürün")
        fig2 = px.bar(df.groupby('MALIN CINSI')['TUTAR'].sum().nlargest(10).reset_index(), 
                      x='TUTAR', y='MALIN CINSI', orientation='h', template="plotly_dark", color='TUTAR', color_continuous_scale='Viridis')
        fig2.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig2, use_container_width=True)

    # 3. Grafik: En Çok Sipariş Edilen Ürünler (Adet Bazlı)
    with row2_c1:
        st.subheader("Top 10: Adet Bazlı Popüler Ürünler")
        fig3 = px.bar(df.groupby('MALIN CINSI')['ADET'].sum().nlargest(10).reset_index(), 
                      x='ADET', y='MALIN CINSI', orientation='h', template="plotly_dark", color='ADET', color_continuous_scale='Reds')
        fig3.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig3, use_container_width=True)
        
    # 4. Grafik: Ürün Kategori Dağılımı (Yüzdesel)
    with row2_c2:
        st.subheader("Ürün Kategori Dağılımı (%)")
        # İlk 10'u al, kalanı "Diğer" yap
        cat_data = df.groupby('MALIN CINSI')['TUTAR'].sum().nlargest(10).reset_index()
        fig4 = px.pie(cat_data, values='TUTAR', names='MALIN CINSI', hole=0.4, template="plotly_dark")
        st.plotly_chart(fig4, use_container_width=True)

except Exception as e:
    st.error(f"Veri işleme hatası: {e}. Lütfen sütun isimlerinin doğruluğunu kontrol edin.")