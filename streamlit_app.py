import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import numpy as np
from typing import List, Dict, Union

# ==============================================================================
# 1. CONFIGURATION & ENTERPRISE THEME
# ==============================================================================
st.set_page_config(
    page_title="ZORE ENTERPRISE BI", 
    page_icon="📊", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Enterprise CSS injection (Theming)
st.markdown("""
    <style>
    :root { --primary-color: #3b82f6; --bg-color: #0f172a; --card-bg: #1e293b; }
    .stApp { background-color: var(--bg-color); color: #f8fafc; }
    div[data-testid="stMetric"] { background-color: var(--card-bg); padding: 20px; border-radius: 12px; border: 1px solid #334155; }
    .css-1r6slp0 { background-color: #0f172a; }
    .chart-container { background-color: var(--card-bg); padding: 20px; border-radius: 15px; border: 1px solid #334155; margin-bottom: 20px; }
    h1, h2, h3 { color: #ffffff !important; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. DATA ENGINEERING ENGINE
# ==============================================================================
class DataProcessor:
    """Veri işleme, temizleme ve özellik mühendisliği katmanı."""
    
    def __init__(self, url: str):
        self.url = url
        self.raw_df = None
        self.clean_df = None

    def load_data(self):
        try:
            self.raw_df = pd.read_csv(self.url)
            self.raw_df.columns = self.raw_df.columns.str.strip()
            self._preprocess()
            return True
        except Exception as e:
            st.error(f"Veri yükleme başarısız: {e}")
            return False

    def _preprocess(self):
        df = self.raw_df.copy()
        
        # Sayısal Temizleme
        df['ADET'] = pd.to_numeric(df['ADET'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
        
        # Para Birimi Temizleme (Regex Logic)
        def clean_currency(val):
            val = str(val).replace('¥', '').replace('$', '').replace(',', '.')
            val = re.sub(r'[^\d.]', '', val)
            try: return float(val)
            except: return 0.0
        
        df['FIYAT_NUM'] = df['FIYAT'].apply(clean_currency)
        df['TUTAR'] = df['ADET'] * df['FIYAT_NUM']
        
        # Akıllı Kategorizasyon
        def classify(name):
            n = str(name).lower()
            if any(x in n for x in ['kapak', 'kılıf', 'case']): return "Kapak & Kılıf"
            if any(x in n for x in ['glass', 'koruyucu', 'ekran']): return "Ekran Koruyucu"
            if any(x in n for x in ['şarj', 'adaptör', 'kablo']): return "Şarj & Kablo"
            if any(x in n for x in ['watch', 'kordon']): return "Saat Grubu"
            return "Diğer"
            
        df['KATEGORI'] = df['MALIN CINSI'].apply(classify)
        self.clean_df = df

    def get_df(self):
        return self.clean_df

# ==============================================================================
# 3. VISUALIZATION FACTORY
# ==============================================================================
class VizFactory:
    """Grafik oluşturma fonksiyonları (Modüler yapı)."""
    
    @staticmethod
    def create_kpi_row(df: pd.DataFrame):
        cols = st.columns(4)
        metrics = [
            ("Toplam Ciro", f"¥{df['TUTAR'].sum():,.0f}"),
            ("Toplam Adet", f"{int(df['ADET'].sum()):,}"),
            ("Aktif Firma", df['FIRMA'].nunique()),
            ("Kategori", df['KATEGORI'].nunique())
        ]
        for i, col in enumerate(cols):
            col.metric(metrics[i][0], metrics[i][1])

    @staticmethod
    def render_bar_chart(df: pd.DataFrame, group_col: str, val_col: str, title: str):
        data = df.groupby(group_col)[val_col].sum().nlargest(10).reset_index()
        fig = px.bar(data, x=val_col, y=group_col, orientation='h', template="plotly_dark", color=val_col, color_continuous_scale='Blues')
        fig.update_layout(yaxis={'categoryorder':'total ascending'}, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        return fig

# ==============================================================================
# 4. PAGE HANDLERS (BUSINESS LOGIC)
# ==============================================================================
def render_dashboard(df: pd.DataFrame):
    st.title("📈 Executive Dashboard")
    VizFactory.create_kpi_row(df)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
        st.subheader("En Yüksek Hacimli Firmalar")
        st.plotly_chart(VizFactory.render_bar_chart(df, 'FIRMA', 'TUTAR', ""), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with c2:
        st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
        st.subheader("Kategori Dağılımı")
        fig = px.pie(df, values='TUTAR', names='KATEGORI', hole=0.6, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

def render_firm_analysis(df: pd.DataFrame):
    st.title("🏢 Firma Detay Analizi")
    firm = st.selectbox("Analiz İçin Firma Seçin:", sorted(df['FIRMA'].unique()))
    
    subset = df[df['FIRMA'] == firm]
    
    # 3'lü Detay
    k1, k2, k3 = st.columns(3)
    k1.metric("Firma Toplam Ciro", f"¥{subset['TUTAR'].sum():,.0f}")
    k2.metric("Toplam Ürün Adedi", int(subset['ADET'].sum()))
    k3.metric("Favori Kategori", subset.groupby('KATEGORI')['TUTAR'].sum().idxmax())
    
    # Detay Tablosu ve Grafik
    st.subheader(f"{firm} - Ürün Detay Dağılımı")
    st.dataframe(subset[['MALIN CINSI', 'KATEGORI', 'ADET', 'FIYAT', 'TUTAR']], use_container_width=True)
    
    # Derinlemesine Grafik
    fig = px.sunburst(subset, path=['KATEGORI', 'MALIN CINSI'], values='TUTAR', template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

def render_product_analysis(df: pd.DataFrame):
    st.title("🔍 Ürün Performans Matrisi")
    
    # Scatter plot: Price vs Volume
    fig = px.scatter(df, x='FIYAT_NUM', y='ADET', color='KATEGORI', size='TUTAR', 
                     hover_data=['MALIN CINSI'], template="plotly_dark", size_max=60)
    st.plotly_chart(fig, use_container_width=True)
    
    # Kategori bazlı karşılaştırma
    st.subheader("Kategori Bazlı Finansal Karşılaştırma")
    st.bar_chart(df.groupby('KATEGORI')[['TUTAR', 'ADET']].sum())

# ==============================================================================
# 5. MAIN EXECUTION LOOP
# ==============================================================================
def main():
    # Data Load
    url = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
    processor = DataProcessor(url)
    
    if not processor.load_data():
        return
    
    df = processor.get_df()
    
    # Navigation
    st.sidebar.title("ZORE CONTROL PANEL")
    page = st.sidebar.radio("Navigasyon", ["Dashboard", "Firma Derin Analizi", "Ürün Performansı", "Ham Veri"])
    
    if page == "Dashboard":
        render_dashboard(df)
    elif page == "Firma Derin Analizi":
        render_firm_analysis(df)
    elif page == "Ürün Performansı":
        render_product_analysis(df)
    else:
        st.title("🗄️ Veri Envanteri")
        st.dataframe(df, use_container_width=True)
        
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.info("Gelişmiş Analitik Modülü V.2.1")

if __name__ == "__main__":
    main()