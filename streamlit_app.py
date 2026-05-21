import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# --- 1. AYARLAR VE SAYFA YAPISI ---
st.set_page_config(page_title="ZORE PRO MASTER", layout="wide")

# CSS ile Dashboard Görünümünü Profesyonelleştir
st.markdown("""
    <style>
    .stMetric { background-color: #0e1117; padding: 15px; border-radius: 10px; border: 1px solid #464e5f; }
    </style>
""", unsafe_allow_html=True)

# 5 Link Sabit
URLS = [
    "https://docs.google.com/spreadsheets/d/1j819WkX93CkCy3VgZkSff5C_zNX5Z98jfK-FwI4ZWUU/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1hVk6VgMFXWAukoQwMDIoOLrG8SD4UDLFFRH9VmDhXSE/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1S1kTptWUEf705cBLw9P9mL6rrqbVjbcp1xk_hgQ-Ny0/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1VKb6za4Fse5XrGawPG6qvrQZuFhDRGaAysmADGIC7Wc/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
]

# --- 2. VERİ MOTORU (Geliştirilmiş) ---
@st.cache_data(ttl=3600)
def load_and_process():
    all_dfs = []
    for url in URLS:
        try:
            df = pd.read_csv(url)
            all_dfs.append(df)
        except: continue
    
    master_df = pd.concat(all_dfs, ignore_index=True)
    master_df.columns = master_df.columns.str.strip()
    
    # Tarih ve Temizlik
    master_df['SIPARIS_TARIHI'] = pd.to_datetime(master_df['SIPARIS_TARIHI'], dayfirst=True, errors='coerce')
    master_df['AY'] = master_df['SIPARIS_TARIHI'].dt.to_period('M').astype(str)
    master_df['ADET'] = pd.to_numeric(master_df['ADET'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
    
    # Fiyat Hesaplama
    def calc_tutar(row):
        val_str = str(row['FIYAT'])
        nums = re.sub(r'[^\d.]', '', val_str.replace(',', '.'))
        price = float(nums) if nums else 0.0
        # ¥ varsa 0.14, yoksa dolar
        return (price * 0.14 * row['ADET']) if '¥' in val_str else (price * row['ADET'])

    master_df['TUTAR'] = master_df.apply(calc_tutar, axis=1)
    return master_df

df = load_and_process()

# --- 3. DASHBOARD YÖNETİMİ ---
st.sidebar.title("🔍 ZORE KONTROL")
page = st.sidebar.radio("Sayfalar", ["Genel Dashboard", "Firma Detay Analizi", "Ham Veri"])

# Filtreleme (Global)
selected_months = st.sidebar.multiselect("Ay Seçimi", sorted(df['AY'].dropna().unique(), reverse=True), default=sorted(df['AY'].dropna().unique(), reverse=True))
df_filtered = df[df['AY'].isin(selected_months)]

# --- 4. SAYFA: GENEL DASHBOARD ---
if page == "Genel Dashboard":
    st.title("📈 Yönetici Özet Paneli")
    
    # Üst Bilgi Kartları
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Ciro (USD)", f"${df_filtered['TUTAR'].sum():,.2f}")
    c2.metric("Toplam Adet", f"{int(df_filtered['ADET'].sum()):,}")
    c3.metric("Firma Sayısı", len(df_filtered['FIRMA'].unique()))
    c4.metric("Kategori Sayısı", len(df_filtered['TUR'].unique()))
    
    st.markdown("---")
    
    # Grafik Grubu 1: Trend ve Dağılım
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🗓️ Aylık Ciro Trendi")
        trend_data = df_filtered.groupby('AY')['TUTAR'].sum().reset_index()
        fig1 = px.line(trend_data, x='AY', y='TUTAR', markers=True, template="plotly_dark")
        st.plotly_chart(fig1, use_container_width=True)
        
    with col2:
        st.subheader("📂 Kategori Payı (TUR)")
        cat_data = df_filtered.groupby('TUR')['TUTAR'].sum().reset_index()
        fig2 = px.pie(cat_data, values='TUTAR', names='TUR', hole=0.5, template="plotly_dark")
        st.plotly_chart(fig2, use_container_width=True)

    # Grafik Grubu 2: Top 10 Analizleri
    col3, col4 = st.columns(2)
    with col3:
        st.subheader("🏢 Top 10 Firma (Harcanan)")
        top_f = df_filtered.groupby('FIRMA')['TUTAR'].sum().nlargest(10).reset_index()
        fig3 = px.bar(top_f, x='TUTAR', y='FIRMA', orientation='h', template="plotly_dark", color='TUTAR')
        st.plotly_chart(fig3, use_container_width=True)
        
    with col4:
        st.subheader("📦 Top 10 Ürün (Ciro)")
        top_p = df_filtered.groupby('MALIN CINSI')['TUTAR'].sum().nlargest(10).reset_index()
        fig4 = px.bar(top_p, x='TUTAR', y='MALIN CINSI', orientation='h', template="plotly_dark", color='TUTAR')
        st.plotly_chart(fig4, use_container_width=True)

# --- 5. SAYFA: FİRMA DETAY ---
elif page == "Firma Detay Analizi":
    st.title("🏢 Firma Detay Analizi")
    firm = st.selectbox("Analiz Edilecek Firma:", sorted(df['FIRMA'].unique()))
    f_df = df_filtered[df_filtered['FIRMA'] == firm]
    
    # Firma Özel Metrikler
    k1, k2, k3 = st.columns(3)
    k1.metric("Toplam Harcama", f"${f_df['TUTAR'].sum():,.2f}")
    k2.metric("Sipariş Sayısı", len(f_df))
    k3.metric("Ürün Çeşidi", len(f_df['MALIN CINSI'].unique()))
    
    st.markdown("---")
    
    # Firma İçin Grafik
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.subheader("Ürün Dağılımı")
        prod_dist = f_df.groupby('MALIN CINSI')['ADET'].sum().nlargest(5).reset_index()
        fig_f1 = px.pie(prod_dist, values='ADET', names='MALIN CINSI', hole=0.4, template="plotly_dark")
        st.plotly_chart(fig_f1, use_container_width=True)
        
    with col_b:
        st.subheader("Sipariş Akışı")
        st.dataframe(f_df[['AY', 'BARKOD', 'MALIN CINSI', 'TUR', 'ADET', 'TUTAR']], use_container_width=True)

# --- 6. SAYFA: HAM VERİ ---
else:
    st.title("🗄️ Master Veri Tablosu")
    st.dataframe(df_filtered, use_container_width=True)