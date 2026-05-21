import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Sayfa Yapısı ve Karanlık Tema Ayarları
st.set_page_config(page_title="Zore Sipariş Takip Paneli", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #f0f6fc; }
    .metric-card { 
        background-color: #161b22; 
        border: 1px solid #30363d; 
        padding: 22px; 
        border-radius: 12px; 
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.4);
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 ZORE SİPARİŞ KONTROL MERKEZİ")
st.write("---")

# 2. GOOGLE SHEETS ENTEGRASYONU
# Buraya AppSheet'te bağladığın ana Google Sheets dokümanının CSV export linkini koyuyoruz
SHEETS_URL = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"

@st.cache_data(ttl=60) # Veriyi dakikada bir otomatik yeniler
def load_data():
    df = pd.read_csv(SHEETS_URL)
    df.columns = df.columns.str.strip() # Sütun başlarındaki boşlukları temizler
    return df

try:
    df = load_data()

    # 3. Üst Özet Kartları (Metrikler)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><h3 style="color:#58a6ff;margin:0;">Toplam Sipariş</h3><h2 style="margin:10px 0 0 0;font-size:32px;">{len(df)} Kalem</h2></div>', unsafe_allow_index=True)
    with col2:
        toplam_adet = int(df['ADET'].sum()) if 'ADET' in df.columns else 0
        st.markdown(f'<div class="metric-card"><h3 style="color:#238636;margin:0;">Toplam Ürün Adeti</h3><h2 style="margin:10px 0 0 0;font-size:32px;">{toplam_adet:,}</h2></div>', unsafe_allow_index=True)
    with col3:
        tur_counts = df['TUR'].value_counts() if 'TUR' in df.columns else {}
        hava_count = tur_counts.get('HAVA', 0) + tur_counts.get('UÇAK', 0)
        st.markdown(f'<div class="metric-card"><h3 style="color:#f0883b;margin:0;">Hava / Uçak Sevkiyatı</h3><h2 style="margin:10px 0 0 0;font-size:32px;">{hava_count} Hat</h2></div>', unsafe_allow_index=True)
    with col4:
        deniz_count = tur_counts.get('GEMİ', 0) + tur_counts.get('DENİZ', 0)
        st.markdown(f'<div class="metric-card"><h3 style="color:#bc8cf2;margin:0;">Gemi / Deniz Sevkiyatı</h3><h2 style="margin:10px 0 0 0;font-size:32px;">{deniz_count} Hat</h2></div>', unsafe_allow_index=True)

    st.write("---")

    # 4. Grafikler (Firma ve Malın Cinsine Göre Yoğunluklar)
    left_chart, right_chart = st.columns(2)

    with left_chart:
        if 'FIRMA' in df.columns and 'ADET' in df.columns:
            st.subheader("📈 Firma Bazlı Yükleme Hacimleri (Adet)")
            fig1 = px.bar(
                df, x='FIRMA', y='ADET', 
                color='TUR' if 'TUR' in df.columns else None,
                template='plotly_dark',
                barmode='stack',
                color_discrete_map={'GEMİ': '#58a6ff', 'DENİZ': '#58a6ff', 'UÇAK': '#238636', 'HAVA': '#f0883b'}
            )
            fig1.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig1, use_container_width=True)

    with right_chart:
        if 'MALIN CINSI' in df.columns and 'ADET' in df.columns:
            st.subheader("📦 En Çok Sipariş Edilen Ürün Tipleri")
            top_products = df.groupby('MALIN CINSI')['ADET'].sum().reset_index().sort_values(by='ADET', ascending=False).head(10)
            fig2 = px.bar(
                top_products, x='ADET', y='MALIN CINSI', 
                orientation='h', template='plotly_dark',
                color_discrete_sequence=['#bc8cf2']
            )
            fig2.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig2, use_container_width=True)

    # 5. Alt Kısım Detaylı Tablo
    st.write("---")
    st.subheader("📋 Tüm Siparişlerin Güncel Listesi")
    st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"Veri çekilirken hata oluştu: {e}")
    st.info("Lütfen tablonuzdaki sütun isimlerinin büyük harflerle FIRMA, ADET, TUR, MALIN CINSI olduğunu kontrol edin.")