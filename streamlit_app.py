import streamlit as st
import pandas as pd
import requests
import io
import openpyxl
import datetime
import json

# --- SİBER UZAY KOMUTA AYARLARI ---
st.set_page_config(layout="wide", page_title="ZORE WAR ROOM SYSTEM")

# Tam Ekran ve Arka Plan Stabilizasyonu (CSS)
st.markdown("""
<style>
    .reportview-container { background: #060913 !important; }
    .stDeployButton { display:none !important; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    div.block-container { padding-top: 1rem; padding-bottom: 0rem; }
</style>
""", unsafe_allow_html=True)

# Veri Kaynakları Havuzu
LINKS = [
    "https://docs.google.com/spreadsheets/d/1j819WkX93CkCy3VgZkSff5C_zNX5Z98jfK-FwI4ZWUU/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1hVk6VgMFXWAukoQwMDIoOLrG8SD4UDLFFRH9VmDhXSE/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1S1kTptWUEf705cBLw9P9mL6rrqbVjbcp1xk_hgQ-Ny0/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1VKb6za4Fse5XrGawPG6qvrQZuFhDRGaAysmADGIC7Wc/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=xlsx"
]

TARGET_TABS = ["has_air", "has_sea", "meh_air", "meh_sea", "ist_air", "ist_sea"]
HEADER_MAP = {
    'SIPARIS TARIHI': 'SIPARIS_TARIHI', 'SIPARIS_TARIHI': 'SIPARIS_TARIHI',
    'FIRMA': 'FIRMA', 'TUR': 'TUR', 'BARKOD': 'BARKOD',
    'MALIN CINSI': 'MALIN CINSI', 'ADET': 'ADET', 'FIYAT': 'FIYAT',
    'YUKLEME TARIHI': 'YUKLEME_TARIHI', 'YUKLEME_TARIHI': 'YUKLEME_TARIHI'
}

# --- STATİK GEÇİCİ DÖVİZ MOTORU ---
rates = {"EUR_TO_USD": 1.09, "CNY_TO_USD": 0.138}

def strict_date_parser(val):
    if pd.isna(val) or val == "": return "BELİRTİLMEMİŞ"
    if hasattr(val, 'strftime'): return val.strftime('%Y-%m-%d')
    s = str(val).strip().split()[0].replace('/', '.').replace('-', '.')
    for fmt in ['%Y.%m.%d', '%d.%m.%Y']:
        try: return datetime.datetime.strptime(s, fmt).strftime('%Y-%m-%d')
        except: continue
    return "BELİRTİLMEMİŞ"

def clean_and_process(df):
    df = df.loc[:, ~df.columns.duplicated()]
    if 'SIPARIS_TARIHI' in df.columns:
        df['SIPARIS_TARIHI'] = df['SIPARIS_TARIHI'].apply(strict_date_parser)
    if 'ADET' in df.columns:
        df['ADET'] = pd.to_numeric(df['ADET'], errors='coerce').fillna(0)
    if 'FIYAT' in df.columns:
        def parse_price(row):
            v = str(row['FIYAT']).upper().strip()
            firma = str(row.get('FIRMA', '')).upper()
            mult = 1.0
            if 'CATHY' in firma or any(x in v for x in ['¥', '￥', 'CNY']): mult = rates["CNY_TO_USD"]
            elif any(x in v for x in ['€', 'EUR']): mult = rates["EUR_TO_USD"]
            cleaned = re.sub(r'[^\d.,]', '', v)
            if ',' in cleaned and '.' in cleaned:
                if cleaned.find(',') > cleaned.find('.'): cleaned = cleaned.replace('.', '').replace(',', '.')
                else: cleaned = cleaned.replace(',', '')
            else: cleaned = cleaned.replace(',', '.')
            try: return float(cleaned) * mult
            except: return 0.0
        df['TOPLAM_SERMAYE'] = df['ADET'] * df.apply(parse_price, axis=1)
    else:
        df['TOPLAM_SERMAYE'] = 0.0
    return df

@st.cache_data(ttl=300)
def load_war_room_data():
    master_list = []
    for link in LINKS:
        try:
            res = requests.get(link, timeout=10)
            if res.status_code != 200: continue
            wb = openpyxl.load_workbook(io.BytesIO(res.content), data_only=True)
            for tab in TARGET_TABS:
                if tab in wb.sheetnames:
                    sheet = wb[tab]
                    rows = list(sheet.iter_rows(values_only=False))
                    if not rows: continue
                    headers = [HEADER_MAP.get(str(c.value).strip().upper().replace('İ','I'), str(c.value)) for c in rows[0]]
                    data = [[cell.value for cell in r] for r in rows[1:] if not all(cell.value is None for cell in r)]
                    sub_df = pd.DataFrame(data, columns=headers[:len(data[0])])
                    master_list.append(clean_and_process(sub_df))
        except: continue
    return pd.concat(master_list, ignore_index=True) if master_list else pd.DataFrame()

