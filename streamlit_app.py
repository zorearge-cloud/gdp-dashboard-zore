import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Sayfa Ayarları
st.set_page_config(page_title="ZORE CORPORATE", layout="wide")

# 2. Kurumsal Stil (CSS)
st.markdown("""
    <style>
    .metric-card { background-color: #161b22; padding: 20px; border-radius: 10px; border: 1px solid #30363d; text-align: center; }
    .metric-title { color: #8b949e; font-size: 14px; font-weight: 600; }
    .metric-value { color: #ffffff; font-size: 24px; font-weight: 800; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

# 3. Veri Yükleme
@st.cache_data(ttl=600)
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    df['ADET'] = pd.to_numeric(df['ADET'], errors='coerce').fillna(0)
    df['FIYAT_NUM'] = df['FIYAT'].astype(str).str.replace('¥', '', regex=False).str.replace(',', '.', regex=False)
    df['FIYAT_NUM'] = pd.to_numeric(df['FIYAT_NUM'], errors='coerce').fillna(0)
    df['TUTAR'] = df['ADET'] * df['FIYAT_NUM']
    return df

df = load_data()

# 4. Sol Menü (Navigasyon)
st.sidebar.title("🔍 ZORE CONTROL")
page = st.sidebar.radio("Seçenekler", ["Dashboard", "Firma Detay Analizi", "Ham Veri"])

# --- DASHBOARD SAYFASI ---
if page == "Dashboard":
    st.title("📊 Yönetim Paneli")
    
    # KPI Kartları
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="metric-card"><div class="metric-title">Toplam Harcama</div><div class="metric-value">¥{df["TUTAR"].sum():,.0f}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><div class="metric-title">Toplam Adet</div><div class="metric-value">{int(df["ADET"].sum()):,}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><div class="metric-title">Aktif Firma</div><div class="metric-value">{len(df["FIRMA"].unique())}</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="metric-card"><div class="metric-title">Ürün Çeşidi</div><div class="metric-value">{len(df["MALIN CINSI"].unique())}</div></div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Büyük Grafikler
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("En Büyük 10 Harcama (Firma)")
        fig1 = px.bar(df.groupby('FIRMA')['TUTAR'].sum().nlargest(10).reset_index(), 
                      x='TUTAR', y='FIRMA', orientation='h', template="plotly_dark", color='TUTAR', color_continuous_scale='Blues')
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        st.subheader("Ürün Kategorisi Dağılımı")
        fig2 = px.pie(df.groupby('MALIN CINSI')['ADET'].sum().nlargest(10).reset_index(), 
                      values='ADET', names='MALIN CINSI', hole=0.5, template="plotly_dark")
        st.plotly_chart(fig2, use_container_width=True)

# --- FİRMA DETAY SAYFASI ---
elif page == "Firma Detay Analizi":
    st.title("🏢 Firma Bazlı Analiz")
    
    selected_firm = st.selectbox("Analiz edilecek firmayı seçin:", sorted(df['FIRMA'].unique()))
    firm_df = df[df['FIRMA'] == selected_firm]
    
    k1, k2 = st.columns(2)
    with k1: st.metric("Bu Firmaya Harcama", f"¥{firm_df['TUTAR'].sum():,.0f}")
    with k2: st.metric("Sipariş Adet", int(firm_df['ADET'].sum()))
    
    st.markdown("---")
    
    # Büyük Firma Grafiği
    st.subheader(f"{selected_firm} - Ürün Performansı")
    fig_firm = px.bar(firm_df.groupby('MALIN CINSI')['ADET'].sum().nlargest(10).reset_index(), 
                      x='ADET', y='MALIN CINSI', orientation='h', template="plotly_dark", color='ADET')
    st.plotly_chart(fig_firm, use_container_width=True)
    
    st.subheader("Detaylı Sipariş Tablosu")
    st.dataframe(firm_df[['MALIN CINSI', 'ADET', 'FIYAT', 'TUTAR']], use_container_width=True)

# --- HAM VERİ ---
else:
    st.title("🗄️ Ham Veri Kayıtları")
    st.dataframe(df, use_container_width=True)