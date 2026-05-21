import streamlit as st
import pandas as pd
import plotly.express as px

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="ZORE PANEL", layout="wide")

# Özel CSS ile Dark Modu pekiştiriyoruz
st.markdown("""
    <style>
    .main { background-color: #0f172a; }
    .stMetric { background-color: #1e293b; padding: 15px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- VERİ YÜKLEME ---
# Burayı kendi veri kaynağınla güncelle
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip().str.upper()
    return df

df = load_data()

# --- BAŞLIK ---
st.title("📊 ZORE SİPARİŞ KONTROL MERKEZİ")

# --- 1. SATIR: KPI KARTLARI ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Toplam Harcama", f"${df['TUTAR_USD'].sum():,.2f}")
c2.metric("Bütçe Kullanımı", "%46.5") # Buraya kendi hesaplamanı ekleyebilirsin
c3.metric("Toplam Adet", f"{df['ADET'].sum():,.0f}")
c4.metric("Kalan Bütçe", "$962,549.27")

st.markdown("---")

# --- 2. SATIR: ORTA GRAFİKLER (3'lü Yapı) ---
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("En Maliyetli 10 Ürün")
    fig1 = px.bar(df.nlargest(10, 'TUTAR_USD'), x='URUN', y='TUTAR_USD', template="plotly_dark")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("En Çok Sipariş Edilen 10 Ürün")
    fig2 = px.bar(df.nlargest(10, 'ADET'), x='URUN', y='ADET', template="plotly_dark", color_discrete_sequence=['#a855f7'])
    st.plotly_chart(fig2, use_container_width=True)

with col3:
    st.subheader("Lojistik Dağılımı")
    fig3 = px.pie(df, names='NAKLIYE_TURU', hole=0.6, template="plotly_dark")
    st.plotly_chart(fig3, use_container_width=True)

# --- 3. SATIR: ALT GRAFİKLER (2'li Yapı) ---
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("En Yüksek Hacimli 10 Tedarikçi")
    top_tedarikci = df.groupby('FIRMA')['TUTAR_USD'].sum().nlargest(10).reset_index()
    fig4 = px.bar(top_tedarikci, x='FIRMA', y='TUTAR_USD', template="plotly_dark", color_discrete_sequence=['#3b82f6'])
    st.plotly_chart(fig4, use_container_width=True)

with col_right:
    st.subheader("Ürün Kategorisi Dağılımı")
    cat_dist = df.groupby('TUR')['ADET'].sum().reset_index()
    fig5 = px.bar(cat_dist, x='TUR', y='ADET', template="plotly_dark")
    st.plotly_chart(fig5, use_container_width=True)