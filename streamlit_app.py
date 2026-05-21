import streamlit as st
import pandas as pd
import plotly.express as px
import json
import base64

# --- AYARLAR VE LOGO ---
LOGO_URL = "https://images.seeklogo.com/logo-png/61/1/zore-logo-png_seeklogo-615897.png"

st.set_page_config(
    page_title="Zore Sipariş Kontrol", 
    layout="wide",
    page_icon=LOGO_URL
)

# Manifest oluşturma
manifest_data = {
    "short_name": "Zore",
    "name": "Zore Sipariş Kontrol",
    "icons": [{"src": LOGO_URL, "sizes": "512x512", "type": "image/png"}],
    "start_url": "/",
    "display": "standalone",
    "background_color": "#0d1117",
    "theme_color": "#0d1117"
}

manifest_str = json.dumps(manifest_data)
encoded_manifest = base64.b64encode(manifest_str.encode()).decode()

# HTML ve CSS Enjeksiyonu
st.markdown(f"""
    <head>
        <link rel="icon" href="{LOGO_URL}">
        <link rel="apple-touch-icon" href="{LOGO_URL}">
        <link rel="manifest" href="data:application/json;base64,{encoded_manifest}">
    </head>
    <style>
    .metric-card {{
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
    }}
    </style>
""", unsafe_allow_html=True)

# --- UYGULAMA MANTIĞI ---
st.title("📊 ZORE SİPARİŞ KONTROL MERKEZİ")
st.write("---")

SHEETS_URL = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"

@st.cache_data(ttl=60)
def load_data():
    df = pd.read_csv(SHEETS_URL)
    df.columns = df.columns.str.strip()
    return df

try:
    df = load_data()

    # Yan Panel
    st.sidebar.header("🔍 Filtreleme")
    firmalar = ["Hepsi"] + list(df['FIRMA'].unique()) if 'FIRMA' in df.columns else ["Hepsi"]
    secilen_firma = st.sidebar.selectbox("Firma:", firmalar)
    turler = ["Hepsi"] + list(df['TUR'].unique()) if 'TUR' in df.columns else ["Hepsi"]
    secilen_tur = st.sidebar.selectbox("Tür:", turler)

    filtered_df = df.copy()
    if secilen_firma != "Hepsi": filtered_df = filtered_df[filtered_df['FIRMA'] == secilen_firma]
    if secilen_tur != "Hepsi": filtered_df = filtered_df[filtered_df['TUR'] == secilen_tur]

    # Metrikler
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><h3>Toplam</h3><h2>{len(filtered_df)}</h2></div>', unsafe_allow_html=True)
    with col2:
        toplam_adet = int(filtered_df['ADET'].sum()) if 'ADET' in filtered_df.columns else 0
        st.markdown(f'<div class="metric-card"><h3>Adet</h3><h2>{toplam_adet:,}</h2></div>', unsafe_allow_html=True)
    with col3:
        hava = (filtered_df['TUR'].isin(['HAVA', 'UÇAK'])).sum()
        st.markdown(f'<div class="metric-card"><h3>Hava</h3><h2>{hava}</h2></div>', unsafe_allow_html=True)
    with col4:
        deniz = (filtered_df['TUR'].isin(['GEMİ', 'DENİZ'])).sum()
        st.markdown(f'<div class="metric-card"><h3>Deniz</h3><h2>{deniz}</h2></div>', unsafe_allow_html=True)

    st.write("---")

    # Grafikler
    l, r = st.columns(2)
    with l:
        st.subheader("Firma Yoğunluğu")
        fig1 = px.bar(filtered_df, x='FIRMA', y='ADET', color='TUR', template='plotly_dark')
        st.plotly_chart(fig1, use_container_width=True)
    with r:
        st.subheader("Ürünler")
        top = filtered_df.groupby('MALIN CINSI')['ADET'].sum().nlargest(10).reset_index()
        fig2 = px.bar(top, x='ADET', y='MALIN CINSI', orientation='h', template='plotly_dark')
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("📋 Liste")
    st.dataframe(filtered_df, use_container_width=True)

except Exception as e:
    st.error(f"Hata: {e}")