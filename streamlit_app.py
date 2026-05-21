import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. Sayfa Ayarları (Uygulamanın profesyonel görünmesi için wide layout şart)
st.set_page_config(page_title="ZORE PRO PANEL", layout="wide", initial_sidebar_state="expanded")

# 2. Modern Tasarım İçin CSS (Kutucukları ve paneli güzelleştirir)
st.markdown("""
    <style>
    div.stButton > button { width: 100%; border-radius: 5px; height: 3em; background-color: #262730; color: white; }
    div.stMetric { background-color: #1e293b; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .css-1v0mbdj { padding-top: 1rem; } /* Sidebar boşluğu */
    </style>
""", unsafe_allow_html=True)

# 3. Veri Yükleme ve Hata Kontrolü
@st.cache_data(ttl=600)
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    # Sayısal alan temizliği
    df['ADET'] = pd.to_numeric(df['ADET'], errors='coerce').fillna(0)
    df['FIYAT_NUM'] = df['FIYAT'].astype(str).str.replace('¥', '', regex=False).str.replace(',', '.', regex=False)
    df['FIYAT_NUM'] = pd.to_numeric(df['FIYAT_NUM'], errors='coerce').fillna(0)
    df['TUTAR'] = df['ADET'] * df['FIYAT_NUM']
    return df

try:
    df = load_data()
except Exception as e:
    st.error("Veri yüklenemedi. Lütfen Google Sheet linkini ve sütun adlarını kontrol edin.")
    st.stop()

# 4. Sol Menü (Navigasyon)
st.sidebar.title("🔍 ZORE KONTROL")
page = st.sidebar.radio("Sayfalar", ["Dashboard", "Firma Detay Analizi", "Ham Veri"])

# --- DASHBOARD SAYFASI ---
if page == "Dashboard":
    st.title("📈 Genel Özet Paneli")
    
    # Üst Bilgi Kartları (Profesyonel Layout)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Harcama", f"¥{df['TUTAR'].sum():,.0f}")
    c2.metric("Toplam Adet", f"{int(df['ADET'].sum()):,}")
    c3.metric("Aktif Firma", len(df['FIRMA'].unique()))
    c4.metric("Ürün Çeşidi", len(df['MALIN CINSI'].unique()))
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("En Büyük 10 Harcama Kalemi")
        fig1 = px.bar(df.groupby('FIRMA')['TUTAR'].sum().nlargest(10).reset_index(), 
                      x='TUTAR', y='FIRMA', orientation='h', template="plotly_dark", color='TUTAR')
        st.plotly_chart(fig1, use_container_width=True)
        
    with col2:
        st.subheader("Ürün Kategorisi Dağılımı")
        fig2 = px.pie(df, values='TUTAR', names='MALIN CINSI', hole=0.4, template="plotly_dark")
        st.plotly_chart(fig2, use_container_width=True)

# --- FİRMA DETAY SAYFASI ---
elif page == "Firma Detay Analizi":
    st.title("🏢 Firma Detay Analizi")
    selected_firm = st.selectbox("Analiz edilecek firmayı seçin:", sorted(df['FIRMA'].unique()))
    
    firm_df = df[df['FIRMA'] == selected_firm]
    
    # Firma KPI
    k1, k2 = st.columns(2)
    k1.metric("Bu Firmaya Toplam Harcama", f"¥{firm_df['TUTAR'].sum():,.0f}")
    k2.metric("Sipariş Adet", int(firm_df['ADET'].sum()))
    
    st.markdown("---")
    
    # Firma Detay Tablosu
    st.subheader(f"{selected_firm} - Sipariş Detayları")
    st.dataframe(firm_df[['MALIN CINSI', 'ADET', 'FIYAT', 'TUTAR']], use_container_width=True)
    
    # Firma Grafik
    fig_firm = px.bar(firm_df, x='MALIN CINSI', y='TUTAR', template="plotly_dark", title="Ürün Bazlı Harcama Dağılımı")
    st.plotly_chart(fig_firm, use_container_width=True)

# --- HAM VERİ SAYFASI ---
else:
    st.title("🗄️ Tüm Kayıtlar")
    st.dataframe(df, use_container_width=True)