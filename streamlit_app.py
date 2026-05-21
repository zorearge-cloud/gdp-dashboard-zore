import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Sayfa Ayarları
st.set_page_config(page_title="ZORE GLOBAL", layout="wide")

# 2. Kurumsal CSS
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .metric-card { background-color: #161b22; padding: 20px; border-radius: 15px; border: 1px solid #30363d; margin-bottom: 20px; }
    .metric-label { color: #8b949e; font-size: 0.9rem; }
    .metric-value { color: #ffffff; font-size: 1.8rem; font-weight: 700; }
    .chart-container { background-color: #161b22; padding: 15px; border-radius: 15px; border: 1px solid #30363d; }
    </style>
""", unsafe_allow_html=True)

# 3. GÜÇLENDİRİLMİŞ Veri Yükleme
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
    df = pd.read_csv(url)
    
    # Sütun isimlerini temizle (boşlukları al)
    df.columns = df.columns.str.strip()
    
    # ADET temizleme
    df['ADET'] = pd.to_numeric(df['ADET'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
    
    # FIYAT temizleme (¥ işaretini kaldır, virgülü noktaya çevir)
    df['FIYAT_NUM'] = df['FIYAT'].astype(str).str.replace('¥', '').str.replace(',', '.').astype(float)
    
    # TUTAR hesaplama
    df['TUTAR'] = df['ADET'] * df['FIYAT_NUM']
    return df

try:
    df = load_data()
    
    # 4. Dashboard Arayüzü
    st.title("🚀 ZORE GLOBAL CONTROL CENTER")
    
    cols = st.columns(4)
    metrics = [
        ("Toplam Harcama", f"¥{df['TUTAR'].sum():,.0f}"), 
        ("Toplam Adet", f"{int(df['ADET'].sum()):,}"), 
        ("Aktif Firma", len(df['FIRMA'].unique())), 
        ("Verimlilik", "%84")
    ]
    
    for i, col in enumerate(cols):
        with col:
            st.markdown(f'<div class="metric-card"><div class="metric-label">{metrics[i][0]}</div><div class="metric-value">{metrics[i][1]}</div></div>', unsafe_allow_html=True)

    # 5. Grafikler
    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.subheader("📊 Firma Performans Analizi")
        fig1 = px.bar(df.groupby('FIRMA')['TUTAR'].sum().nlargest(10).reset_index(), 
                      x='FIRMA', y='TUTAR', template="plotly_dark", color_discrete_sequence=['#58a6ff'])
        st.plotly_chart(fig1, use_container_width=True)
        
    with col_b:
        st.subheader("📦 Kategori Payı")
        fig2 = px.pie(df.groupby('MALIN CINSI')['ADET'].sum().nlargest(5).reset_index(), 
                      values='ADET', names='MALIN CINSI', template="plotly_dark", hole=0.6)
        st.plotly_chart(fig2, use_container_width=True)

except Exception as e:
    st.error(f"Veri yüklenirken bir hata oluştu: {e}")
    st.write("Lütfen Google Sheets dosyasındaki sütun isimlerinin tam olarak şu olduğundan emin ol: 'FIRMA', 'MALIN CINSI', 'ADET', 'FIYAT'")