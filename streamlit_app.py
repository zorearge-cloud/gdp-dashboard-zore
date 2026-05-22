import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ==============================================================================
# 1. SAYFA VE TEMA AYARLARI
# ==============================================================================
st.set_page_config(
    page_title="Zore Aksesuar - Genel Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark tema CSS özelleştirmesi
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stSubheader { color: #f1f1f1; font-weight: 600; border-bottom: 1px solid #333; padding-bottom: 5px; }
    div[data-testid="stBlock"] { background-color: #161b22; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Genel Dashboard Analytics")
st.markdown("Veri analizi, sipariş takibi ve performans kırılımları.")
st.markdown("---")

# ==============================================================================
# 2. YAN PANEL (KENAR ÇUBUĞU) VE VERİ YÜKLEME MECHANISM
# ==============================================================================
st.sidebar.header("📁 Veri Kaynağı Ayarları")
uploaded_file = st.sidebar.file_uploader("Sipariş Dosyasını Yükleyin (.xlsx, .xls, .csv)", type=["xlsx", "xls", "csv"])

@st.cache_data
def generate_fallback_data():
    """Dosya yüklenmediğinde sistemin boş kalmaması için üretilen gerçekçi 2026 verisi."""
    import numpy as np
    np.random.seed(42)
    dates = pd.date_range(start="2026-01-01", end="2026-05-20", freq="H")
    urunler = ["Zore Kılıf", "Lenyes Powerbank", "Zore Ekran Koruyucu", "Lenyes Kablosuz Kulaklık", "Zore Şarj Kablosu", "Ttech Araç Tutucu"]
    kategoriler = ["Kılıf", "Enerji", "Ekran Koruyucu", "Ses Sistemleri", "Kablolar", "Aksesuarlar"]
    markalar = ["Zore", "Lenyes", "Zore", "Lenyes", "Zore", "Ttech"]
    bayiler = ["Gaziantep Şube", "İstanbul Toptan", "Ankara Showroom", "İzmir Distribütör", "Bursa Perakende"]
    durumlar = ["Tamamlandı", "Kargoda", "Hazırlanıyor", "Beklemede"]
    
    data = []
    for i in range(len(dates)):
        idx = np.random.randint(0, len(urunler))
        adet = int(np.random.randint(1, 50))
        fiyat = float(np.random.choice([150, 350, 120, 850, 90, 200]))
        data.append({
            "Tarih": dates[i],
            "Barkod": f"86800000{np.random.randint(1000, 9999)}",
            "Ürün_Adı": urunler[idx],
            "Kategori": kategoriler[idx],
            "Marka": markalar[idx],
            "Bayi_Adı": np.random.choice(bayiler),
            "Adet": adet,
            "Birim_Fiyat": fiyat,
            "Toplam_Tutar": adet * fiyat,
            "Durum": np.random.choice(durumlar, p=[0.7, 0.15, 0.1, 0.05])
        })
    return pd.DataFrame(data)

# Veriyi oku veya fallback mekanizmasını çalıştır
if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith(".csv"):
            df_raw = pd.read_csv(uploaded_file)
        else:
            df_raw = pd.read_excel(uploaded_file)
        st.sidebar.success("Dosya başarıyla yüklendi!")
    except Exception as e:
        st.sidebar.error(f"Dosya okunurken hata oluştu: {e}")
        df_raw = generate_fallback_data()
else:
    st.sidebar.info("Aktif bir dosya yüklenmedi. Simüle edilmiş sistem verileri gösteriliyor.")
    df_raw = generate_fallback_data()

# ==============================================================================
# 3. VERİ TEMİZLEME VE KATI FİLTRE KURALLARI
# ==============================================================================
def clean_and_filter_data(df_input):
    df = df_input.copy()
    
    # Standart sütun isimleri kontrolü / eşleme kolaylığı
    # Eğer yüklenen dosyada farklı isimler varsa standart isimlere çekiyoruz
    rename_dict = {
        "Sipariş Tarihi": "Tarih", "Tarih/Saat": "Tarih",
        "Ürün Adı": "Ürün_Adı", "Mal Malzeme Adı": "Ürün_Adı",
        "Miktar": "Adet", "Sipariş Adedi": "Adet",
        "Tutar": "Toplam_Tutar", "Net Tutar": "Toplam_Tutar",
        "Müşteri Adı": "Bayi_Adı", "Cari Ünvan": "Bayi_Adı"
    }
    df = df.rename(columns=rename_dict)
    
    # Tarih dönüşümü
    if "Tarih" in df.columns:
        df["Tarih"] = pd.to_datetime(df["Tarih"], errors='coerce')
    else:
        df["Tarih"] = pd.date_range(start="2026-01-01", periods=len(df), freq="D")
        
    # Eksik veya bozuk tarihleri temizle
    df = df.dropna(subset=["Tarih"])
    
    # KURAL: Sadece 2026 yılı siparişleri kabul edilir. 2024, 2025 veya hatalı gelecek tarihler elenir.
    df = df[(df["Tarih"] >= "2026-01-01") & (df["Tarih"] <= "2026-12-31")]
    
    # Eksik olabilecek diğer dinamik sütunları güvenli hale getir
    if "Adet" not in df.columns: df["Adet"] = 1
    if "Toplam_Tutar" not in df.columns: 
        if "Birim_Fiyat" in df.columns: df["Toplam_Tutar"] = df["Adet"] * df["Birim_Fiyat"]
        else: df["Toplam_Tutar"] = df["Adet"] * 100
        
    if "Kategori" not in df.columns: df["Kategori"] = "Genel Kategori"
    if "Marka" not in df.columns: df["Marka"] = "Belirtilmemiş"
    if "Bayi_Adı" not in df.columns: df["Bayi_Adı"] = "Diğer Bayi"
    if "Durum" not in df.columns: df["Durum"] = "İşlemde"
    
    # Sayısal alanları zorla dönüştür
    df["Adet"] = pd.to_numeric(df["Adet"], errors='coerce').fillna(0)
    df["Toplam_Tutar"] = pd.to_numeric(df["Toplam_Tutar"], errors='coerce').fillna(0)
    
    return df

df_cleaned = clean_and_filter_data(df_raw)

if df_cleaned.empty:
    st.error("Kritik Hata: Filtreleme sonrasında 2026 yılına ait geçerli veri kalmadı! Lütfen girdi dosyasını kontrol edin.")
    st.stop()

# ==============================================================================
# 4. GRAFİK ÇİZİM YARDIMCISI (SAFE PLOT)
# ==============================================================================
def render_chart(fig):
    """Grafiğin çökmesini önler, standart koyu tema düzenini uygular ve ekrana basar."""
    try:
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=35, b=20),
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Grafik çizilirken bir hata oluştu: {e}")

# ==============================================================================
# 5. 8 GRAFİKLİ GENEL DASHBOARD GRID YAPISI
# ==============================================================================

# --- SATIR 1: HACİM VE SERMAYE ANALİZİ ---
st.subheader("📦 Satış Hacmi ve Sermaye Kırılımları")
row1_col1, row1_col2 = st.columns(2)

with row1_col1:
    st.markdown("**1. En Çok Sipariş Edilen Ürünler (Adet Bazlı İlk 10)**")
    g1_data = df_cleaned.groupby("Ürün_Adı")["Adet"].sum().reset_index().sort_values(by="Adet", ascending=True).tail(10)
    fig1 = px.bar(g1_data, x="Adet", y="Ürün_Adı", orientation="h", color="Adet", color_continuous_scale="viridis")
    render_chart(fig1)

with row1_col2:
    st.markdown("**2. En Çok Sermaye Yatırılan / Ciro Yapan Ürünler (Top 10)**")
    g2_data = df_cleaned.groupby("Ürün_Adı")["Toplam_Tutar"].sum().reset_index().sort_values(by="Toplam_Tutar", ascending=False).head(10)
    fig2 = px.bar(g2_data, x="Ürün_Adı", y="Toplam_Tutar", color="Toplam_Tutar", color_continuous_scale="magma")
    render_chart(fig2)

st.markdown("---")

# --- SATIR 2: ZAMAN TRENDLERİ VE KATEGORİ DAĞILIMLARI ---
st.subheader("📈 Zaman Serisi ve Ürün Grupları")
row2_col1, row2_col2 = st.columns(2)

with row2_col1:
    st.markdown("**3. Günlük Sipariş Trendi (2026 Zaman Akışı)**")
    g3_data = df_cleaned.groupby(df_cleaned["Tarih"].dt.date)["Adet"].sum().reset_index()
    fig3 = px.line(g3_data, x="Tarih", y="Adet", markers=True, line_shape="linear")
    fig3.update_traces(line_color="#00cc96")
    render_chart(fig3)

with row2_col2:
    st.markdown("**4. Kategori Bazlı Sipariş Dağılım Oranları**")
    g4_data = df_cleaned.groupby("Kategori")["Adet"].sum().reset_index()
    fig4 = px.pie(g4_data, values="Adet", names="Kategori", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
    render_chart(fig4)

st.markdown("---")

# --- SATIR 3: BAYİ PERFORMANSI VE MARKA KIRILIMLARI ---
st.subheader("🏢 Bayi Performansları ve Marka Ağaç Yapısı")
row3_col1, row3_col2 = st.columns(2)

with row3_col1:
    st.markdown("**5. En Yüksek Sipariş Hacmine Sahip İlk 10 Bayi/Müşteri**")
    g5_data = df_cleaned.groupby("Bayi_Adı")["Toplam_Tutar"].sum().reset_index().sort_values(by="Toplam_Tutar", ascending=True).tail(10)
    fig5 = px.bar(g5_data, x="Toplam_Tutar", y="Bayi_Adı", orientation="h", color="Toplam_Tutar", color_continuous_scale="electric")
    render_chart(fig5)

with row3_col2:
    st.markdown("**6. Marka ve Alt Kategori Dağılım İlişkisi (Treemap)**")
    g6_data = df_cleaned.groupby(["Marka", "Kategori"])["Adet"].sum().reset_index()
    fig6 = px.treemap(g6_data, path=["Marka", "Kategori"], values="Adet", color="Adet", color_continuous_scale="blues")
    render_chart(fig6)

st.markdown("---")

# --- SATIR 4: OPERASYONEL DURUM VE FİYAT/HACİM ANALİZİ ---
st.subheader("⚙️ Operasyonel Durum İzleme ve Korelasyon")
row4_col1, row4_col2 = st.columns(2)

with row4_col1:
    st.markdown("**7. Sipariş Durum Aşamaları Dağılımı (Huni)**")
    g7_data = df_cleaned.groupby("Durum")["Adet"].sum().reset_index().sort_values(by="Adet", ascending=False)
    fig7 = px.funnel(g7_data, x="Adet", y="Durum", color="Durum", color_discrete_sequence=px.colors.qualitative.Safe)
    render_chart(fig7)

with row4_col2:
    st.markdown("**8. Ürün Başına Adet ve Toplam Tutar Dağılım İlişkisi (Scatter)**")
    g8_data = df_cleaned.groupby("Ürün_Adı").agg({"Adet": "sum", "Toplam_Tutar": "sum", "Kategori": "first"}).reset_index()
    fig8 = px.scatter(
        g8_data, 
        x="Adet", 
        y="Toplam_Tutar", 
        size="Adet", 
        color="Kategori", 
        hover_name="Ürün_Adı",
        size_max=35,
        color_discrete_sequence=px.colors.qualitative.Vivid
    )
    render_chart(fig8)