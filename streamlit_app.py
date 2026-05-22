import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import time
from datetime import datetime

# ==============================================================================
# 1. GLOBAL SAYFA VE SİBER-PUNK TEMA AYARLARI
# ==============================================================================
st.set_page_config(
    page_title="Zore Aksesuar Genel Kontrol Merkezi",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Tamamen özelleştirilmiş karanlık arayüz, neon metrik kartları ve border tasarımları
st.markdown("""
    <style>
    .main { background-color: #06090e; color: #f0f6fc; }
    div[data-testid="stSidebarCollapseButton"] {     color: #00cc96; }
    .stHeading h1 { color: #ffffff; font-family: 'Courier New', Courier, monospace; font-weight: 800; }
    
    /* Metrik Kartları Özelleştirmeleri */
    .metric-container {
        background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    }
    .metric-title {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #8b949e;
        margin-bottom: 10px;
    }
    .metric-value-1 { font-size: 32px; font-weight: bold; color: #00f0ff; font-family: 'Impact', sans-serif; }
    .metric-value-2 { font-size: 32px; font-weight: bold; color: #ff00ea; font-family: 'Impact', sans-serif; }
    .metric-value-3 { font-size: 32px; font-weight: bold; color: #00ff66; font-family: 'Impact', sans-serif; }
    
    /* Grafik Panel Kutuları */
    .chart-box {
        background-color: #0d1117;
        border: 1px solid #21262d;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. VERİ KAYNAĞI VE SİMÜLASYON MOTORU (Pandas Sürüm Hataları Giderilmiş Tam Yapı)
# ==============================================================================
@st.cache_data
def load_production_cyber_data():
    """
    Ekran görüntülerindeki gerçek ürün gruplarını, markaları ve ciro limitlerini 
    birebir taklit eden, Pandas 'h' bugından arındırılmış veri üretim motoru.
    """
    np.random.seed(101)
    # Pandas 3.14+ uyumlu küçük 'h' harfiyle saatlik periyot oluşturma
    dates = pd.date_range(start="2026-01-01 00:00:00", end="2026-05-22 12:00:00", freq="h")
    
    # Ekran görüntülerinde geçen birebir ürün adları
    urunler = [
        "ZT03 Charger Kit white", "ZT05 Charger Kit white", "VD-TC019BA Charger white",
        "ZORE CL-12 IP 17 PRO-İP 17 PRO MAX LACİVERT TEMPERLİ CAM", 
        "ZORE CL-12 IP 17 PRO-İP 17 PRO MAX TURUNCU TEMPERLİ CAM",
        "VD-DC20CC White", "ZT04 Charger Kit white", "ZT06 Charger Kit white"
    ]
    
    # Ekran görüntülerindeki aktör firmalar ve kategoriler
    firmalar = ["BENKS", "WIWU", "ANNY", "LENYES", "RAPTIC", "KEL", "MOHSEVEN", "PITAKA", "CG MOBILE", "JUDY", "VENDES", "CATHY"]
    turler = ["KAPAK", "EKRAN KORUYUCU", "LENS KORUYUCU", "KILIF", "POWERBANK", "ŞARJ ALETİ", "KULAKLIK", "FAN", "SPEAKER", "TABLET KILIF", "KABLO"]
    
    data_list = []
    for current_date in dates:
        # Rastgele kayıt yoğunluğu kontrolü
        if np.random.rand() > 0.15:
            continue
            
        u_idx = np.random.randint(0, len(urunler))
        f_idx = np.random.randint(0, len(firmalar))
        t_idx = np.random.randint(0, len(turler))
        
        adet = int(np.random.randint(10, 500))
        # Toplam sermaye limitlerini milyon seviyesine getirecek birim fiyat çarpanı
        birim_fiyat = float(np.random.uniform(50, 1200))
        toplam_sermaye = adet * birim_fiyat
        
        # Dinamik aylık büyüme trendi enjekte etme
        if current_date.month == 1: toplam_sermaye *= 1.8
        elif current_date.month == 4: toplam_sermaye *= 1.4
        elif current_date.month == 5: toplam_sermaye *= 1.2
        
        data_list.append({
            "Tarih": current_date,
            "Ürün_Adı": urunler[u_idx],
            "FIRMA": firmalar[f_idx],
            "MALIN_CINSI": turler[t_idx],
            "ADET": adet,
            "TOPLAM_SERMAYE": toplam_sermaye,
            "DURUM": np.random.choice(["TAMAMLANDI", "SEVKİYATTA", "REZERVE", "BEKLEMEDE"], p=[0.75, 0.15, 0.07, 0.03])
        })
        
    df = pd.DataFrame(data_list)
    # Sıkı koruma kuralı: Sadece 2026 verileri kalacak
    df["Tarih"] = pd.to_datetime(df["Tarih"])
    df = df[(df["Tarih"] >= "2026-01-01") & (df["Tarih"] <= "2026-12-31")]
    return df

# Ana ham veri kaynağını yükle
df_master = load_production_cyber_data()

# ==============================================================================
# 3. YAN PANEL (SIDEBAR) KONTROLLERİ VE FİLM MODU TETİKLEYİCİSİ
# ==============================================================================
st.sidebar.title("🛠️ Kontrol Matrisi")
st.sidebar.markdown("---")

app_mode = st.sidebar.radio(
    "Görünüm Modu Seçiniz:",
    ["📊 Genel Statik Dashboard", "🎬 Canlı Sinematik Döngü Koridoru (Film Modu)"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📅 Manuel Dönem Filtresi")
ay_secenekleri = {
    "Tüm Dönem (Ocak - Mayıs)": "ALL",
    "2026-01 (Ocak)": 1,
    "2026-02 (Şubat)": 2,
    "2026-03 (Mart)": 3,
    "2026-04 (Nisan)": 4,
    "2026-05 (Mayıs)": 5
}
selected_month_label = st.sidebar.selectbox("Analiz Edilecek Ay:", list(ay_secenekleri.keys()))
selected_month_val = ay_secenekleri[selected_month_label]

# Veriyi yan panel seçimine göre daraltma (Statik mod için)
if selected_month_val != "ALL" and app_mode == "📊 Genel Statik Dashboard":
    df_filtered = df_master[df_master["Tarih"].dt.month == selected_month_val]
else:
    df_filtered = df_master.copy()

# ==============================================================================
# MAPPING MOD - 1: GENEL STATİK DASHBOARD (Eksiksiz 8 Grafik Matrisi)
# ==============================================================================
if app_mode == "📊 Genel Statik Dashboard":
    
    # Üst Başlık Grubu
    st.title("📊 Genel Dashboard")
    st.markdown("Sistem Veri Matris Odası - Gerçek Zamanlı Sipariş ve Finansal İzleme Modülü")
    
    # KANLI METRİK KARTLARI (Tam Hesaplamalı)
    total_pcs = df_filtered["ADET"].sum()
    total_usd = df_filtered["TOPLAM_SERMAYE"].sum()
    total_firms = df_filtered["FIRMA"].nunique()
    
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">📦 TOPLAM SİPARİŞ ADETİ</div>
                <div class="metric-value-1">{total_pcs:,} <span style="font-size:16px;">Adet</span></div>
            </div>
        """, unsafe_allow_html=True)
    with m_col2:
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">💰 TOPLAM SERMAYE YATIRIMI (USD)</div>
                <div class="metric-value-2">{total_usd:,.2f} <span style="font-size:16px;">$</span></div>
            </div>
        """, unsafe_allow_html=True)
    with m_col3:
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">🏢 ÇALIŞILAN FİRMA SAYISI</div>
                <div class="metric-value-3">{total_firms} <span style="font-size:16px;">Firma</span></div>
            </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --------------------------------------------------------------------------
    # GRID SATIR 1 (Grafik 1 & Grafik 2)
    # --------------------------------------------------------------------------
    r1_c1, r1_c2 = st.columns(2)
    
    with r1_c1:
        st.markdown("<div class='chart-box'>", unsafe_allow_html=True)
        st.markdown("### // En Çok Sipariş Edilen Ürünler (Adet)")
        g1_df = df_filtered.groupby("Ürün_Adı")["ADET"].sum().reset_index().sort_values(by="ADET", ascending=True).tail(8)
        fig1 = px.bar(
            g1_df, x="ADET", y="Ürün_Adı", orientation="h",
            color="ADET", color_continuous_scale=["#0052d4", "#4364f7", "#6fb1fc"]
        )
        fig1.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=10, b=10), height=340, xaxis_title="", yaxis_title=""
        )
        fig1.update_xaxes(showgrid=True, gridcolor="#1f2937")
        fig1.update_yaxes(showgrid=False)
        st.plotly_chart(fig1, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with r1_c2:
        st.markdown("<div class='chart-box'>", unsafe_allow_html=True)
        st.markdown("### // En Büyük 7 Aktör Sermaye Dağılımı")
        g2_df = df_filtered.groupby("FIRMA")["TOPLAM_SERMAYE"].sum().reset_index().sort_values(by="TOPLAM_SERMAYE", ascending=False).head(7)
        fig2 = px.bar(
            g2_df, x="FIRMA", y="TOPLAM_SERMAYE",
            color="TOPLAM_SERMAYE", color_continuous_scale=["#00c6ff", "#0072ff"]
        )
        fig2.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=10, b=10), height=340, xaxis_title="", yaxis_title=""
        )
        fig2.update_yaxes(showgrid=True, gridcolor="#1f2937")
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # GRID SATIR 2 (Grafik 3 & Grafik 4)
    # --------------------------------------------------------------------------
    r2_c1, r2_c2 = st.columns(2)
    
    with r2_c1:
        st.markdown("<div class='chart-box'>", unsafe_allow_html=True)
        st.markdown("### // Periyodik Hız Haritası Akışkanlığı")
        g3_df = df_filtered.groupby(df_filtered["Tarih"].dt.to_period("M"))["TOPLAM_SERMAYE"].sum().reset_index()
        g3_df["Tarih"] = g3_df["Tarih"].astype(str)
        fig3 = px.line(g3_df, x="Tarih", y="TOPLAM_SERMAYE", markers=True)
        fig3.update_traces(line=dict(color="#00ff66", width=3), marker=dict(size=8, color="#ffffff"))
        fig3.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=10, b=10), height=340, xaxis_title="", yaxis_title=""
        )
        fig3.update_xaxes(showgrid=True, gridcolor="#1f2937")
        fig3.update_yaxes(showgrid=True, gridcolor="#1f2937")
        st.plotly_chart(fig3, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with r2_c2:
        st.markdown("<div class='chart-box'>", unsafe_allow_html=True)
        st.markdown("### // Sektörel Log Matris Oranları")
        g4_df = df_filtered.groupby("MALIN_CINSI")["TOPLAM_SERMAYE"].sum().reset_index()
        fig4 = go.Figure(data=[go.Pie(
            labels=g4_df["MALIN_CINSI"], values=g4_df["TOPLAM_SERMAYE"],
            hole=0.6,
            marker=dict(colors=px.colors.qualitative.Cyber)
        )])
        fig4.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=10, b=10), height=340, showlegend=True,
            annotations=[dict(text="ZORE RADAR", x=0.5, y=0.5, font_size=14, font_color="#00f0ff", font_family="monospace", showarrow=False)]
        )
        st.plotly_chart(fig4, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # GRID SATIR 3 (Grafik 5 & Grafik 6)
    # --------------------------------------------------------------------------
    r3_c1, r3_c2 = st.columns(2)
    
    with r3_c1:
        st.markdown("<div class='chart-box'>", unsafe_allow_html=True)
        st.markdown("### // Harcama Yapılan İlk 10 Firmanın Aylık Hacmi ($)")
        g5_df = df_filtered.groupby("FIRMA")["TOPLAM_SERMAYE"].sum().reset_index().sort_values(by="TOPLAM_SERMAYE", ascending=True).tail(10)
        fig5 = px.bar(g5_df, x="TOPLAM_SERMAYE", y="FIRMA", orientation="h", color="FIRMA", color_discrete_sequence=px.colors.qualitative.Bold)
        fig5.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=10, b=10), height=340, showlegend=False, xaxis_title="", yaxis_title=""
        )
        fig5.update_xaxes(showgrid=True, gridcolor="#1f2937")
        st.plotly_chart(fig5, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with r3_c2:
        st.markdown("<div class='chart-box'>", unsafe_allow_html=True)
        st.markdown("### // Tür Bazlı Harcama Dağılımı Matrix Görünüm")
        g6_df = df_filtered.groupby("MALIN_CINSI")["ADET"].sum().reset_index().sort_values(by="ADET", ascending=False)
        fig6 = px.pie(g6_df, values="ADET", names="MALIN_CINSI", color_discrete_sequence=px.colors.qualitative.Prism)
        fig6.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=10, b=10), height=340, showlegend=True
        )
        st.plotly_chart(fig6, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # GRID SATIR 4 (Grafik 7 & Grafik 8)
    # --------------------------------------------------------------------------
    r4_c1, r4_c2 = st.columns(2)
    
    with r4_c1:
        st.markdown("<div class='chart-box'>", unsafe_allow_html=True)
        st.markdown("### // Sevkiyat ve Sipariş Durum Akış Hunisi")
        g7_df = df_filtered.groupby("DURUM")["ADET"].sum().reset_index().sort_values(by="ADET", ascending=False)
        fig7 = px.funnel(g7_df, x="ADET", y="DURUM", color="DURUM", color_discrete_sequence=["#ff00ea", "#00f0ff", "#00ff66", "#ffcc00"])
        fig7.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=10, b=10), height=340, showlegend=False, xaxis_title="", yaxis_title=""
        )
        st.plotly_chart(fig7, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with r4_c2:
        st.markdown("<div class='chart-box'>", unsafe_allow_html=True)
        st.markdown("### // Firma Yoğunluk ve Finansal Güç Korelasyonu")
        g8_df = df_filtered.groupby("FIRMA").agg({"ADET": "sum", "TOPLAM_SERMAYE": "sum"}).reset_index()
        fig8 = px.scatter(
            g8_df, x="ADET", y="TOPLAM_SERMAYE", text="FIRMA", size="TOPLAM_SERMAYE",
            color="TOPLAM_SERMAYE", color_continuous_scale="Viridis", size_max=40
        )
        fig8.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=10, b=10), height=340, xaxis_title="Kümülatif Sipariş Adedi", yaxis_title="Sermaye Hacmi ($)"
        )
        fig8.update_xaxes(showgrid=True, gridcolor="#1f2937")
        fig8.update_yaxes(showgrid=True, gridcolor="#1f2937")
        st.plotly_chart(fig8, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# MAPPING MOD - 2: CANLI SİNEMATİK DÖNGÜ KORİDORU (Hata Veren Altyapı Düzeltildi)
# ==============================================================================
elif app_mode == "🎬 Canlı Sinematik Döngü Koridoru (Film Modu)":
    
    st.title("🎬 Canlı Sinematik Döngü Koridoru")
    st.markdown("**Tarayıcı Motoru Aktif:** Sistem aylık verileri sırayla tarayarak otomatik döngüde sinematik akış sağlar.")
    
    # Animasyon Kontrol Düğmeleri
    loop_control_col1, loop_control_col2 = st.columns([1, 5])
    with loop_control_col1:
        start_loop = st.button("🚀 Döngüyü Başlat")
    with loop_control_col2:
        loop_speed = st.slider("Tarama Hızı (Saniye):", min_value=1.0, max_value=5.0, value=2.0, step=0.5)
        
    # Dinamik Olarak Güncellenecek Boş Streamlit Konteynerleri (Layout Alanları)
    status_indicator = st.empty()
    metric_dashboard_row = st.empty()
    st.markdown("---")
    chart_row_1 = st.empty()
    chart_row_2 = st.empty()
    
    # Döngü Tetikleme Mantığı
    if start_loop:
        # 2026'nın ilk 5 ayını sürekli döndür
        months_to_loop = [1, 2, 3, 4, 5]
        month_names = {1: "Ocak 2026", 2: "Şubat 2026", 3: "Mart 2026", 4: "Nisan 2026", 5: "Mayıs 2026"}
        
        while True:
            for active_month in months_to_loop:
                # Canlı veri filtresi
                df_live = df_master[df_master["Tarih"].dt.month == active_month]
                
                # Bilgi Durum Çubuğunu Güncelle
                status_indicator.markdown(f"### 🟢 Aktif Taranan Dönem: `{month_names[active_month]}` | `[ SİSTEM SÜREKLİ DÖNGÜDE - FİLM MODU AKTİF ]`")
                
                # 1. Metrik Kartları Konteyner Güncellemesi
                l_pcs = df_live["ADET"].sum()
                l_usd = df_live["TOPLAM_SERMAYE"].sum()
                l_firms = df_live["FIRMA"].nunique()
                
                metric_dashboard_row.markdown(f"""
                    <div style="display: flex; justify-content: space-between; gap: 15px; width: 100%;">
                        <div class="metric-container" style="flex: 1;">
                            <div class="metric-title">💻 CANLI SEVKİYAT ADET MÜHİMMATI</div>
                            <div class="metric-value-1">{l_pcs:,} <span style="font-size:14px;">Pcs</span></div>
                        </div>
                        <div class="metric-container" style="flex: 1;">
                            <div class="metric-title">⚡ ENJEKTE EDİLEN TOPLAM FİNANSAL GÜÇ</div>
                            <div class="metric-value-2">{l_usd:,.2f} <span style="font-size:14px;">$</span></div>
                        </div>
                        <div class="metric-container" style="flex: 1;">
                            <div class="metric-title">👁️ MONITORINGDEKİ GLOBAL PARTNERLER</div>
                            <div class="metric-value-3">{l_firms} <span style="font-size:14px;">Firma</span></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                # 2. Grafik Satırı 1 (Firmaların Güç Yarışı & Tür Dağılım Matrisi)
                with chart_row_1.container():
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("#### 3. Firmaların Aylık Birikimli Güç Yarışı (Sinematik Akış)")
                        g5_live = df_live.groupby("FIRMA")["TOPLAM_SERMAYE"].sum().reset_index().sort_values(by="TOPLAM_SERMAYE", ascending=True).tail(10)
                        fig5_l = px.bar(g5_live, x="TOPLAM_SERMAYE", y="FIRMA", orientation="h", color="TOPLAM_SERMAYE", color_continuous_scale="Turbo")
                        fig5_l.update_layout(
                            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            margin=dict(l=20, r=20, t=10, b=10), height=350, xaxis_title="", yaxis_title=""
                        )
                        # Slayt çökmesini engelleyen güvenli güncelleme
                        fig5_l.layout.coloraxis.showscale = False
                        st.plotly_chart(fig5_l, use_container_width=True)
                        
                    with c2:
                        st.markdown(f"#### 4. {month_names[active_month]} Dönemi Tür Dağılım Matrisi")
                        g4_live = df_live.groupby("MALIN_CINSI")["TOPLAM_SERMAYE"].sum().reset_index()
                        fig4_l = go.Figure(data=[go.Pie(
                            labels=g4_live["MALIN_CINSI"], values=g4_live["TOPLAM_SERMAYE"],
                            hole=0.6, marker=dict(colors=px.colors.qualitative.Neon)
                        )])
                        fig4_l.update_layout(
                            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            margin=dict(l=20, r=20, t=10, b=10), height=350, showlegend=False,
                            annotations=[dict(text="ZORE RADAR", x=0.5, y=0.5, font_size=13, font_color="#ff00ea", font_family="monospace", showarrow=False)]
                        )
                        st.plotly_chart(fig4_l, use_container_width=True)
                
                # 3. Grafik Satırı 2 (Ürün Hacmi & Durum Analizleri)
                with chart_row_2.container():
                    c3, c4 = st.columns(2)
                    with c3:
                        st.markdown("#### // Anlık En Çok Sipariş Edilen Hatlar")
                        g1_live = df_live.groupby("Ürün_Adı")["ADET"].sum().reset_index().sort_values(by="ADET", ascending=True).tail(5)
                        fig1_l = px.bar(g1_live, x="ADET", y="Ürün_Adı", orientation="h", color="ADET", color_continuous_scale="Aggrnyl")
                        fig1_l.update_layout(
                            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            margin=dict(l=20, r=20, t=10, b=10), height=320, xaxis_title="", yaxis_title=""
                        )
                        fig1_l.layout.coloraxis.showscale = False
                        st.plotly_chart(fig1_l, use_container_width=True)
                        
                    with c4:
                        st.markdown("#### // Operasyon Lojistik Dağılım İndeksi")
                        g7_live = df_live.groupby("DURUM")["ADET"].sum().reset_index()
                        fig7_l = px.pie(g7_live, values="ADET", names="DURUM", color_discrete_sequence=px.colors.qualitative.Pastel)
                        fig7_l.update_layout(
                            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            margin=dict(l=20, r=20, t=10, b=10), height=320, showlegend=True
                        )
                        st.plotly_chart(fig7_l, use_container_width=True)
                
                # Ayarlar panelinden gelen hız kontrolü kadar uyut
                time.sleep(loop_speed)
    else:
        st.info("Sinematik akışı başlatmak için sol taraftaki 'Döngüyü Başlat' butonuna basın.")