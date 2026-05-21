import streamlit as st
import pandas as pd
import plotly.express as px

# Zore'nin Aktif Çalışan Gerçek Kurumsal Logosu
LOGO_URL = "https://seeklogo.com/vector-logo/615897/zore"

# 1. Sayfa Yapısı ve Mobil Uygulama Ayarları
st.set_page_config(
    page_title="Zore Sipariş Kontrol", 
    layout="wide",
    page_icon=LOGO_URL  # Tarayıcı sekmesindeki ikon
)

# Telefonun ana ekrana eklerken logoyu ve ismi hafızaya alması için gereken net ayarlar
st.markdown(f"""
    <head>
        <title>Zore Kontrol</title>
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="apple-mobile-web-app-title" content="Zore Kontrol">
        <meta name="application-name" content="Zore Kontrol">
        <link rel="apple-touch-icon" href="{LOGO_URL}">
        <link rel="icon" type="image/png" href="{LOGO_URL}">
    </head>
""", unsafe_allow_html=True)

st.title("📊 ZORE SİPARİŞ KONTROL MERKEZİ")
st.write("---")

# 2. GOOGLE SHEETS ENTEGRASYONU
SHEETS_URL = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"

@st.cache_data(ttl=10) # Test aşamasında veriyi 10 saniyede bir hızlıca çeksin
def load_data():
    df = pd.read_csv(SHEETS_URL)
    df.columns = df.columns.str.strip()
    return df

try:
    df = load_data()

    # 3. YAN PANEL FİLTRELERİ (Özelleştirme Gücü)
    st.sidebar.header("🔍 Filtreleme Paneli")
    
    # Firma Filtresi
    firmalar = ["Hepsi"] + list(df['FIRMA'].unique()) if 'FIRMA' in df.columns else ["Hepsi"]
    secilen_firma = st.sidebar.selectbox("Firma Seçin:", firmalar)
    
    # Tür Filtresi
    turler = ["Hepsi"] + list(df['TUR'].unique()) if 'TUR' in df.columns else ["Hepsi"]
    secilen_tur = st.sidebar.selectbox("Taşıma Türü Seçin:", turler)

    # Veriyi Filtreleme Mantığı
    filtered_df = df.copy()
    if secilen_firma != "Hepsi":
        filtered_df = filtered_df[filtered_df['FIRMA'] == secilen_firma]
    if secilen_tur != "Hepsi":
        filtered_df = filtered_df[filtered_df['TUR'] == secilen_tur]

    # 4. ÜST TARAF / BÜYÜK NEON RENKLİ METRİK KARTLARI
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><h3 style="color:#58a6ff;margin:0;font-size:16px;">Toplam Sipariş</h3><h2 style="margin:10px 0 0 0;font-size:28px;color:#f0f6fc;">{len(filtered_df)} Satır</h2></div>', unsafe_allow_html=True)
    with col2:
        toplam_adet = int(filtered_df['ADET'].sum()) if 'ADET' in filtered_df.columns else 0
        st.markdown(f'<div class="metric-card"><h3 style="color:#34d399;margin:0;font-size:16px;">Toplam Ürün Adeti</h3><h2 style="margin:10px 0 0 0;font-size:28px;color:#34d399;">{toplam_adet:,}</h2></div>', unsafe_allow_html=True)
    with col3:
        tur_counts = filtered_df['TUR'].value_counts() if 'TUR' in filtered_df.columns else {}
        hava_count = tur_counts.get('HAVA', 0) + tur_counts.get('UÇAK', 0)
        st.markdown(f'<div class="metric-card"><h3 style="color:#fb923c;margin:0;font-size:16px;">Hava / Uçak Sevkiyat</h3><h2 style="margin:10px 0 0 0;font-size:28px;color:#fb923c;">{hava_count} Kalem</h2></div>', unsafe_allow_html=True)
    with col4:
        deniz_count = tur_counts.get('GEMİ', 0) + tur_counts.get('DENİZ', 0)
        st.markdown(f'<div class="metric-card"><h3 style="color:#c084fc;margin:0;font-size:16px;">Gemi / Deniz Sevkiyat</h3><h2 style="margin:10px 0 0 0;font-size:28px;color:#c084fc;">{deniz_count} Kalem</h2></div>', unsafe_allow_html=True)

    st.write("---")

    # 5. GRAFİKLER (Özel Renk Paletiyle)
    left_chart, right_chart = st.columns(2)

    with left_chart:
        if 'FIRMA' in filtered_df.columns and 'ADET' in filtered_df.columns:
            st.subheader("📈 Firma Bazlı Yükleme Yoğunluğu")
            fig1 = px.bar(
                filtered_df, x='FIRMA', y='ADET', 
                color='TUR' if 'TUR' in filtered_df.columns else None,
                template='plotly_dark',
                barmode='stack',
                # Burada hangi taşıma türünün hangi renk olacağını sen seçiyorsun:
                color_discrete_map={'GEMİ': '#c084fc', 'DENİZ': '#60a5fa', 'UÇAK': '#34d399', 'HAVA': '#fb923c'}
            )
            fig1.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig1, use_container_width=True)

    with right_chart:
        if 'MALIN CINSI' in filtered_df.columns and 'ADET' in filtered_df.columns:
            st.subheader("📦 En Çok Sipariş Edilen Ürün Tipleri (Top 10)")
            top_products = filtered_df.groupby('MALIN CINSI')['ADET'].sum().reset_index().sort_values(by='ADET', ascending=False).head(10)
            fig2 = px.bar(
                top_products, x='ADET', y='MALIN CINSI', 
                orientation='h', template='plotly_dark',
                color_discrete_sequence=['#38bdf8'] # Çubukların rengi
            )
            fig2.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig2, use_container_width=True)

    # 6. ALT KISIM DİNAMİK LİSTE
    st.write("---")
    st.subheader("📋 Filtrelenmiş Sipariş Listesi")
    st.dataframe(filtered_df, use_container_width=True)

except Exception as e:
    st.error(f"Veri işlenirken hata oluştu: {e}")