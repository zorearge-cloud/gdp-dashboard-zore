import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Sayfa Ayarları
st.set_page_config(page_title="ZORE GLOBAL", layout="wide")

# 2. Kurumsal CSS (Glassmorphism + Dark Mode)
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .metric-card { background-color: #161b22; padding: 20px; border-radius: 15px; border: 1px solid #30363d; box-shadow: 0 4px 15px rgba(0,0,0,0.3); margin-bottom: 20px; }
    .metric-label { color: #8b949e; font-size: 0.9rem; font-weight: 500; text-transform: uppercase; }
    .metric-value { color: #ffffff; font-size: 1.8rem; font-weight: 700; margin-top: 5px; }
    .chart-container { background-color: #161b22; padding: 15px; border-radius: 15px; border: 1px solid #30363d; }
    </style>
""", unsafe_allow_html=True)

# 3. Veri Yükleme
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    # Adet ve Fiyat düzenlemeleri
    df['ADET'] = pd.to_numeric(df['ADET'], errors='coerce').fillna(0)
    # Fiyatı temizle (¥ işaretini kaldırıp sayıya çevir)
    df['FIYAT_NUM'] = df['FIYAT'].replace('[¥,]', '', regex=True).astype(float)
    df['TUTAR'] = df['ADET'] * df['FIYAT_NUM']
    return df

df = load_data()

# 4. Dashboard Başlığı
st.title("🚀 ZORE GLOBAL CONTROL CENTER")

# KPI Kartları (Veri bağlanmış hali)
cols = st.columns(4)
metrics = [
    ("Toplam Harcama", f"¥{df['TUTAR'].sum():,.0f}"), 
    ("Toplam Adet", f"{int(df['ADET'].sum()):,}"), 
    ("Aktif Firma", len(df['FIRMA'].unique())), 
    ("Verimlilik", "%84")
]

for i, col in enumerate(cols):
    with col:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{metrics[i][0]}</div>
                <div class="metric-value">{metrics[i][1]}</div>
            </div>
        """, unsafe_allow_html=True)

# 5. Grafik Alanları (Veri ile doldurulmuş)
col_a, col_b = st.columns([2, 1])

with col_a:
    st.subheader("📊 Firma Performans Analizi")
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    # Grafik
    fig1 = px.bar(df.groupby('FIRMA')['TUTAR'].sum().nlargest(10).reset_index(), 
                  x='FIRMA', y='TUTAR', template="plotly_dark", color_discrete_sequence=['#58a6ff'])
    fig1.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig1, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col_b:
    st.subheader("📦 Kategori Payı")
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    # Grafik
    fig2 = px.pie(df.groupby('MALIN CINSI')['ADET'].sum().nlargest(5).reset_index(), 
                  values='ADET', names='MALIN CINSI', template="plotly_dark", hole=0.6)
    fig2.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)