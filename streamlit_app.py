import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import io
import openpyxl
import re
import datetime
import json

# --- AYARLAR VE ANAYASA (TAM KAPSAMLI YAPI) ---
st.set_page_config(layout="wide", page_title="ZORE Veri Paneli")

# Arka planı koyu neon temaya sabitleyen global CSS enjeksiyonu
st.markdown("""
<style>
    .reportview-container { background: #060913 !important; }
    .stDeployButton { display:none !important; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    div.block-container { padding-top: 1rem; padding-bottom: 0rem; padding-left: 1.5rem; padding-right: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# 1. KURAL: Veri çekme bağlantıları ve tab yapıları korunacak
LINKS = [
    "https://docs.google.com/spreadsheets/d/1j819WkX93CkCy3VgZkSff5C_zNX5Z98jfK-FwI4ZWUU/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1hVk6VgMFXWAukoQwMDIoOLrG8SD4UDLFFRH9VmDhXSE/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1S1kTptWUEf705cBLw9P9mL6rrqbVjbcp1xk_hgQ-Ny0/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1VKb6za4Fse5XrGawPG6qvrQZuFhDRGaAysmADGIC7Wc/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=xlsx"
]

TARGET_TABS = ["has_air", "has_sea", "meh_air", "meh_sea", "ist_air", "ist_sea"]
EXPECTED_COLUMNS = ['SIPARIS_TARIHI', 'FIRMA', 'TUR', 'BARKOD', 'MALIN CINSI', 'ADET', 'FIYAT', 'YUKLEME_TARIHI', 'NAKLİYE_TÜRÜ']

HEADER_MAP = {
    'SIPARIS TARIHI': 'SIPARIS_TARIHI', 'SIPARIS_TARIHI': 'SIPARIS_TARIHI',
    'FIRMA': 'FIRMA', 'TUR': 'TUR', 'BARKOD': 'BARKOD',
    'MALIN CINSI': 'MALIN CINSI', 'ADET': 'ADET', 'FIYAT': 'FIYAT',
    'YUKLEME TARIHI': 'YUKLEME_TARIHI', 'YUKLEME_TARIHI': 'YUKLEME_TARIHI'
}

# --- CANLI DÖVİZ KURU MOTORU ---
@st.cache_data(ttl=3600)
def get_live_rates():
    rates = {"EUR_TO_USD": 1.09, "CNY_TO_USD": 0.138, "PROUNCE": "Yedek Kur Panelden Okundu"}
    try:
        response = requests.get("https://open.er-api.com/v6/latest/USD", timeout=4)
        if response.status_code == 200:
            data = response.json()
            usd_rates = data.get("rates", {})
            eur_rate = usd_rates.get("EUR")
            cny_rate = usd_rates.get("CNY")
            if eur_rate and cny_rate:
                rates["EUR_TO_USD"] = 1.0 / eur_rate
                rates["CNY_TO_USD"] = 1.0 / cny_rate
                rates["PROUNCE"] = "Canlı Kur API'den Çekildi"
    except:
        pass
    return rates

rates = get_live_rates()

# --- GELİŞMİŞ TARİH STANDARTLAŞTIRMA MOTORU ---
def strict_date_string_parser(val):
    if pd.isna(val) or val == "":
        return "BELİRTİLMEMİŞ"
    if hasattr(val, 'strftime'):
        return val.strftime('%Y-%m-%d')
    val_str = str(val).strip()
    if " " in val_str:
        val_str = val_str.split()[0]
    val_str = val_str.replace('/', '.').replace('-', '.')
    for fmt in ['%Y.%m.%d', '%d.%m.%Y', '%Y.%d.%m']:
        try:
            dt = datetime.datetime.strptime(val_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except:
            continue
    try:
        dt = pd.to_datetime(val_str, dayfirst=True, errors='coerce')
        if not pd.isna(dt):
            return dt.strftime('%Y-%m-%d')
    except:
        pass
    return "BELİRTİLMEMİŞ"

# --- VERİ TEMİZLEME VE DÖNÜŞTÜRME MOTORU ---
def clean_data(df, rates):
    df = df.loc[:, ~df.columns.duplicated()]
    for col in ['SIPARIS_TARIHI', 'YUKLEME_TARIHI']:
        if col in df.columns:
            df[col] = df[col].apply(strict_date_string_parser)
            
    available_cols = [c for c in EXPECTED_COLUMNS if c in df.columns]
    df = df[available_cols].copy()
    df = df.dropna(how='all')
    
    if 'ADET' in df.columns:
        df['ADET'] = pd.to_numeric(df['ADET'], errors='coerce').fillna(0)
    
    if 'FIYAT' in df.columns and 'FIRMA' in df.columns:
        def parse_price_details(row):
            val = row['FIYAT']
            firma_name = str(row['FIRMA']).upper().strip()
            if pd.isna(val):
                return 0.0, 0.0, '$'
            
            val_str = str(val).strip()
            currency = 'USD'
            sym_char = '$'
            
            yuan_symbols = ['¥', '￥', 'CNY', 'RMB', '元', 'CHINESE']
            euro_symbols = ['€', 'EUR', 'EURO']
            
            if 'CATHY' in firma_name or 'AECOOLY' in firma_name or any(sym in val_str for sym in yuan_symbols) or any(sym in val_str.upper() for sym in yuan_symbols):
                currency = 'CNY'
                sym_char = '¥'
            elif any(sym in val_str for sym in euro_symbols) or any(sym in val_str.upper() for sym in euro_symbols):
                currency = 'EUR'
                sym_char = '€'
            
            for clean_target in yuan_symbols + euro_symbols + ['$', 'usd', 'USD']:
                val_str = val_str.replace(clean_target, '')
            val_str = val_str.strip()
            
            if ',' in val_str and '.' in val_str:
                if val_str.find(',') > val_str.find('.'):
                    val_str = val_str.replace('.', '').replace(',', '.')
                else:
                    val_str = val_str.replace(',', '')
            elif ',' in val_str:
                val_str = val_str.replace(',', '.')
                
            try: numeric_price = float(val_str)
            except: numeric_price = 0.0
                
            if currency == 'CNY': usd_price = numeric_price * rates["CNY_TO_USD"]
            elif currency == 'EUR': usd_price = numeric_price * rates["EUR_TO_USD"]
            else: usd_price = numeric_price
                
            return usd_price, numeric_price, sym_char

        res = df.apply(parse_price_details, axis=1)
        df['FIYAT'] = [r[0] for r in res]
        df['ORIJINAL_FIYAT'] = [r[1] for r in res]
        df['PARA_BIRIMI'] = [r[2] for r in res]
    else:
        df['ORIJINAL_FIYAT'] = df['FIYAT'] if 'FIYAT' in df.columns else 0.0
        df['PARA_BIRIMI'] = '$'
    
    df['TOPLAM_SERMAYE'] = df['ADET'] * df['FIYAT']
    
    for text_col in ['FIRMA', 'TUR', 'MALIN CINSI', 'BARKOD', 'NAKLİYE_TÜRÜ']:
        if text_col in df.columns:
            if text_col == 'BARKOD':
                def strict_barcode_clean(x):
                    if pd.isna(x): return "BELİRTİLMEMİŞ"
                    if isinstance(x, (int, float)):
                        try:
                            if x == int(x): return str(int(x))
                            return str(x)
                        except: return str(x)
                    s = str(x).strip()
                    if s.endswith('.0'): s = s[:-2]
                    if '.' in s:
                        try:
                            f = float(s)
                            if f == int(f): return str(int(f))
                        except: pass
                    if s in ['nan', 'None', '']: return "BELİRTİLMEMİŞ"
                    return s
                df['BARKOD'] = df['BARKOD'].apply(strict_barcode_clean)
            else:
                val_series = df[text_col].fillna("BELİRTİLMEMİŞ").astype(str).str.strip()
                df[text_col] = val_series.replace({'nan': 'BELİRTİLMEMİŞ', 'None': 'BELİRTİLMEMİŞ', '': 'BELİRTİLMEMİŞ'})
            
    return df

# --- COKLU DOSYA VE LINK YÖNETİM MOTORU ---
@st.cache_data(ttl=600)
def get_all_data(rates):
    all_data_list = []
    pool = {tab: [] for tab in TARGET_TABS}
    
    for link in LINKS:
        try:
            response = requests.get(link, timeout=10)
            if response.status_code != 200: continue
            
            wb = openpyxl.load_workbook(io.BytesIO(response.content), data_only=True)
            for tab in TARGET_TABS:
                if tab in wb.sheetnames:
                    sheet = wb[tab]
                    rows = list(sheet.iter_rows(values_only=False))
                    if not rows: continue
                    
                    raw_headers = [str(cell.value).strip().upper() if cell.value is not None else '' for cell in rows[0]]
                    headers = []
                    for h in raw_headers:
                        clean_h = h.replace('İ', 'I').replace('Ş', 'S').replace('Ü', 'U').replace('Ç', 'C').replace('Ğ', 'G').replace('_', ' ')
                        headers.append(HEADER_MAP.get(clean_h, h))
                    
                    try: fiyat_idx = headers.index('FIYAT')
                    except ValueError: fiyat_idx = -1
                        
                    data = []
                    for row in rows[1:]:
                        if all(cell.value is None for cell in row): continue
                        row_data = []
                        for idx, cell in enumerate(row):
                            if idx >= len(headers): break
                            val = cell.value
                            if idx == fiyat_idx and val is not None:
                                fmt = str(cell.number_format).upper()
                                if any(x in fmt for x in ['¥', '￥', 'CNY', '元', '804', '2052', 'E01']): val = f"¥{val}"
                                elif any(x in fmt for x in ['€', 'EUR', '40C']): val = f"€{val}"
                            row_data.append(val)
                            
                        while len(row_data) < len(headers): row_data.append(None)
                        data.append(row_data)
                        
                    df = pd.DataFrame(data, columns=headers)
                    tab_lower = tab.lower()
                    prefix = ""
                    if "has" in tab_lower: prefix = "HAS "
                    elif "meh" in tab_lower: prefix = "MEH "
                    elif "ist" in tab_lower: prefix = "IST "
                        
                    if "air" in tab_lower: df['NAKLİYE_TÜRÜ'] = prefix + "HAVA"
                    elif "sea" in tab_lower: df['NAKLİYE_TÜRÜ'] = prefix + "DENİZ"
                    else: df['NAKLİYE_TÜRÜ'] = prefix + "BELİRTİLMEMİŞ"
                        
                    df_clean = clean_data(df, rates)
                    if not df_clean.empty:
                        pool[tab].append(df_clean)
                        all_data_list.append(df_clean)
        except:
            continue
    
    full_df = pd.concat(all_data_list, ignore_index=True) if all_data_list else pd.DataFrame()
    if not full_df.empty:
        def get_clean_period(x):
            if x == "BELİRTİLMEMİŞ" or len(x) < 7: return "Bilinmeyen Dönem"
            return x[:7]
        full_df['SIPARIS_AY'] = full_df['SIPARIS_TARIHI'].apply(get_clean_period)
        
    return full_df, pool

df_dashboard, data_pool = get_all_data(rates)

# --- NAVİGASYON VE SIDEBAR YÖNETİMİ ---
st.sidebar.title("ZORE YÖNETİM PANELİ")
st.sidebar.markdown(f"**Döviz Durumu:** `{rates['PROUNCE']}`")
st.sidebar.text(f"1 EUR = {rates['EUR_TO_USD']:.4f} $")
st.sidebar.text(f"1 CNY = {rates['CNY_TO_USD']:.4f} $")
st.sidebar.markdown("---")

page = st.sidebar.radio("Sayfa Seçimi", ["1. Genel Dashboard", "2. Firma Bazlı Analiz", "3. Ham Veri"])

# --- SAYFA 1: GENEL DASHBOARD (ASİL NEON VE KURUMSAL İSİMLERLE YENİDEN TASARLANDI) ---
if page == "1. Genel Dashboard":
    st.header("📊 Genel Dashboard")
    
    if df_dashboard.empty:
        st.error("Veri havuzunda işlenecek kayıt bulunamadı.")
    else:
        # Metriklerin Hazırlığı
        total_adet = int(df_dashboard['ADET'].sum())
        total_sermaye = float(df_dashboard['TOPLAM_SERMAYE'].sum())
        active_firms = int(df_dashboard['FIRMA'].nunique())

        # Grafik Verilerinin Hazırlığı (ECharts Formatına Eşleme)
        # 1. En Çok Sipariş Edilen Ürünler (Bar)
        top_sips = df_dashboard.groupby('MALIN CINSI')['ADET'].sum().nlargest(8).reset_index()
        sips_names = top_sips['MALIN CINSI'].tolist()
        sips_values = top_sips['ADET'].tolist()

        # 2. En Çok Sermaye Yatırılan Ürünler (Bar)
        top_money = df_dashboard.groupby('MALIN CINSI')['TOPLAM_SERMAYE'].sum().nlargest(8).reset_index()
        money_names = top_money['MALIN CINSI'].tolist()
        money_values = top_money['TOPLAM_SERMAYE'].round(2).tolist()

        # 3. Harcama Yapılan İlk Firmalar (Pie/Donut)
        top_firma = df_dashboard.groupby('FIRMA')['TOPLAM_SERMAYE'].sum().nlargest(6).reset_index()
        firma_pie_data = [{"value": round(row['TOPLAM_SERMAYE'], 2), "name": str(row['FIRMA'])} for _, row in top_firma.iterrows()]

        # 4. Tür Bazlı Harcama Dağılımı (Pie/Donut)
        top_tur = df_dashboard.groupby('TUR')['TOPLAM_SERMAYE'].sum().nlargest(6).reset_index()
        tur_pie_data = [{"value": round(row['TOPLAM_SERMAYE'], 2), "name": str(row['TUR'])} for _, row in top_tur.iterrows()]

        # 5. Dönemsel Toplam Sermaye Akışı Trendi (2026 Filtreli Akışkan Line)
        df_2026 = df_dashboard[df_dashboard['SIPARIS_AY'].str.startswith('2026', na=False)].copy().sort_values('SIPARIS_AY')
        if df_2026.empty:
            df_2026 = df_dashboard.copy().sort_values('SIPARIS_AY')
        trend_total = df_2026.groupby('SIPARIS_AY')['TOPLAM_SERMAYE'].sum().reset_index()
        trend_months = trend_total['SIPARIS_AY'].tolist()
        trend_values = trend_total['TOPLAM_SERMAYE'].round(2).tolist()

        # Resimdeki Gelişmiş Tasarımı Birebir Sağlayan Enjekte HTML/JS Bloğu
        neon_matrix_html = f"""
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
                }}
                .header-matrix {{
                    display: flex;
                    justify-content: space-between;
                    gap: 20px;
                    margin-bottom: 25px;
                }}
                .matrix-card {{
                    flex: 1;
                    background: linear-gradient(135deg, rgba(6, 16, 39, 0.9) 0%, rgba(3, 8, 22, 0.95) 100%);
                    border: 1px solid rgba(0, 243, 255, 0.25);
                    border-radius: 8px;
                    padding: 16px;
                    text-align: center;
                    position: relative;
                    box-shadow: 0 0 15px rgba(0, 243, 255, 0.05);
                }}
                .card-title {{
                    font-size: 11px;
                    letter-spacing: 1.5px;
                    color: #5f7595;
                    margin: 0 0 6px 0;
                    font-weight: 600;
                }}
                .card-value {{
                    font-size: 30px;
                    font-weight: 800;
                    color: #ffffff;
                    margin: 0;
                    text-shadow: 0 0 12px rgba(0, 243, 255, 0.35);
                }}
                .grid-layout {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 20px;
                    margin-bottom: 20px;
                }}
                .panel-box {{
                    background: rgba(4, 11, 28, 0.65);
                    border: 1px solid rgba(0, 243, 255, 0.12);
                    border-radius: 8px;
                    padding: 15px;
                    height: 330px;
                }}
                .full-panel {{
                    grid-column: span 2;
                    height: 280px;
                }}
            </style>
        </head>
        <body>

            <div class="header-matrix">
                <div class="matrix-card" style="border-color: rgba(0, 243, 255, 0.45);">
                    <p class="card-title">📦 TOPLAM SİPARİŞ ADETİ</p>
                    <p class="card-value" style="color: #00f3ff;">{total_adet:,} <span style="font-size:14px; color:#5f7595;">Adet</span></p>
                </div>
                <div class="matrix-card" style="border-color: rgba(255, 0, 255, 0.45);">
                    <p class="card-title">💰 TOPLAM SERMAYE YATIRIMI (USD)</p>
                    <p class="card-value" style="color: #ff00ff;">{total_sermaye:,.2f} <span style="font-size:14px; color:#5f7595;">$</span></p>
                </div>
                <div class="matrix-card" style="border-color: rgba(0, 255, 102, 0.45);">
                    <p class="card-title">🏢 ÇALIŞILAN FİRMA SAYISI</p>
                    <p class="card-value" style="color: #00ff66;">{active_firms} <span style="font-size:14px; color:#5f7595;">Firma</span></p>
                </div>
            </div>

            <div class="grid-layout">
                <div id="chart_sips" class="panel-box"></div>
                <div id="chart_money" class="panel-box"></div>
                <div id="chart_firma" class="panel-box"></div>
                <div id="chart_tur" class="panel-box"></div>
                <div id="chart_trend" class="panel-box full-panel"></div>
            </div>

            <script>
                // Python Veri Paketlerinin Alınması
                const sipsNames = {json.dumps(sips_names)};
                const sipsValues = {json.dumps(sips_values)};
                const moneyNames = {json.dumps(money_names)};
                const moneyValues = {json.dumps(money_values)};
                const dataFirma = {json.dumps(firma_pie_data)};
                const dataTur = {json.dumps(tur_pie_data)};
                const trendMonths = {json.dumps(trend_months)};
                const trendValues = {json.dumps(trend_values)};

                // Ortak Grafik Ayar Şablonu
                const textStyleConfig = {{ color: '#7a92b5', fontSize: 11 }};
                
                // --- 1. EN ÇOK SİPARİŞ EDİLEN ÜRÜNLER (BAR) ---
                const cSips = echarts.init(document.getElementById('chart_sips'));
                cSips.setOption({{
                    backgroundColor: 'transparent',
                    title: {{ text: '// En Çok Sipariş Edilen Ürünler (Adet)', textStyle: {{ color: '#00f3ff', fontSize: 13, fontWeight: '500' }} }},
                    tooltip: {{ trigger: 'axis', backgroundColor: 'rgba(6,16,39,0.95)', borderColor: '#00f3ff' }},
                    grid: {{ left: '4%', right: '4%', bottom: '15%', containLabel: true }},
                    xAxis: {{ type: 'category', data: sipsNames, axisLabel: {{ color: '#7a92b5', interval: 0, rotate: 20, fontSize: 10 }} }},
                    yAxis: {{ type: 'value', axisLabel: textStyleConfig, splitLine: {{ lineStyle: {{ color: 'rgba(0,243,255,0.05)' }} }} }},
                    series: [{{
                        data: sipsValues,
                        type: 'bar',
                        itemStyle: {{
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                {{ offset: 0, color: '#00f3ff' }},
                                {{ offset: 1, color: '#0033ff' }}
                            ]),
                            borderRadius: [4, 4, 0, 0]
                        }}
                    }}]
                }});

                // --- 2. EN ÇOK SERMAYE YATIRILAN ÜRÜNLER (BAR) ---
                const cMoney = echarts.init(document.getElementById('chart_chart_money'));
                const targetMoneyDOM = document.getElementById('chart_money');
                const cMoneyReal = echarts.init(targetMoneyDOM);
                cMoneyReal.setOption({{
                    backgroundColor: 'transparent',
                    title: {{ text: '// En Çok Sermaye Yatırılan Ürünler ($)', textStyle: {{ color: '#ff00ff', fontSize: 13, fontWeight: '500' }} }},
                    tooltip: {{ trigger: 'axis', backgroundColor: 'rgba(6,16,39,0.95)', borderColor: '#ff00ff' }},
                    grid: {{ left: '4%', right: '4%', bottom: '15%', containLabel: true }},
                    xAxis: {{ type: 'category', data: moneyNames, axisLabel: {{ color: '#7a92b5', interval: 0, rotate: 20, fontSize: 10 }} }},
                    yAxis: {{ type: 'value', axisLabel: textStyleConfig, splitLine: {{ lineStyle: {{ color: 'rgba(255,0,255,0.05)' }} }} }},
                    series: [{{
                        data: moneyValues,
                        type: 'bar',
                        itemStyle: {{
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                {{ offset: 0, color: '#ff00ff' }},
                                {{ offset: 1, color: '#660066' }}
                            ]),
                            borderRadius: [4, 4, 0, 0]
                        }}
                    }}]
                }});

                // --- 3. HARCAMA YAPILAN İLK FİRMALAR (DONUT) ---
                const cFirma = echarts.init(document.getElementById('chart_firma'));
                cFirma.setOption({{
                    backgroundColor: 'transparent',
                    title: {{ text: '// Harcama Yapılan İlk Firmalar', textStyle: {{ color: '#00ff66', fontSize: 13, fontWeight: '500' }} }},
                    tooltip: {{ trigger: 'item' }},
                    series: [{{
                        type: 'pie',
                        radius: ['42%', '68%'],
                        avoidLabelOverlap: true,
                        itemStyle: {{ borderRadius: 6, borderColor: '#040b1c', borderWidth: 2 }},
                        label: {{ color: '#7a92b5', fontSize: 10, formatter: '{{b}}\\n({{d}}%)' }},
                        data: dataFirma,
                        color: ['#00f3ff', '#ff00ff', '#00ff66', '#ffaa00', '#9900ff', '#ff0055']
                    }}]
                }});

                // --- 4. TÜR BAZLI HARCAMA DAĞILIMI (DONUT) ---
                const cTur = echarts.init(document.getElementById('chart_tur'));
                cTur.setOption({{
                    backgroundColor: 'transparent',
                    title: {{ text: '// Tür Bazlı Harcama Dağılımı (USD)', textStyle: {{ color: '#ffaa00', fontSize: 13, fontWeight: '500' }} }},
                    tooltip: {{ trigger: 'item' }},
                    series: [{{
                        type: 'pie',
                        radius: ['42%', '68%'],
                        avoidLabelOverlap: true,
                        itemStyle: {{ borderRadius: 6, borderColor: '#040b1c', borderWidth: 2 }},
                        label: {{ color: '#7a92b5', fontSize: 10, formatter: '{{b}}\\n({{d}}%)' }},
                        data: dataTur,
                        color: ['#ffaa00', '#00f3ff', '#ff00ff', '#00ff66', '#9900ff', '#dd2222']
                    }}]
                }});

                // --- 5. DÖNEMSEL TOPLAM SERMAYE AKIŞI TRENDİ (AKIŞKAN AREA LINE) ---
                const cTrend = echarts.init(document.getElementById('chart_trend'));
                cTrend.setOption({{
                    backgroundColor: 'transparent',
                    title: {{ text: '// Dönemsel Sermaye Akış Trendi', textStyle: {{ color: '#00f3ff', fontSize: 13, fontWeight: '500' }} }},
                    tooltip: {{ trigger: 'axis', backgroundColor: 'rgba(6,16,39,0.95)' }},
                    grid: {{ left: '3%', right: '3%', bottom: '10%', containLabel: true }},
                    xAxis: {{ type: 'category', data: trendMonths, axisLabel: textStyleConfig, boundaryGap: false }},
                    yAxis: {{ type: 'value', axisLabel: textStyleConfig, splitLine: {{ lineStyle: {{ color: 'rgba(0,243,255,0.04)' }} }} }},
                    series: [{{
                        data: trendValues,
                        type: 'line',
                        smooth: true,
                        symbol: 'circle',
                        symbolSize: 6,
                        lineStyle: {{ color: '#00f3ff', width: 3 }},
                        itemStyle: {{ color: '#ffffff', borderColor: '#00f3ff', borderWidth: 2 }},
                        areaStyle: {{
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                {{ offset: 0, color: 'rgba(0,243,255,0.28)' }},
                                {{ offset: 1, color: 'rgba(0,243,255,0.0)' }}
                            ])
                        }}
                    }}]
                }});

                // Responsive Ekran Boyutlandırması
                window.addEventListener('resize', function() {{
                    cSips.resize();
                    cMoneyReal.resize();
                    cFirma.resize();
                    cTur.resize();
                    cTrend.resize();
                }});
            </script>
        </body>
        </html>
        """
        st.components.v1.html(neon_matrix_html, height=1050, scrolling=False)

# --- SAYFA 2: FİRMA BAZLI ANALİZ (DOKUNULMADI - %100 KORUNDU) ---
elif page == "2. Firma Bazlı Analiz":
    st.header("🏢 Firma Bazlı Analiz")
    
    if df_dashboard.empty:
        st.error("Veri havuzu boş.")
    else:
        firmalar = sorted([str(f) for f in df_dashboard['FIRMA'].unique() if str(f) != "BELİRTİLMEMİŞ"])
        
        if not firmalar:
            st.warning("Analiz edilecek geçerli bir firma kaydı bulunamadı.")
        else:
            selected_firma = st.selectbox("Analiz edilecek firmayı seçin", firmalar)
            firma_df = df_dashboard[df_dashboard['FIRMA'] == selected_firma]
            
            c1, c2, c3 = st.columns(3)
            c1.metric(f"{selected_firma} Toplam Alım (Adet)", f"{int(firma_df['ADET'].sum()):,}")
            c2.metric(f"{selected_firma} Toplam Ciro (USD)", f"{firma_df['TOPLAM_SERMAYE'].sum():,.2f} $")
            
            tur_counts = firma_df.groupby('TUR')['ADET'].sum()
            en_cok_tur = tur_counts.idxmax() if not tur_counts.empty and tur_counts.sum() > 0 else "Veri Yok"
            c3.metric("En Çok Aldığı Tür", en_cok_tur)
            
            col_a, col_b = st.columns(2)
            
            if not firma_df.empty and firma_df['TOPLAM_SERMAYE'].sum() > 0:
                kategori_ozet = firma_df.groupby('TUR')['TOPLAM_SERMAYE'].sum().reset_index()
                if len(kategori_ozet) > 6:
                    en_buyuk_6 = kategori_ozet.nlargest(6, 'TOPLAM_SERMAYE')['TUR'].tolist()
                    firma_df_pie = firma_df.copy()
                    firma_df_pie['TUR_GRAFIK'] = firma_df_pie['TUR'].apply(lambda x: x if x in en_buyuk_6 else 'DİĞER')
                else:
                    firma_df_pie = firma_df.copy()
                    firma_df_pie['TUR_GRAFIK'] = firma_df_pie['TUR']
                
                fig_a = px.pie(firma_df_pie, values='TOPLAM_SERMAYE', names='TUR_GRAFIK', title=f"{selected_firma} Ürün Kategorisi Dağılımı (İlk 6 + Diğer)", hole=0.4)
                fig_a.update_traces(textinfo='label+percent')
                col_a.plotly_chart(fig_a, use_container_width=True)
            else:
                col_a.info("Grafik için yeterli veri yok.")
            
            trend_data_all = firma_df.groupby('SIPARIS_AY')['TOPLAM_SERMAYE'].sum().reset_index().sort_values('SIPARIS_AY')
            if not trend_data_all.empty and trend_data_all['TOPLAM_SERMAYE'].sum() > 0:
                fig_b = px.bar(trend_data_all, x='SIPARIS_AY', y='TOPLAM_SERMAYE', title=f"{selected_firma} Dönemsel Alım Trendi ($)", color='TOPLAM_SERMAYE')
                fig_b.update_layout(xaxis_type='category')
                col_b.plotly_chart(fig_b, use_container_width=True)
            else:
                col_b.info("Zaman trendi grafik verisi bulunamadı.")
            
            st.markdown("---")
            st.subheader(f"🔍 {selected_firma} Sipariş Listesinde Barkod Sorgulama")
            
            search_barcode = st.text_input("Barkod Yazın (Varmı / Yokmu Kontrolü):", placeholder="Kontrol etmek istediğiniz barkodu buraya girin...").strip()
            
            display_df = firma_df.copy()
            if search_barcode:
                search_res = display_df[display_df['BARKOD'].str.contains(search_barcode, case=False, na=False)]
                if not search_res.empty:
                    st.success(f"✅ Barkod Bulundu! Bu firmaya ait listede aradığınız barkod ile eşleşen {len(search_res)} adet kayıt var.")
                    display_df = search_res  
                else:
                    st.error("❌ Barkod Bulunamadı! Bu firmanın ham veri listesinde yazdığınız barkod mevcut değil.")
            
            st.markdown(f"**{selected_firma} Veri Listesi:**")
            display_df_formatted = display_df.copy()
            
            display_df_formatted['FIYAT'] = display_df_formatted['FIYAT'].map('{:,.2f} $'.format)
            display_df_formatted['TOPLAM_SERMAYE'] = display_df_formatted['TOPLAM_SERMAYE'].map('{:,.2f} $'.format)
            
            drop_cols = [c for c in ['ORIJINAL_FIYAT', 'PARA_BIRIMI'] if c in display_df_formatted.columns]
            if drop_cols:
                display_df_formatted = display_df_formatted.drop(columns=drop_cols)
                
            st.dataframe(display_df_formatted.sort_values(by='SIPARIS_TARIHI', ascending=False), use_container_width=True, hide_index=True)

# --- SAYFA 3: HAM VERİ (DOKUNULMADI - %100 KORUNDU) ---
elif page == "3. Ham Veri":
    st.header("📋 Ham Veri Havuzu")
    tabs = st.tabs(TARGET_TABS)
    for i, tab_ui in enumerate(tabs):
        with tab_ui:
            tab_name = TARGET_TABS[i]
            df_list = data_pool[tab_name]
            if df_list:
                combined_df = pd.concat(df_list, ignore_index=True).drop_duplicates()
                
                raw_display = combined_df.copy()
                raw_display['FIYAT'] = raw_display['FIYAT'].map('{:,.2f} $'.format)
                raw_display['TOPLAM_SERMAYE'] = raw_display['TOPLAM_SERMAYE'].map('{:,.2f} $'.format)
                
                drop_cols = [c for c in ['ORIJINAL_FIYAT', 'PARA_BIRIMI'] if c in raw_display.columns]
                if drop_cols:
                    raw_display = raw_display.drop(columns=drop_cols)
                    
                st.dataframe(raw_display, use_container_width=True, hide_index=True)
            else:
                st.warning(f"Bu sekme ({tab_name}) için veri bulunamadı.")