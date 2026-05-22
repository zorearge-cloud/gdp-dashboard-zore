import streamlit as st
import pandas as pd
import requests
import io
import openpyxl
import datetime
import json
import re  # <--- Hatanın kaynağı burasıydı, sisteme enjekte edildi!

# --- SİBER UZAY KOMUTA AYARLARI ---
st.set_page_config(layout="wide", page_title="ZORE WAR ROOM SYSTEM")

# Tam Ekran, Arka Plan Stabilizasyonu ve Streamlit Öğelerini Gizleme (CSS)
st.markdown("""
<style>
    .reportview-container { background: #060913 !important; }
    .stDeployButton { display:none !important; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    div.block-container { padding-top: 1rem; padding-bottom: 0rem; padding-left: 1.5rem; padding-right: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# Canlı Veri Havuzu
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
    error_logs = []
    for idx, link in enumerate(LINKS):
        try:
            res = requests.get(link, timeout=12)
            if res.status_code != 200: 
                error_logs.append(f"Link {idx+1} HTTP Hatası: {res.status_code}")
                continue
            wb = openpyxl.load_workbook(io.BytesIO(res.content), data_only=True)
            for tab in TARGET_TABS:
                if tab in wb.sheetnames:
                    sheet = wb[tab]
                    rows = list(sheet.iter_rows(values_only=False))
                    if not rows or len(rows) < 2: continue
                    headers = [HEADER_MAP.get(str(c.value).strip().upper().replace('İ','I'), str(c.value)) for c in rows[0]]
                    data = [[cell.value for cell in r] for r in rows[1:] if not all(cell.value is None for cell in r)]
                    if not data: continue
                    sub_df = pd.DataFrame(data, columns=headers[:len(data[0])])
                    master_list.append(clean_and_process(sub_df))
        except Exception as e:
            error_logs.append(f"Link {idx+1} İşleme Hatası: {str(e)}")
            continue
    return (pd.concat(master_list, ignore_index=True) if master_list else pd.DataFrame()), error_logs

# Veriyi ve logları çekiyoruz
df_raw, logs = load_war_room_data()

# Eğer arka planda hata varsa sol menüde küçük bir uyarı mekanizması kuruyoruz
if logs:
    with st.sidebar.expander("🛠️ Sistem Terminal Çıktıları"):
        for log in logs: st.caption(log)

if df_raw.empty:
    st.error("🚨 SİBER VERİ MATRİSİ ALINAMADI. Link hatası veya Excel şablon uyuşmazlığı algılandı. Lütfen sol menüdeki terminal çıktılarını kontrol edin.")
else:
    # Veriyi Zaman Eğrisine Bölme ve Filtreleme
    if 'SIPARIS_TARIHI' in df_raw.columns:
        df_raw['AY'] = df_raw['SIPARIS_TARIHI'].str[:7]
    else:
        df_raw['AY'] = "2026-01"
        
    df_2026 = df_raw[df_raw['AY'].str.startswith('2026', na=False)].copy()
    
    if df_2026.empty:
        df_2026 = df_raw.copy() # 2026 boşsa test amaçlı tüm veriyi aç

    # Küresel Metrik Havuzu
    total_adet = int(df_2026['ADET'].sum()) if 'ADET' in df_2026.columns else 0
    total_sermaye = float(df_2026['TOPLAM_SERMAYE'].sum())
    active_firms = int(df_2026['FIRMA'].dropna().nunique()) if 'FIRMA' in df_2026.columns else 0
    
    # ECharts JSON Adaptörleri
    if 'FIRMA' in df_2026.columns:
        top_firms = df_2026.groupby('FIRMA')['TOPLAM_SERMAYE'].sum().nlargest(7).reset_index()
        firms_json = top_firms['FIRMA'].tolist()
        sermaye_json = top_firms['TOPLAM_SERMAYE'].round(2).tolist()
    else:
        firms_json, sermaye_json = ["Firma Yok"], [0]
        
    if 'TUR' in df_2026.columns:
        top_categories = df_2026.groupby('TUR')['ADET'].sum().nlargest(6).reset_index()
        cat_pie_data = [{"value": int(row['ADET']), "name": str(row['TUR'])} for _, row in top_categories.iterrows()]
    else:
        cat_pie_data = [{"value": 0, "name": "Tür Yok"}]
        
    trend_data = df_2026.groupby('AY')['TOPLAM_SERMAYE'].sum().sort_index().reset_index()
    trend_months = trend_data['AY'].tolist()
    trend_values = trend_data['TOPLAM_SERMAYE'].round(2).tolist()

    # --- CANVAS & WEBGL SAVAŞ ODASI ARAYÜZÜ (HTML5 / ECHARTS) ---
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
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 0px;
                overflow: hidden;
            }}
            .header-matrix {{
                display: flex;
                justify-content: space-between;
                gap: 20px;
                margin-bottom: 20px;
            }}
            .matrix-card {{
                flex: 1;
                background: linear-gradient(135deg, rgba(6, 16, 39, 0.9) 0%, rgba(3, 8, 22, 0.95) 100%);
                border: 1px solid rgba(0, 243, 255, 0.3);
                border-radius: 8px;
                padding: 18px;
                text-align: center;
                position: relative;
                box-shadow: 0 0 20px rgba(0, 243, 255, 0.05);
            }}
            .matrix-card::after {{
                content: '';
                position: absolute;
                top: 0; left: 0; width: 100%; height: 100%;
                border-radius: 8px;
                box-shadow: inset 0 0 15px rgba(0, 243, 255, 0.1);
                pointer-events: none;
            }}
            .card-title {{
                font-size: 11px;
                letter-spacing: 3px;
                color: #5f7595;
                margin: 0 0 8px 0;
                font-weight: 600;
            }}
            .card-value {{
                font-size: 32px;
                font-weight: 800;
                color: #ffffff;
                margin: 0;
                text-shadow: 0 0 15px rgba(0, 243, 255, 0.5);
            }}
            .grid-layout {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
            }}
            .panel-box {{
                background: rgba(4, 11, 28, 0.7);
                border: 1px solid rgba(0, 243, 255, 0.12);
                border-radius: 8px;
                padding: 15px;
                height: 340px;
                box-shadow: 0 4px 30px rgba(0, 0, 0, 0.4);
            }}
            .full-panel {{
                grid-column: span 2;
                height: 250px;
            }}
        </style>
    </head>
    <body>

        <div class="header-matrix">
            <div class="matrix-card" style="border-color: rgba(0, 243, 255, 0.45);">
                <p class="card-title">🛸 CANLI SEVKİYAT ADET MÜHİMMATI</p>
                <p class="card-value" style="color: #00f3ff;">{total_adet:,} <span style="font-size:16px; color:#5f7595;">Pcs</span></p>
            </div>
            <div class="matrix-card" style="border-color: rgba(255, 0, 255, 0.45);">
                <p class="card-title">⚡ ENJEKTE EDİLEN TOPLAM FİNANSAL GÜÇ</p>
                <p class="card-value" style="color: #ff00ff;">{total_sermaye:,.2f} <span style="font-size:16px; color:#5f7595;">$</span></p>
            </div>
            <div class="matrix-card" style="border-color: rgba(0, 255, 102, 0.45);">
                <p class="card-title">👁️ MONITORINGDEKİ GLOBAL PARTNERLER</p>
                <p class="card-value" style="color: #00ff66;">{active_firms} <span style="font-size:16px; color:#5f7595;">Firma</span></p>
            </div>
        </div>

        <div class="grid-layout">
            <div id="glow_bar" class="panel-box"></div>
            <div id="glow_pie" class="panel-box"></div>
            <div id="glow_line" class="panel-box full-panel"></div>
        </div>

        <script>
            // Data Transfer Bridge
            const dataFirms = {json.dumps(firms_json)};
            const dataSermaye = {json.dumps(sermaye_json)};
            const dataPie = {json.dumps(cat_pie_data)};
            const dataMonths = {json.dumps(trend_months)};
            const dataLine = {json.dumps(trend_values)};

            // --- 1. SİBER BAR GRAFİĞİ ---
            const barChart = echarts.init(document.getElementById('glow_bar'));
            barChart.setOption({{
                backgroundColor: 'transparent',
                title: {{ text: '// EN BÜYÜK 7 AKTÖR SERMAYE DAĞILIMI', textStyle: {{ color: '#00f3ff', fontSize: 13, fontWeight: 'normal' }} }},
                tooltip: {{ trigger: 'axis', backgroundBackgroundColor: 'rgba(6,16,39,0.9)', borderColor: '#00f3ff' }},
                xAxis: {{ type: 'category', data: dataFirms, axisLabel: {{ color: '#7a92b5' }} }},
                yAxis: {{ type: 'value', axisLabel: {{ color: '#7a92b5' }}, splitLine: {{ lineStyle: {{ color: 'rgba(0,243,255,0.04)' }} }} }},
                series: [{{
                    data: dataSermaye,
                    type: 'bar',
                    itemStyle: {{
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            {{ offset: 0, color: '#00f3ff' }},
                            {{ offset: 1, color: '#0033ff' }}
                        ]),
                        borderRadius: [3, 3, 0, 0]
                    }}
                }}]
            }});

            // --- 2. FÜTÜRİSTİK HALO PASTA GRAFİĞİ ---
            const pieChart = echarts.init(document.getElementById('glow_pie'));
            pieChart.setOption({{
                backgroundColor: 'transparent',
                title: {{ text: '// SEKTÖREL LOG MATRİS ORANLARI', textStyle: {{ color: '#ff00ff', fontSize: 13, fontWeight: 'normal' }} }},
                tooltip: {{ trigger: 'item' }},
                series: [{{
                    type: 'pie',
                    radius: ['45%', '70%'],
                    itemStyle: {{ borderRadius: 5, borderColor: '#040b1c', borderWidth: 2 }},
                    label: {{ color: '#7a92b5', fontSize: 11 }},
                    data: dataPie,
                    color: ['#00f3ff', '#ff00ff', '#00ff66', '#ffaa00', '#9900ff', '#ff0055']
                }}]
            }});

            // --- 3. DALGALI SPEKTRUM TREND GRAFİĞİ ---
            const lineChart = echarts.init(document.getElementById('glow_line'));
            lineChart.setOption({{
                backgroundColor: 'transparent',
                title: {{ text: '// PERİYODİK HIZ HARİTASI AKIŞKANLIĞI', textStyle: {{ color: '#00ff66', fontSize: 13, fontWeight: 'normal' }} }},
                tooltip: {{ trigger: 'axis' }},
                xAxis: {{ type: 'category', data: dataMonths, axisLabel: {{ color: '#7a92b5' }}, boundaryGap: false }},
                yAxis: {{ type: 'value', axisLabel: {{ color: '#7a92b5' }}, splitLine: {{ lineStyle: {{ color: 'rgba(0,255,102,0.04)' }} }} }},
                series: [{{
                    data: dataLine,
                    type: 'line',
                    smooth: true,
                    symbol: 'circle',
                    symbolSize: 6,
                    lineStyle: {{ color: '#00ff66', width: 2.5 }},
                    itemStyle: {{ color: '#ffffff', borderColor: '#00ff66' }},
                    areaStyle: {{
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            {{ offset: 0, color: 'rgba(0,255,102,0.2)' }},
                            {{ offset: 1, color: 'rgba(0,255,102,0.0)' }}
                        ])
                    }}
                }}]
            }});

            // GPU Optimizasyonu & Ekran Boyut Adaptörü
            window.addEventListener('resize', function() {{
                barChart.resize();
                pieChart.resize();
                lineChart.resize();
            }});
        </script>
    </body>
    </html>
    """

    # HTML5/WebGL Yapısını Ekrana Basıyoruz
    st.components.v1.html(war_room_html, height=730, scrolling=False)