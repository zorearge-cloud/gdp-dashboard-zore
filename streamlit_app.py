import streamlit as st
import pandas as pd
import plotly.express as px

# 1. SAYFA YAPILANDIRMASI
st.set_page_config(page_title="ZORE CORPORATE", layout="wide", initial_sidebar_state="collapsed")

# 2. KURUMSAL CSS (Dashboard'u şık gösteren gizli dokunuş)
st.markdown("""
    <style>
    /* Kart tasarımı */
    .metric-card {
        background-color: #1a1c24;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #30363d;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .metric-title { color: #8b949e; font-size: 14px; font-weight: 600; margin-bottom: 10px; }
    .metric-value { color: #ffffff; font-size: 28px; font-weight: 800; }
    
    /* Bölüm Başlıkları */
    h2 { color: #ffffff; font-size: 20px; margin-top: 20px; border-bottom: 2px solid #30363d; padding-bottom: 10px; }
    
    /* Sidebar gizleme vb. */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# 3. VERİ YÜKLEME (Optimize edilmiş)
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    df['ADET'] = pd.to_numeric(df['ADET'], errors='coerce').fillna(0)
    return df

df = load_data()

# 4. DASHBOARD GÖRÜNÜMÜ
st.title("🚀 ZORE GLOBAL DASHBOARD")

# KPI KARTLARI (Kendi özel kartlarımızı oluşturuyoruz)
cols = st.columns(4)
metrics = [
    ("Toplam Harcama", f"¥{df['ADET'].sum() * 1.48:,.0f}"), # Örnek hesap
    ("Toplam Adet", f"{int(df['ADET'].sum()):,}"),
    ("Aktif Firma", len(df['FIRMA'].unique())),
    ("Verimlilik", "%84.2")
]

for i, col in enumerate(cols):
    with col:
        title, val = metrics[i]
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">{title}</div>
                <div class="metric-value">{val}</div>
            </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ANA GRAFİK ALANI
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("📊 Firma Performans Dağılımı")
    fig = px.bar(df.groupby('FIRMA')['ADET'].sum().nlargest(10).reset_index(), 
                 x='FIRMA', y='ADET', template="plotly_dark", color_discrete_sequence=['#58a6ff'])
    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("📦 Kategori Payı")
    fig2 = px.pie(df.groupby('TUR')['ADET'].sum().reset_index(), 
                  values='ADET', names='TUR', template="plotly_dark", hole=0.6)
    fig2.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)