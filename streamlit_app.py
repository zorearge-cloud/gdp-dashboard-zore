import streamlit as st
import pandas as pd
import plotly.express as px
import re

# 1. Sayfa ve Tasarım Ayarları
st.set_page_config(page_title="ZORE PRO DASHBOARD", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: white; }
    .css-1r6slb0 { background-color: #161b22; }
    .metric-card { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 15px; padding: 20px; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# 2. Kurşun Geçirmez Veri Yükleme Fonksiyonu
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
    df = pd.read_csv(url)
    # Sütun isimlerini temizle (boşlukları sil)
    df.columns = df.columns.str.strip()
    
    # ADET temizliği
    df['ADET'] = pd.to_numeric(df['ADET'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
    
    # FİYAT temizliği (Sembollerden arındırıp sayıya çevir)
    def clean_price(x):
        s = str(x).replace('¥', '').replace('$', '').replace(',', '.')
        # Sadece sayı ve nokta kalsın
        s = re.sub(r'[^\d.]', '', s)
        try: return float(s)
        except: return 0.0
        
    df['FIYAT_NUM'] = df['FIYAT'].apply(clean_price)
    df['TUTAR'] = df['ADET'] * df['FIYAT_NUM']
    return df

try:
    df = load_data()
    
    # 3. Arayüz
    st.title("🚀 ZORE GLOBAL CONTROL CENTER")
    
    # KPI Metrikleri
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Harcama", f"¥{df['TUTAR'].sum():,.0f}")
    c2.metric("Toplam Adet", f"{int(df['ADET'].sum()):,}")
    c3.metric("Aktif Firma", df['FIRMA'].nunique())
    c4.metric("Ürün Çeşidi", df['MALIN CINSI'].nunique())
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 4. Modern Grafik Alanları
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("Firma Bazlı Harcama")
        fig1 = px.bar(df.groupby('FIRMA')['TUTAR'].sum().nlargest(10).reset_index(), 
                      x='TUTAR', y='FIRMA', orientation='h', template="plotly_dark", color_discrete_sequence=['#58a6ff'])
        fig1.update_layout(yaxis={'categoryorder':'total ascending'}, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig1, use_container_width=True)
        
    with col_b:
        st.subheader("Ürün Bazlı Adet (İlk 10)")
        fig2 = px.bar(df.groupby('MALIN CINSI')['ADET'].sum().nlargest(10).reset_index(), 
                      x='ADET', y='MALIN CINSI', orientation='h', template="plotly_dark", color_discrete_sequence=['#af85ff'])
        fig2.update_layout(yaxis={'categoryorder':'total ascending'}, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig2, use_container_width=True)

except Exception as e:
    st.error(f"Sistem Hatası: {e}. Lütfen Sheets sütunlarının (FIRMA, ADET, FIYAT) doğru yazıldığından emin olun.")