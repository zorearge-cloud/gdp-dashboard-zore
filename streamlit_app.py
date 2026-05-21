import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# 1. ULUSLARARASI KURUMSAL YAPI AYARLARI
st.set_page_config(page_title="ZORE STRATEGIC COMMAND", layout="wide", initial_sidebar_state="expanded")

# 2. ÖZEL CSS - (Animasyonlar, Cam Efekti ve Neon Glow)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    /* Arka Plan */
    .stApp {
        background: radial-gradient(circle at top right, #0a0b10, #161b22);
    }

    /* Glassmorphism Kartlar */
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 25px;
        transition: all 0.3s ease;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        animation: fadeIn 1.5s ease;
    }
    
    .metric-card:hover {
        border: 1px solid #58a6ff;
        transform: translateY(-5px);
        background: rgba(88, 166, 255, 0.05);
    }

    /* Sayı Animasyonu Efekti */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .glow-text {
        color: #ffffff;
        text-shadow: 0 0 10px rgba(88, 166, 255, 0.5);
        font-weight: 800;
        font-size: 2rem;
    }
    
    .label-text {
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-size: 0.8rem;
    }

    /* Sidebar Tasarımı */
    section[data-testid="stSidebar"] {
        background-color: #0d1117;
        border-right: 1px solid rgba(255,255,255,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# 3. ROBUST VERİ TEMİZLEME MOTORU
@st.cache_data(ttl=600)
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    
    # Adet Temizliği
    df['ADET'] = pd.to_numeric(df['ADET'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
    
    # Fiyat Temizliği (Dolar, Yen, Virgül fark etmez)
    def clean_currency(val):
        s = str(val).replace('¥', '').replace('$', '').replace(',', '.')
        s = re.sub(r'[^\d.]', '', s)
        try: return float(s)
        except: return 0.0

    df['FIYAT_NUM'] = df['FIYAT'].apply(clean_currency)
    df['TUTAR'] = df['ADET'] * df['FIYAT_NUM']
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Veri Bağlantı Hatası: {e}")
    st.stop()

# 4. SOL MENÜ (NAVİGASYON)
st.sidebar.markdown("<h1 style='text-align: center; color: #58a6ff;'>🚀 ZORE OPS</h1>", unsafe_allow_html=True)
page = st.sidebar.radio("KOMUTA MERKEZİ", ["DASHBOARD", "FİRMA ANALİZİ", "HAM VERİ"], label_visibility="collapsed")

# --- DASHBOARD (MACRO VIEW) ---
if page == "DASHBOARD":
    st.markdown("<h2 style='color: white; font-weight: 800;'>📊 GLOBAL STRATEJİK ÖZET</h2>", unsafe_allow_html=True)
    
    # KPI SECTION
    c1, c2, c3, c4 = st.columns(4)
    
    def metric_box(label, val, col):
        col.markdown(f"""
            <div class="metric-card">
                <div class="label-text">{label}</div>
                <div class="glow-text">{val}</div>
            </div>
        """, unsafe_allow_html=True)

    metric_box("Toplam Ciro", f"¥{df['TUTAR'].sum():,.0f}", c1)
    metric_box("Lojistik Hacim", f"{int(df['ADET'].sum()):,}", c2)
    metric_box("Partner Sayısı", f"{df['FIRMA'].nunique()}", c3)
    metric_box("Ürün SKU", f"{df['MALIN CINSI'].nunique()}", c4)

    st.markdown("<br>", unsafe_allow_html=True)

    # GRAPHS
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("<h4 style='color: white;'>📈 Finansal Dalgalanma Trendi</h4>", unsafe_allow_html=True)
        # Dalgalı alan grafiği (Spline Area)
        fig_trend = px.area(df.groupby('FIRMA')['TUTAR'].sum().nlargest(15).reset_index(), 
                            x='FIRMA', y='TUTAR', 
                            template="plotly_dark",
                            color_discrete_sequence=['#58a6ff'])
        fig_trend.update_traces(line_shape='spline', line_width=4, fillcolor='rgba(88, 166, 255, 0.2)')
        fig_trend.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis_title="")
        st.plotly_chart(fig_trend, use_container_width=True)

    with col_right:
        st.markdown("<h4 style='color: white;'>🎯 Kategori Payı</h4>", unsafe_allow_html=True)
        fig_pie = px.pie(df.groupby('MALIN CINSI')['TUTAR'].sum().nlargest(8).reset_index(), 
                         values='TUTAR', names='MALIN CINSI', 
                         hole=0.6, template="plotly_dark")
        fig_pie.update_traces(textinfo='none', marker=dict(colors=px.colors.sequential.Blues_r))
        fig_pie.update_layout(showlegend=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_pie, use_container_width=True)

# --- FİRMA ANALİZİ (MICRO VIEW) ---
elif page == "FİRMA ANALİZİ":
    st.markdown("<h2 style='color: white;'>🏢 PARTNER ANALİZ PROFİLİ</h2>", unsafe_allow_html=True)
    
    selected_firm = st.selectbox("Analiz edilecek firmayı seçin:", sorted(df['FIRMA'].unique()))
    firm_df = df[df['FIRMA'] == selected_firm]
    total_spend = df['TUTAR'].sum()
    firm_spend = firm_df['TUTAR'].sum()
    share = (firm_spend / total_spend) * 100

    c1, c2 = st.columns([1, 2])
    
    with c1:
        # Kurumsal Gösterge (Gauge Chart)
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = share,
            title = {'text': "Genel Ciro Payı %", 'font': {'size': 16, 'color': "white"}},
            number = {'font': {'color': '#58a6ff'}},
            gauge = {
                'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "white"},
                'bar': {'color': "#58a6ff"},
                'bgcolor': "rgba(255,255,255,0.05)",
                'borderwidth': 2,
                'bordercolor': "white",
                'steps': [
                    {'range': [0, 50], 'color': 'rgba(255,255,255,0.05)'},
                    {'range': [50, 100], 'color': 'rgba(255,255,255,0.1)'}],
            }
        ))
        fig_gauge.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(t=50, b=0, l=20, r=20))
        st.plotly_chart(fig_gauge, use_container_width=True)

    with c2:
        st.markdown(f"<h4 style='color: white;'>📦 {selected_firm} Ürün Dağılımı</h4>", unsafe_allow_html=True)
        # Hareketli Bar Grafiği
        top_firm_products = firm_df.groupby('MALIN CINSI')['ADET'].sum().nlargest(10).reset_index()
        fig_bar = px.bar(top_firm_products, x='ADET', y='MALIN CINSI', orientation='h',
                         template="plotly_dark", color='ADET',
                         color_continuous_scale='Blues')
        fig_bar.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.subheader("📋 Partner Sipariş Hareketleri")
    st.dataframe(firm_df[['MALIN CINSI', 'ADET', 'FIYAT', 'TUTAR']].sort_values(by='TUTAR', ascending=False), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# --- HAM VERİ (DATA VIEW) ---
else:
    st.markdown("<h2 style='color: white;'>🗄️ STRATEJİK VERİ ENVANTERİ</h2>", unsafe_allow_html=True)
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)