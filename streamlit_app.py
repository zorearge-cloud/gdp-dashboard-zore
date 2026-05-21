import streamlit as st
import pandas as pd
import plotly.express as px

# Sayfa Yapılandırması
st.set_page_config(page_title="ZORE PANEL", layout="wide")

# Veri Yükleme Fonksiyonu
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
    df = pd.read_csv(url)
    
    # Sütun isimlerini temizle (Sadece baş ve sondaki boşlukları al, aradaki boşluk kalsın)
    df.columns = df.columns.str.strip()
    
    # ADET temizliği
    df['ADET'] = pd.to_numeric(df['ADET'], errors='coerce').fillna(0)
    
    # FIYAT temizliği ('¥' ve ',' karakterlerini kaldır, sayıya çevir)
    df['FIYAT_NUM'] = df['FIYAT'].astype(str).str.replace('¥', '', regex=False).str.replace(',', '.', regex=False)
    df['FIYAT_NUM'] = pd.to_numeric(df['FIYAT_NUM'], errors='coerce').fillna(0)
    
    # TUTAR hesapla
    df['TUTAR'] = df['ADET'] * df['FIYAT_NUM']
    
    return df

try:
    df = load_data()

    # --- PANEL ---
    st.title("📊 ZORE SİPARİŞ KONTROL MERKEZİ")

    # KPI Kartları
    c1, c2, c3 = st.columns(3)
    c1.metric("Toplam Harcama", f"¥{df['TUTAR'].sum():,.2f}")
    c2.metric("Toplam Adet", f"{int(df['ADET'].sum()):,}")
    c3.metric("Toplam Firma", len(df['FIRMA'].unique()))

    st.markdown("---")

    # --- GRAFİKLER ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Firma Bazlı Harcama")
        # FIRMA bazlı gruplama
        fig1 = px.bar(df.groupby('FIRMA')['TUTAR'].sum().reset_index().nlargest(10, 'TUTAR'), 
                      x='FIRMA', y='TUTAR', template="plotly_dark", color_discrete_sequence=['#3b82f6'])
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader("Ürün Bazlı Adet (İlk 10)")
        # 'MALIN CINSI' olarak düzeltildi (boşluklu hali)
        fig2 = px.bar(df.groupby('MALIN CINSI')['ADET'].sum().reset_index().nlargest(10, 'ADET'), 
                      x='MALIN CINSI', y='ADET', template="plotly_dark", color_discrete_sequence=['#a855f7'])
        st.plotly_chart(fig2, use_container_width=True)

    # Ham Veri
    with st.expander("Ham Veriyi Görüntüle"):
        st.dataframe(df)

except Exception as e:
    st.error(f"Hata oluştu, lütfen kodu kontrol edin: {e}")