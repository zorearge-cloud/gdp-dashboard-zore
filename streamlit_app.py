import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Sayfa Ayarları - En geniş format
st.set_page_config(page_title="ZORE PRO", layout="wide")

# 2. Modern Tasarım (CSS) - İşte o "profesyonel" görünümün sırrı burada
st.markdown("""
    <style>
    /* Arka plan */
    .stApp { background: #07080a; color: #e0e0e0; }
    
    /* Modern Kart Tasarımı (Glassmorphism) */
    .card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 25px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    
    .card-title { font-size: 14px; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
    .card-value { font-size: 32px; font-weight: 700; color: #fff; }
    
    /* Sidebar gizle/özelleştir */
    section[data-testid="stSidebar"] { background-color: #0d1117; }
    </style>
""", unsafe_allow_html=True)

# 3. Veri Temizliği
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    df['ADET'] = pd.to_numeric(df['ADET'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
    df['FIYAT_NUM'] = df['FIYAT'].astype(str).str.replace('¥', '').str.replace(',', '.').astype(float)
    df['TUTAR'] = df['ADET'] * df['FIYAT_NUM']
    return df

try:
    df = load_data()
    
    # 4. Arayüz
    st.title("🚀 ZORE CONTROL CENTER")
    
    # KPI Kartları
    cols = st.columns(4)
    metrics = [("Toplam Harcama", f"¥{df['TUTAR'].sum():,.0f}"), ("Toplam Adet", f"{int(df['ADET'].sum()):,}"), 
               ("Aktif Firma", len(df['FIRMA'].unique())), ("Verimlilik", "84.2%")]
    
    for i, col in enumerate(cols):
        with col:
            st.markdown(f"""
                <div class="card">
                    <div class="card-title">{metrics[i][0]}</div>
                    <div class="card-value">{metrics[i][1]}</div>
                </div>
            """, unsafe_allow_html=True)
            
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Grafik Alanları
    col_a, col_b = st.columns([2, 1])
    
    with col_a:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📊 Firma Performans Dağılımı")
        fig1 = px.bar(df.groupby('FIRMA')['TUTAR'].sum().nlargest(10).reset_index(), 
                      x='FIRMA', y='TUTAR', template="plotly_dark", color_discrete_sequence=['#4a9eff'])
        fig1.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig1, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_b:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📦 Kategori Payı")
        fig2 = px.pie(df.groupby('MALIN CINSI')['ADET'].sum().nlargest(5).reset_index(), 
                      values='ADET', names='MALIN CINSI', template="plotly_dark", hole=0.7)
        fig2.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

except Exception as e:
    st.error("Veri işleme hatası. Lütfen tablo yapısını kontrol edin.")