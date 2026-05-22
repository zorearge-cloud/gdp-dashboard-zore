import streamlit as st
import pandas as pd
import requests
import io
import openpyxl
import datetime
import json
import re

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

if logs:
    with st.sidebar.expander("🛠️ Sistem Terminal Çıktıları"):
        for log in logs: st.caption(log)

if df_raw.empty:
    st.error("🚨 SİBER VERİ MATRİSİ ALINAMADI. Bağlantıları kontrol edin.")
else:
    # Dönemsel Zaman Eğrisini Çıkarma
    if 'SIPARIS_TARIHI' in df_raw.columns:
        df_raw['AY'] = df_raw['SIPARIS_TARIHI'].str[:7]
    else:
        df_raw['AY'] = "2026-01"
        
    df_2026 = df_raw[df_raw['AY'].str.startswith('2026', na=False)].copy()
    if df_2026.empty:
        df_2026 = df_raw.copy()

    # Kronolojik olarak ayları sırala
    months_sequence = sorted(df_2026['AY'].unique())
    
    # JavaScript Matrix Veri Köprüsü Hazırlığı
    timeline_matrix = {}
    
    for month in months_sequence:
        df_m = df_2026[df_2026['AY'] == month]
        
        # 1. Yatay Bar Yarışı için Firma Sıralaması (Büyükten Küçüğe ECharts Map için tersten dizilir)
        if 'FIRMA' in df_m.columns:
            top_firms = df_m.groupby('FIRMA')['TOPLAM_SERMAYE'].sum().nlargest(10).reset_index()
            top_firms = top_firms.iloc[::-1]  # Görsel akış için ters çevrilir
            firms_list = top_firms['FIRMA'].tolist()
            sermaye_list = top_firms['TOPLAM_SERMAYE'].round(2).tolist()
        else:
            firms_list, sermaye_list = ["Firma Verisi Yok"], [0]
            
        # 2. Tür Dağılım Matrisi (Donut Matrisi Verisi)
        if 'TUR' in df_m.columns:
            top_cats = df_m.groupby('TUR')['ADET'].sum().nlargest(8).reset_index()
            pie_data = [{"value": int(row['ADET']), "name": str(row['TUR'])} for _, row in top_cats.iterrows()]
        else:
            pie_data = [{"value": 0, "name": "Tür Yok"}]
            
        timeline_matrix[month] = {
            "firms": firms_list,
            "sermaye": sermaye_list,
            "pie": pie_data
        }

    # --- CANVAS & WEBGL SAVAŞ ODASI MATRİS ARAYÜZÜ (HTML5 / ECHARTS) ---
    cinematic_loop_html = f"""
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
            .matrix-header {{
                margin-bottom: 15px;
                border-bottom: 1px dashed rgba(0,243,255,0.15); 
                padding-bottom: 10px;
            }}
            .matrix-title {{
                margin: 0;
                font-size: 16px; 
                color: #ffffff; 
                letter-spacing: 1px;
                font-weight: 600;
            }}
            .matrix-subtitle {{
                margin: 5px 0 0 0;
                font-size: 12px; 
                color: #00f3ff; 
                font-weight: 600;
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
                height: 520px;
                box-shadow: 0 4px 30px rgba(0, 0, 0, 0.4);
            }}
        </style>
    </head>
    <body>

        <div class="matrix-header">
            <h2 class="matrix-title">🎬 Canlı Sinematik Döngü Koridoru (Otomatik Film Modu)</h2>
            <p class="matrix-subtitle">
                DÖNEM: <span id="active-period" style="color: #ffaa00; background: rgba(255,170,0,0.15); padding: 2px 8px; border-radius: 4px; font-family: monospace;">---- --</span> 
                <span style="color: #00ff66; margin-left: 10px;">[ 🟢 Sistem SÜREKLİ DÖNGÜDE - FİLM MODU AKTİF ]</span>
            </p>
        </div>

        <div class="grid-layout">
            <div id="glow_bar_race" class="panel-box"></div>
            <div id="glow_pie_radar" class="panel-box"></div>
        </div>

        <script>
            // Veri Altyapısının Enjeksiyonu
            const timelineMatrix = {json.dumps(timeline_matrix)};
            const monthsSequence = {json.dumps(months_sequence)};
            
            let currentIndex = 0;

            // --- 1. SİBER YATAY BAR YARIŞI ---
            const barChart = echarts.init(document.getElementById('glow_bar_race'));
            const barOption = {{
                backgroundColor: 'transparent',
                title: {{ text: '3. Firmaların Aylık Birikimli Güç Yarışı (Sinematik Akış)', textStyle: {{ color: '#00f3ff', fontSize: 13, fontWeight: 'normal' }} }},
                tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
                grid: {{ left: '15%', right: '8%', top: '12%', bottom: '8%' }},
                xAxis: {{ type: 'value', axisLabel: {{ color: '#7a92b5' }}, splitLine: {{ lineStyle: {{ color: 'rgba(0,243,255,0.04)' }} }} }},
                yAxis: {{ type: 'category', data: [], axisLabel: {{ color: '#7a92b5', fontSize: 11 }} }},
                series: [{{
                    type: 'bar',
                    data: [],
                    itemStyle: {{
                        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                            {{ offset: 0, color: '#0033ff' }},
                            {{ offset: 1, color: '#00f3ff' }}
                        ]),
                        borderRadius: [0, 4, 4, 0]
                    }},
                    label: {{ show: true, position: 'right', color: '#ffffff', formatter: '{{c}} $' }}
                }}]
            }};
            barChart.setOption(barOption);

            // --- 2. FÜTÜRİSTİK HALO PASTA GRAFİĞİ (ZORE RADAR CENTER) ---
            const pieChart = echarts.init(document.getElementById('glow_pie_radar'));
            const pieOption = {{
                backgroundColor: 'transparent',
                title: [
                    {{
                        text: '4. Toplam Dönem Genel Tür Dağılım Matrisi',
                        textStyle: {{ color: '#ff00ff', fontSize: 13, fontWeight: 'normal' }},
                        left: 'left',
                        top: 'top'
                    }},
                    {{
                        text: 'ZORE\\nRADAR',
                        left: 'center',
                        top: '48%',
                        textStyle: {{ color: '#00f3ff', fontSize: 12, fontWeight: '800', align: 'center', fontFamily: 'monospace', lineHeight: 16 }}
                    }}
                ],
                tooltip: {{ trigger: 'item', formatter: '{{b}}: {{c}} Adet ({{d}}%)' }},
                series: [{{
                    type: 'pie',
                    radius: ['42%', '68%'],
                    center: ['50%', '52%'],
                    itemStyle: {{ borderRadius: 5, borderColor: '#040b1c', borderWidth: 2 }},
                    label: {{ color: '#7a92b5', fontSize: 11, formatter: '{{b}}\\n{{d}}%' }},
                    data: [],
                    color: ['#00f3ff', '#ff00ff', '#00ff66', '#ffaa00', '#9900ff', '#ff0055', '#00cccc', '#cc00cc']
                }}]
            }};
            pieChart.setOption(pieOption);

            // --- SİNEMATİK DÖNGÜ VE GEÇİŞ MOTORU ---
            function runCinematicFrame() {{
                if (monthsSequence.length === 0) return;
                const activeMonth = monthsSequence[currentIndex];
                const currentData = timelineMatrix[activeMonth];

                // Başlık Panel Güncellemesi
                document.getElementById('active-period').innerText = activeMonth;
                
                // Grafik Veri Enjeksiyonları
                barChart.setOption({{
                    yAxis: {{ data: currentData.firms }},
                    series: [{{ data: currentData.sermaye }}]
                }});
                
                pieChart.setOption({{
                    series: [{{ data: currentData.pie }}]
                }});
                
                // Endeksi İlerlet (Döngü Başa Saracak Şekilde)
                currentIndex = (currentIndex + 1) % monthsSequence.length;
            }}

            // 2.5 Saniyede Bir Yumuşak Dönüşüm Akışı
            setInterval(runCinematicFrame, 2500);
            runCinematicFrame(); // İlk kareyi anında tetikle

            // Ekran Boyut Adaptörü
            window.addEventListener('resize', function() {{
                barChart.resize();
                pieChart.resize();
            }});
        </script>
    </body>
    </html>
    """

    # Gelişmiş HTML WebGL Yapısını Ekrana Basıyoruz
    st.components.v1.html(cinematic_loop_html, height=590, scrolling=False)