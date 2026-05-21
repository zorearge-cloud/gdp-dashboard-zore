import streamlit as st
import pandas as pd
import plotly.express as px
import json

# Zore Kurumsal Logo Linki
LOGO_URL = "https://images.seeklogo.com/logo-png/61/1/zore-logo-png_seeklogo-615897.png"

# 1. SAYFA YAPISI VE MOBİL UYGULAMA AYARLARI
st.set_page_config(
    page_title="Zore Sipariş Kontrol", 
    layout="wide",
    page_icon=LOGO_URL
)

# 2. TELEFONUN İKONU ALGILAMASI İÇİN SİHİRLİ MANIFEST AYARI
# Telefonların ana ekrana eklerken aradığı resmi uygulama kimlik dosyası (Manifest)
manifest_data = {
    "short_name": "Zore Kontrol",
    "name": "Zore Sipariş Kontrol Merkezi",
    "icons": [
        {
            "src": LOGO_URL,
            "sizes": "192x192",
            "type": "image/png",
            "purpose": "any maskable"
        },
        {
            "src": LOGO_URL,
            "sizes": "512x512",
            "type": "image/png",
            "purpose": "any maskable"
        }
    ],
    "start_url": ".",
    "background_color": "#0d1117",
    "theme_color": "#0d1117",
    "display": "standalone",
    "orientation": "portrait"
}

# Bu bilgiyi telefonun tarayıcısının okuyabileceği bir formata çeviriyoruz
manifest_string = json.dumps(manifest_data)

# HTML Kafasına (Head) telefonun ikonu ve manifesti zorla okuması için gereken kodları gömüyoruz
st.markdown(f"""
    <head>
        <title>Zore Kontrol</title>
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="apple-mobile-web-app-title" content="Zore Kontrol">
        <meta name="application-name" content="Zore Kontrol">
        <meta name="theme-color" content="#0d1117">
        <link rel="apple-touch-icon" href="{LOGO_URL}">
        <link rel="icon" type="image/png" href="{LOGO_URL}">
        <link rel="manifest" href="data:application/json;base64,{pd.io.json.base64.b64encode(manifest_string.encode()).decode()}">
    </head>
""", unsafe_allow_html=True)

# METRİK KARTLARINI ŞIKLAŞTIRAN CSS TASARIMI
st.markdown("""
    <style>
    .metric-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 10px;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# Buradan aşağısı senin mevcut kodunla aynı şekilde devam ediyor...
st.title("📊 ZORE SİPARİŞ KONTROL MERKEZİ")
st.write("---")