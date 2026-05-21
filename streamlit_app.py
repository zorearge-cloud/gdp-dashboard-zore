import streamlit as st
import pandas as pd
import plotly.express as px

# Sayfa Ayarları
st.set_page_config(page_title="ZORE PRO PANEL", layout="wide", initial_sidebar_state="expanded")

# CSS - Tasarım
st.markdown("""
    <style>
    div.stMetric { background-color: #1e293b; padding: 15px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# Veri Yükleme
@st.cache_data(ttl=600)
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    df['ADET'] = pd.to_numeric(df['ADET'], errors='coerce').fillna(0)
    df['FIYAT_NUM'] = df['FIYAT'].astype(str).str.replace('¥', '', regex=False).str.replace(',', '.', regex=False)
    df['FIYAT_NUM'] = pd.to_numeric(df['FIYAT_NUM'], errors='coerce').fillna(0)
    df['TUTAR'] = df['ADET'] * df['FIYAT_NUM']
    return df

try:
    df = load_data()
except:
    st.error("Veri yükleme hatası!")
    st.stop()

# Sol Menü
st.sidebar.title("🔍 ZORE KONTROL")
page = st.sidebar.radio("Seçenekler", ["Dashboard", "Firma Detay Analizi", "Ham Veri"])

# --- DASHBOARD ---
if page == "Dashboard":
    st.title("📈 Genel Özet Paneli")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Harcama", f"¥{df['TUTAR'].sum():,.0f}")
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
        st.subheader("En Çok Harcama Yapılan İlk 10 Ürün")
        # Grafiği bozan şey tüm veriyi basmaktı, şimdi sadece ilk 10'u basıyoruz.
        top_products = df.groupby('MALIN CINSI')['TUTAR'].sum().nlargest(10).reset_index()
        fig2 = px.pie(top_products, values='TUTAR', names='MALIN CINSI', hole=0.4, template="plotly_dark")
        st.plotly_chart(fig2, use_container_width=True)

# --- FİRMA DETAY ---
elif page == "Firma Detay Analizi":
    st.title("🏢 Firma Detay Analizi")
    selected_firm = st.selectbox("Analiz edilecek firmayı seçin:", sorted(df['FIRMA'].unique()))
    
    firm_df = df[df['FIRMA'] == selected_firm]
    
    k1, k2 = st.columns(2)
    k1.metric("Bu Firmaya Harcama", f"¥{firm_df['TUTAR'].sum():,.0f}")
    k2.metric("Sipariş Adet", int(firm_df['ADET'].sum()))
    
    st.markdown("---")
    
    # GRAFİK: Sadece ilk 10 ürün (Yatay Bar Grafiği)
    st.subheader(f"En Çok Sipariş Edilen İlk 10 Ürün ({selected_firm})")
    top_firm_products = firm_df.groupby('MALIN CINSI')['ADET'].sum().nlargest(10).reset_index()
    fig_firm = px.bar(top_firm_products, x='ADET', y='MALIN CINSI', orientation='h', template="plotly_dark", color='ADET')
    st.plotly_chart(fig_firm, use_container_width=True)
    
    # Tablo
    st.subheader("Sipariş Kalemleri (Detaylı Liste)")
    st.dataframe(firm_df[['MALIN CINSI', 'ADET', 'FIYAT', 'TUTAR']], use_container_width=True)

# --- HAM VERİ ---
else:
    st.title("🗄️ Tüm Kayıtlar")
    st.dataframe(df, use_container_width=True)