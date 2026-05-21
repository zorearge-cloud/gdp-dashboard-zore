import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Sayfa ve Stil Ayarları
st.set_page_config(page_title="ZORE SİPARİŞ", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .metric-card { background-color: #161b22; padding: 20px; border-radius: 10px; border: 1px solid #30363d; text-align: center; }
    .metric-title { color: #8b949e; font-size: 0.8rem; text-transform: uppercase; }
    .metric-val { color: #ffffff; font-size: 1.5rem; font-weight: bold; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

# 2. Veri Yükleme ve Temizleme
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
    df = pd.read_csv(url)
    
    # Sütun isimlerini temizle (boşlukları yok et)
    df.columns = df.columns.str.strip()
    
    # ADET temizleme
    df['ADET'] = pd.to_numeric(df['ADET'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
    
    # FIYAT temizleme
    df['FIYAT_NUM'] = df['FIYAT'].astype(str).str.replace('¥', '').str.replace(',', '.').astype(float)
    
    # Hesaplama
    df['TUTAR'] = df['ADET'] * df['FIYAT_NUM']
    return df

try:
    df = load_data()
    
    # Başlık
    st.title("📊 ZORE YÖNETİM PANELİ")
    
    # KPI Kartları
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(f'<div class="metric-card"><div class="metric-title">Toplam Harcama</div><div class="metric-val">¥{df["TUTAR"].sum():,.0f}</div></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="metric-card"><div class="metric-title">Toplam Adet</div><div class="metric-val">{int(df["ADET"].sum()):,}</div></div>', unsafe_allow_html=True)
    with col3: st.markdown(f'<div class="metric-card"><div class="metric-title">Aktif Firma</div><div class="metric-val">{df["FIRMA"].nunique()}</div></div>', unsafe_allow_html=True)
    with col4: st.markdown(f'<div class="metric-card"><div class="metric-title">Ürün Çeşidi</div><div class="metric-val">{df["MALIN CINSI"].nunique()}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Grafikler
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("En Büyük 10 Harcama (Firma)")
        fig1 = px.bar(df.groupby('FIRMA')['TUTAR'].sum().nlargest(10).reset_index(), 
                      x='TUTAR', y='FIRMA', orientation='h', template="plotly_dark", color_discrete_sequence=['#58a6ff'])
        fig1.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig1, use_container_width=True)
        
    with c2:
        st.subheader("Ürün Kategorisi Dağılımı")
        fig2 = px.pie(df.groupby('MALIN CINSI')['ADET'].sum().nlargest(10).reset_index(), 
                      values='ADET', names='MALIN CINSI', template="plotly_dark", hole=0.6)
        st.plotly_chart(fig2, use_container_width=True)

except Exception as e:
    st.error(f"Veri yüklenirken hata oluştu: {e}")
    st.write("Sütunların tam isimleri: FIRMA, MALIN CINSI, ADET, FIYAT olmalıdır.")