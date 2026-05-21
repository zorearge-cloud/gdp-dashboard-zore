import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Sayfa Ayarları (Wide mode profesyonel görünüm için zorunludur)
st.set_page_config(page_title="ZORE PRO | Yönetim Paneli", layout="wide")

# 2. Kurumsal Stil Dosyası (Tasarımın kalbi burası)
st.markdown("""
    <style>
    /* Ana arkaplan */
    .stApp { background-color: #0e1117; }
    
    /* Kart tasarımı - Glassmorphism etkisi */
    .metric-card {
        background-color: #161b22;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #30363d;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        margin-bottom: 10px;
    }
    .metric-label { color: #8b949e; font-size: 0.9rem; font-weight: 500; text-transform: uppercase; }
    .metric-value { color: #ffffff; font-size: 1.8rem; font-weight: 700; margin-top: 5px; }
    
    /* Başlık stili */
    h2 { color: #e6edf3; font-size: 1.5rem; font-weight: 600; margin-bottom: 20px; }
    
    /* Grafik alanı kutusu */
    .chart-container {
        background-color: #161b22;
        padding: 15px;
        border-radius: 15px;
        border: 1px solid #30363d;
    }
    </style>
""", unsafe_allow_html=True)

# 3. Veri Yükleme (Örnek)
@st.cache_data
def load_data():
    # Buraya kendi verini yükle
    return pd.DataFrame() 

# 4. Arayüz
st.title("🚀 ZORE GLOBAL CONTROL CENTER")

# KPI Kartları (Dashboard'un profesyonel girişi)
cols = st.columns(4)
metrics = [("Toplam Harcama", "¥3,460,372"), ("Toplam Adet", "352,608"), ("Aktif Firma", "23"), ("Verimlilik", "%84")]

for i, col in enumerate(cols):
    with col:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{metrics[i][0]}</div>
                <div class="metric-value">{metrics[i][1]}</div>
            </div>
        """, unsafe_allow_html=True)

# İçerik Düzeni (İki sütunlu profesyonel yapı)
st.markdown("<br>", unsafe_allow_html=True)
col_a, col_b = st.columns([2, 1])

with col_a:
    st.subheader("📊 Firma Performans Analizi")
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    # Buraya Plotly grafiğini ekle
    st.write("Grafik Alanı")
    st.markdown('</div>', unsafe_allow_html=True)

with col_b:
    st.subheader("📦 Kategori Payı")
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    # Buraya Pasta grafiğini ekle
    st.write("Grafik Alanı")
    st.markdown('</div>', unsafe_allow_html=True)