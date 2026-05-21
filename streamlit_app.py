import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import numpy as np

# --- 1. CONFIG & CSS ---
st.set_page_config(page_title="ZORE GLOBAL BI PRO", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main { background-color: #0b1021; }
    .stApp { background-color: #0b1021; }
    .css-1r6slp0 { background-color: #1a2234; }
    .stMetric { background-color: #1a2234; padding: 20px; border-radius: 10px; border: 1px solid #334155; }
    h1, h2, h3 { color: #f1f5f9; }
    .stDataFrame { border: 1px solid #334155; }
    </style>
""", unsafe_allow_html=True)

# --- 2. VERİ MOTORU (GELİŞMİŞ) ---
@st.cache_data(ttl=3600)
def get_clean_data():
    url = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        
        # Temizlik: Adet ve Fiyat
        df['ADET'] = pd.to_numeric(df['ADET'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
        
        def parse_currency(val):
            # '¥1,48' veya '$6.41' gibi değerleri temizle
            val = str(val).replace('¥', '').replace('$', '').replace(',', '.')
            val = re.sub(r'[^\d.]', '', val)
            try: return float(val)
            except: return 0.0
            
        df['FIYAT_NUM'] = df['FIYAT'].apply(parse_currency)
        df['TUTAR'] = df['ADET'] * df['FIYAT_NUM']
        
        # Akıllı Kategorizasyon
        def categorize(name):
            name = str(name).lower()
            if any(x in name for x in ['kapak', 'case', 'kılıf']): return "Kapak & Kılıf"
            if any(x in name for x in ['glass', 'koruyucu', 'ekran']): return "Ekran Koruyucu"
            if any(x in name for x in ['şarj', 'adaptör', 'kablo', 'power']): return "Güç & Aksesuar"
            if any(x in name for x in ['watch', 'kordon']): return "Saat Grubu"
            if any(x in name for x in ['kulak', 'ses', 'speaker']): return "Ses Sistemleri"
            return "Diğer"
            
        df['KATEGORI'] = df['MALIN CINSI'].apply(categorize)
        return df
    except Exception as e:
        st.error(f"Veri yükleme hatası: {e}")
        return pd.DataFrame()

# --- 3. DASHBOARD BİLEŞENLERİ ---
def render_kpi(df):
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Toplam Harcama", f"¥{df['TUTAR'].sum():,.0f}")
    with c2: st.metric("Toplam Adet", f"{int(df['ADET'].sum()):,}")
    with c3: st.metric("Aktif Firma", df['FIRMA'].nunique())
    with c4: st.metric("Kategori Çeşitliliği", df['KATEGORI'].nunique())

def render_main_charts(df):
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Firma Bazlı Harcama Analizi")
        fig1 = px.bar(df.groupby('FIRMA')['TUTAR'].sum().nlargest(10).reset_index(), 
                      x='TUTAR', y='FIRMA', orientation='h', color='TUTAR', template="plotly_dark")
        st.plotly_chart(fig1, use_container_width=True)
        
    with col2:
        st.subheader("Kategori Dağılımı (Sunburst)")
        fig2 = px.sunburst(df, path=['KATEGORI', 'MALIN CINSI'], values='TUTAR', template="plotly_dark")
        st.plotly_chart(fig2, use_container_width=True)

# --- 4. SAYFA YAPISI ---
df = get_clean_data()
if not df.empty:
    st.title("🚀 ZORE GLOBAL BI DASHBOARD")
    tabs = st.tabs(["Dashboard", "Firma Derin Analizi", "Ürün Performans", "Ham Veri"])
    
    with tabs[0]:
        render_kpi(df)
        render_main_charts(df)
        
    with tabs[1]:
        st.header("Firma Derin Analizi")
        selected_firm = st.selectbox("Firma Seçin:", sorted(df['FIRMA'].unique()))
        firm_df = df[df['FIRMA'] == selected_firm]
        
        # Firma içi detay
        f1, f2 = st.columns([1, 2])
        with f1:
            st.metric("Bu Firmaya Harcanan", f"¥{firm_df['TUTAR'].sum():,.0f}")
            st.metric("Ürün Çeşitliliği", firm_df['MALIN CINSI'].nunique())
        
        with f2:
            fig3 = px.pie(firm_df, values='TUTAR', names='KATEGORI', hole=0.4, title="Kategori Payı")
            st.plotly_chart(fig3, use_container_width=True)
            
        st.subheader("Bu Firmadan En Çok Ne Alındı?")
        fig4 = px.bar(firm_df.groupby('MALIN CINSI')['TUTAR'].sum().nlargest(10).reset_index(), 
                      x='TUTAR', y='MALIN CINSI', orientation='h', template="plotly_dark")
        st.plotly_chart(fig4, use_container_width=True)
        
    with tabs[2]:
        st.header("Ürün Performans Matrisi")
        # Ürünlerin fiyat ve adet korelasyonu
        fig5 = px.scatter(df, x='FIYAT_NUM', y='ADET', color='KATEGORI', size='TUTAR', 
                          hover_data=['MALIN CINSI'], template="plotly_dark", title="Fiyat vs Adet İlişkisi")
        st.plotly_chart(fig5, use_container_width=True)
        
    with tabs[3]:
        st.dataframe(df, use_container_width=True)
else:
    st.warning("Veri bulunamadı veya işlenemedi.")

# --- 5. FOOTER ---
st.markdown("---")
st.caption("ZORE GLOBAL © 2026 - Gelişmiş Analiz Paneli")