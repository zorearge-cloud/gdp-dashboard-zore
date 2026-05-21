import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# --- 1. AYARLAR VE TASARIM ---
st.set_page_config(page_title="ZORE ENTERPRISE PANEL", layout="wide", initial_sidebar_state="expanded")

# Kurumsal CSS (Glassmorphism ve Modern UI)
st.markdown("""
    <style>
    .main { background: #0f172a; color: white; }
    .stMetric { background-color: #1e293b; padding: 20px; border-radius: 15px; border: 1px solid #334155; }
    .css-1r6slp0 { background-color: #1e293b; }
    h1, h2, h3 { color: #f8fafc; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)

# --- 2. VERİ MOTORU (GELİŞMİŞ) ---
@st.cache_data(ttl=600)
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    
    # Sayısal alanları temizle
    df['ADET'] = pd.to_numeric(df['ADET'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
    
    def clean_currency(val):
        s = str(val).replace('¥', '').replace('$', '').replace(',', '.')
        s = re.sub(r'[^\d.]', '', s)
        try: return float(s)
        except: return 0.0
    
    df['FIYAT_NUM'] = df['FIYAT'].apply(clean_currency)
    df['TUTAR'] = df['ADET'] * df['FIYAT_NUM']
    
    # Akıllı Kategorizasyon (Ürün ismine göre otomatik sınıflandırma)
    def categorize_product(name):
        name = str(name).lower()
        if "kapak" in name or "case" in name: return "Kapak Grubu"
        if "glass" in name or "koruyucu" in name: return "Ekran Koruyucu"
        if "şarj" in name or "adaptör" in name or "kablo" in name: return "Şarj/Kablo"
        if "kordon" in name or "watch" in name: return "Saat Kordonu"
        if "power" in name or "bank" in name: return "Powerbank"
        return "Diğer"
    
    df['KATEGORI'] = df['MALIN CINSI'].apply(categorize_product)
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Veri yüklenemedi: {e}")
    st.stop()

# --- 3. NAVİGASYON ---
st.sidebar.title("🚀 ZORE KONTROL MERKEZİ")
menu = st.sidebar.radio("Sayfalar", ["Dashboard", "Firma Detay Analizi", "Ham Veri"])

# --- 4. SAYFA 1: DASHBOARD ---
if menu == "Dashboard":
    st.title("📊 Yönetici Özet Paneli")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Harcama", f"¥{df['TUTAR'].sum():,.0f}")
    c2.metric("Toplam Adet", f"{int(df['ADET'].sum()):,}")
    c3.metric("Aktif Firma", df['FIRMA'].nunique())
    c4.metric("Kategori Sayısı", df['KATEGORI'].nunique())
    
    st.markdown("---")
    
    # Grid 1: Firma ve Kategori Dağılımları
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("Firma Bazlı Harcama (İlk 10)")
        fig1 = px.bar(df.groupby('FIRMA')['TUTAR'].sum().nlargest(10).reset_index(), 
                      x='TUTAR', y='FIRMA', orientation='h', template="plotly_dark", color='TUTAR')
        st.plotly_chart(fig1, use_container_width=True)
        
    with col_b:
        st.subheader("Kategori Bazlı Harcama Dağılımı")
        fig2 = px.pie(df.groupby('KATEGORI')['TUTAR'].sum().reset_index(), 
                      values='TUTAR', names='KATEGORI', hole=0.5, template="plotly_dark")
        st.plotly_chart(fig2, use_container_width=True)

    # Grid 2: Detaylı Analiz
    col_c, col_d = st.columns(2)
    
    with col_c:
        st.subheader("En Çok Adet Sipariş Edilen Ürünler (İlk 10)")
        fig3 = px.bar(df.groupby('MALIN CINSI')['ADET'].sum().nlargest(10).reset_index(), 
                      x='ADET', y='MALIN CINSI', orientation='h', template="plotly_dark", color='ADET')
        st.plotly_chart(fig3, use_container_width=True)
        
    with col_d:
        st.subheader("Aylık/Hacimsel Trend")
        # Örnek olarak kategorilere göre adet
        fig4 = px.scatter(df.groupby('KATEGORI')['TUTAR'].sum().reset_index(), 
                          x='KATEGORI', y='TUTAR', size='TUTAR', color='KATEGORI', template="plotly_dark")
        st.plotly_chart(fig4, use_container_width=True)

# --- 5. SAYFA 2: FİRMA DETAY ANALİZİ ---
elif menu == "Firma Detay Analizi":
    st.title("🏢 Firma Detay Analizi")
    
    firm_list = sorted(df['FIRMA'].unique())
    selected_firm = st.selectbox("Analiz edilecek firmayı seçin:", firm_list)
    
    firm_df = df[df['FIRMA'] == selected_firm]
    
    # Detay Metrikleri
    f1, f2, f3 = st.columns(3)
    f1.metric("Toplam Harcama", f"¥{firm_df['TUTAR'].sum():,.0f}")
    f2.metric("Toplam Adet", int(firm_df['ADET'].sum()))
    f3.metric("Favori Kategori", firm_df.groupby('KATEGORI')['ADET'].sum().idxmax())
    
    st.markdown("---")
    
    # Firma İçi Grafik
    fig_f = px.pie(firm_df.groupby('KATEGORI')['TUTAR'].sum().reset_index(), 
                   values='TUTAR', names='KATEGORI', title=f"{selected_firm} - Kategori Payı",
                   template="plotly_dark", hole=0.4)
    st.plotly_chart(fig_f, use_container_width=True)
    
    st.subheader("Sipariş Kalemleri Detayı")
    st.dataframe(firm_df[['SIPARIS_TARIHI', 'MALIN CINSI', 'KATEGORI', 'ADET', 'FIYAT', 'TUTAR']], use_container_width=True)

# --- 6. SAYFA 3: HAM VERİ ---
else:
    st.title("🗄️ Ham Veri Envanteri")
    st.dataframe(df, use_container_width=True)
    
    st.download_button(
        label="Veriyi CSV Olarak İndir",
        data=df.to_csv(index=False),
        file_name='zore_data.csv',
        mime='text/csv',
    )