df_raw = load_war_room_data()

if df_raw.empty:
    st.error("🚨 SİBER VERİ MATRİSİ ALINAMADI. BAĞLANTILARI KONTROL EDİN.")
else:
    # 2026 Filtresi ve Agregasyonlar
    df_raw['AY'] = df_raw['SIPARIS_TARIHI'].str[:7]
    df_2026 = df_raw[df_raw['AY'].str.startswith('2026', na=False)].copy()
    
    # Metrik Hesaplamaları
    total_adet = int(df_2026['ADET'].sum())
    total_sermaye = float(df_2026['TOPLAM_SERMAYE'].sum())
    active_firms = int(df_2026['FIRMA'].dropna().nunique())
    
    # ECharts İçin Veri Hazırlığı (JSON formatına dönüştürme)
    top_firms = df_2026.groupby('FIRMA')['TOPLAM_SERMAYE'].sum().nlargest(7).reset_index()
    firms_json = top_firms['FIRMA'].tolist()
    sermaye_json = top_firms['TOPLAM_SERMAYE'].round(2).tolist()
    
    top_categories = df_2026.groupby('TUR')['ADET'].sum().nlargest(6).reset_index()
    cat_pie_data = [{"value": int(row['ADET']), "name": str(row['TUR'])} for _, row in top_categories.iterrows()]
    
    trend_data = df_2026.groupby('AY')['TOPLAM_SERMAYE'].sum().sort_index().reset_index()
    trend_months = trend_data['AY'].tolist()
    trend_values = trend_data['TOPLAM_SERMAYE'].round(2).tolist()

    # --- CANVAS & WEBGL WAR ROOM MOTORU (HTML/JS ENJEKSİYONU) ---
    war_room_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
        <style>
            body {{
                background-color: #060913;
                color: #00f3ff;
                font-family: 'Courier New', monospace;
                margin: 0;
                padding: 10px;
                overflow-x: hidden;
            }}
            /* Üst Siber Panel Kartları */
            .header-container {{
                display: flex;
                justify-content: space-between;
                gap: 15px;
                margin-bottom: 20px;
            }}
            .metric-card {{
                flex: 1;
                background: linear-gradient(135deg, rgba(10,24,50,0.8) 0%, rgba(5,12,30,0.9) 100%);
                border: 1px solid #00f3ff;
                box-shadow: 0 0 15px rgba(0, 243, 255, 0.2);
                border-radius: 6px;
                padding: 15px;
                text-align: center;
                position: relative;
                overflow: hidden;
            }}
            .metric-card::before {{
                content: '';
                position: absolute;
                top: 0; left: -100%;
                width: 100%; height: 2px;
                background: linear-gradient(90deg, transparent, #00f3ff, transparent);
                animation: scanline 3s linear infinite;
            }}
            .metric-title {{
                font-size: 11px;
                letter-spacing: 2px;
                color: #88a0c0;
                margin: 0;
            }}
            .metric-value {{
                font-size: 28px;
                font-weight: bold;
                color: #ffffff;
                margin: 5px 0 0 0;
                text-shadow: 0 0 10px rgba(0, 243, 255, 0.6);
            }}
            /* Grafik Grid Düzeni */
            .grid-container {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 20px;
            }}
            .chart-panel {{
                background: rgba(10, 18, 36, 0.6);
                border: 1px solid rgba(0, 243, 255, 0.15);
                border-radius: 8px;
                padding: 15px;
                height: 380px;
                box-shadow: inset 0 0 20px rgba(0,0,0,0.5);
            }}
            .full-width-panel {{
                grid-column: span 2;
                height: 300px;
            }}
            /* Siber Radar Gradiyent Efekti */
            @keyframes scanline {{
                0% {{ left: -100%; }}
                100% {{ left: 100%; }}
            }}
        </style>
    </head>
    <body>

        <div class="header-container">
            <div class="metric-card" style="border-color: #00f3ff; box-shadow: 0 0 15px rgba(0, 243, 255, 0.15);">
                <p class="metric-title">🛸 SEVKİYAT MÜHİMMAT HACMİ</p>
                <p class="metric-value">{total_adet:,} ADET</p>
            </div>
            <div class="metric-card" style="border-color: #ff00ff; box-shadow: 0 0 15px rgba(255, 0, 255, 0.15);">
                <p class="metric-title">⚡ ENJEKTE EDİLEN TOPLAM SERMAYE</p>
                <p class="metric-value">{total_sermaye:,.2f} $</p>
            </div>
            <div class="metric-card" style="border-color: #00ff66; box-shadow: 0 0 15px rgba(0, 255, 102, 0.15);">
                <p class="metric-title">👁️ AKTİF TAKİPTEKİ GLOBAL ODAKLAR</p>
                <p class="metric-value">{active_firms} FİRMA</p>
            </div>
        </div>

        <div class="grid-container">
            <div id="chart_bar" class="chart-panel"></div>
            <div id="chart_pie" class="chart-panel"></div>
            <div id="chart_line" class="chart-panel full-width-panel"></div>
        </div>

        <script>
            // Python'dan Gelen Canlı Veri Setleri
            const firms = {json.dumps(firms_json)};
            const sermaye = {json.dumps(sermaye_json)};
            const pieData = {json.dumps(cat_pie_data)};
            const months = {json.dumps(trend_months)};
            const lineValues = {json.dumps(trend_values)};

            // --- 1. EN BÜYÜK AKTÖRLER BAR GRAFİĞİ (SÜREKLİ AKIŞKAN) ---
            const barChart = echarts.init(document.getElementById('chart_bar'));
            barChart.setOption({{
                backgroundColor: 'transparent',
                title: {{ text: '🟢 TOP 7 GLOBAL AKTÖR SERMAYE DAĞILIMI', textStyle: {{ color: '#00f3ff', fontFamily: 'Courier New', fontSize: 14 }} }},
                tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
                xAxis: {{ type: 'category', data: firms, axisLabel: {{ color: '#88a0c0' }} }},
                yAxis: {{ type: 'value', axisLabel: {{ color: '#88a0c0' }}, splitLine: {{ lineStyle: {{ color: 'rgba(0,243,255,0.05)' }} }} }},
                series: [{{
                    data: sermaye,
                    type: 'bar',
                    itemStyle: {{
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            {{ offset: 0, color: '#00f3ff' }},
                            {{ offset: 1, color: '#7000ff' }}
                        ]),
                        borderRadius: [4, 4, 0, 0]
                    }},
                    showBackground: true,
                    backgroundStyle: {{ color: 'rgba(0, 243, 255, 0.03)' }}
                }}]
            }});

            // --- 2. KATEGORİSEL SİBER RADAR / PASTA MATRİSİ ---
            const pieChart = echarts.init(document.getElementById('chart_pie'));
            pieChart.setOption({{
                backgroundColor: 'transparent',
                title: {{ text: '🔮 SEKTÖREL LOG MATRİS DAĞILIMI', textStyle: {{ color: '#ff00ff', fontFamily: 'Courier New', fontSize: 14 }} }},
                tooltip: {{ trigger: 'item' }},
                series: [{{
                    name: 'Kategori Hacmi',
                    type: 'pie',
                    radius: ['40%', '70%'],
                    avoidLabelOverlap: false,
                    itemStyle: {{ borderRadius: 6, borderColor: '#060913', borderWidth: 2 }},
                    label: {{ show: true, color: '#fff' }},
                    data: pieData,
                    color: ['#00f3ff', '#ff00ff', '#00ff66', '#ffb000', '#7000ff', '#ff0055']
                }}]
            }});

            // --- 3. KÜMÜLATİF DÖNEMSEL HIZ HARİTASI (DALGALI LİNE) ---
            const lineChart = echarts.init(document.getElementById('chart_line'));
            lineChart.setOption({{
                backgroundColor: 'transparent',
                title: {{ text: '📈 2026 PERİYODİK FİNANSAL SPEKTRUM AKIŞI', textStyle: {{ color: '#00ff66', fontFamily: 'Courier New', fontSize: 14 }} }},
                tooltip: {{ trigger: 'axis' }},
                xAxis: {{ type: 'category', data: months, axisLabel: {{ color: '#88a0c0' }}, boundaryGap: false }},
                yAxis: {{ type: 'value', axisLabel: {{ color: '#88a0c0' }}, splitLine: {{ lineStyle: {{ color: 'rgba(0,255,102,0.05)' }} }} }},
                series: [{{
                    data: lineValues,
                    type: 'line',
                    smooth: true,
                    symbol: 'circle',
                    symbolSize: 8,
                    lineStyle: {{ color: '#00ff66', width: 3 }},
                    itemStyle: {{ color: '#ffffff', borderColor: '#00ff66', borderWidth: 2 }},
                    areaStyle: {{
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            {{ offset: 0, color: 'rgba(0,255,102,0.25)' }},
                            {{ offset: 1, color: 'rgba(0,255,102,0.0)' }}
                        ])
                    }}
                }}]
            }});

            // Ekran Boyutu Değiştiğinde Grafiklerin WebGL Motorunu Yeniden Hesapla (Auto-Resize)
            window.addEventListener('resize', function() {{
                barChart.resize();
                pieChart.resize();
                lineChart.resize();
            }});
        </script>
    </body>
    </html>
    """

    # Kodumuzu Streamlit Hücresine Kusursuz Enjekte Ediyoruz (Boyut Ayarlı)
    st.components.v1.html(war_room_html, height=760, scrolling=False)