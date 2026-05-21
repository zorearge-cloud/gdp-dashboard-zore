import streamlit as st
import pandas as pd
import plotly.express as px
import re

# Sayfa Ayarları
st.set_page_config(page_title="ZORE PRO PANEL", layout="wide")

# Veri Motoru (Arka planda otomatik temizler ve hesaplar)
@st.cache_data(ttl=600)
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    
    # 1. Adet Temizleme
    df['ADET'] = pd.to_numeric(df['ADET'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
    
    # 2. Kur ve Fiyat Temizleme (Otomatik Hesaplama)
    def calculate_usd(row):
        val_str = str(row['FIYAT'])
        # Rakamları ve noktayı ayıkla
        clean_val = re.sub(r'[^\d.]', '', val_str.replace(',', '.'))
        if clean_val == '': return 0.0
        price = float(clean_val)
        
        # Eğer Yuan sembolü varsa 0.14 ile çarp, yoksa direkt dolar kabul et
        if '¥' in val_str:
            return price * 0.14 * row['ADET']
        return price * row['ADET']

    df['TUTAR'] = df.apply(calculate_usd, axis=1)
    
    # Boş satırları temizle
    df = df[df['FIRMA'].notna()]
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Veri yükleme hatası: {e}. Lütfen Sheets dosyasını kontrol et.")
    st.stop()

# --- ALTIN ÜÇLÜ YAPISI ---
st.sidebar.title("🔍 ZORE KONTROL")
page = st.sidebar.radio("Sayfalar", ["Dashboard", "Firma Detay Analizi", "Ham Veri"])

# 1. DASHBOARD
if page == "Dashboard":
    st.title("📈 Genel Özet Paneli")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Harcama (USD)", f"${df['TUTAR'].sum():,.2f}")
    c2.metric("Toplam Adet", f"{int(df['ADET'].sum()):,}")
    c3.metric("Aktif Firma", len(df['FIRMA'].unique()))
    c4.metric("Ürün Çeşidi", len(df['MALIN CINSI'].unique()))
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("En Büyük 10 Harcama Kalemi")
        fig1 = px.bar(df.groupby('FIRMA')['TUTAR'].sum().nlargest(10).reset_index(), 
                      x='TUTAR', y='FIRMA', orientation='h', template="plotly_dark", color='TUTAR')
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        st.subheader("Ürün Payları")
        top_products = df.groupby('MALIN CINSI')['TUTAR'].sum().nlargest(10).reset_index()
        fig2 = px.pie(top_products, values='TUTAR', names='MALIN CINSI', hole=0.4, template="plotly_dark")
        st.plotly_chart(fig2, use_container_width=True)

# 2. FİRMA DETAY ANALİZİ
elif page == "Firma Detay Analizi":
    st.title("🏢 Firma Detay Analizi")
    selected_firm = st.selectbox("Analiz edilecek firmayı seçin:", sorted(df['FIRMA'].unique()))
    firm_df = df[df['FIRMA'] == selected_firm]
    
    k1, k2 = st.columns(2)
    k1.metric("Bu Firmaya Harcama", f"${firm_df['TUTAR'].sum():,.2f}")
    k2.metric("Sipariş Adet", int(firm_df['ADET'].sum()))
    
    st.markdown("---")
    st.subheader(f"En Çok Sipariş Edilen Ürünler ({selected_firm})")
    fig_firm = px.bar(firm_df.groupby('MALIN CINSI')['ADET'].sum().nlargest(10).reset_index(), 
                      x='ADET', y='MALIN CINSI', orientation='h', template="plotly_dark", color='ADET')
    st.plotly_chart(fig_firm, use_container_width=True)
    
    st.subheader("Sipariş Kalemleri")
    st.dataframe(firm_df[['MALIN CINSI', 'ADET', 'TUTAR']], use_container_width=True)

# 3. HAM VERİ
else:
    st.title("🗄️ Tüm Kayıtlar")
    st.dataframe(df, use_container_width=True)