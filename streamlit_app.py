import streamlit as st
import pandas as pd
import requests
import io
import openpyxl
import datetime
import json
import re

# --- AYARLAR VE ANAYASA (TAM KAPSAMLI YAPI) ---
st.set_page_config(layout="wide", page_title="ZORE Siber Veri Paneli")

# 1. KURAL: Veri çekme bağlantıları ve tab yapıları tamamen korundu
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
    'MALIN CINSI': 'MALIN CINSI', 
    'ADET': 'ADET', 'FIYAT': 'FIYAT',
    'YUKLEME TARIHI': 'YUKLEME_TARIHI', 'YUKLEME_TARIHI': 'YUKLEME_TARIHI'
}

# --- CANLI DÖVİZ KURU MOTORU (SİBER HAVUZDAN ÇEKİLİR) ---
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
                
            try:
                numeric_price = float(val_str)
            except:
                numeric_price = 0.0
                
            if currency == 'CNY':
                usd_price = numeric_price * rates["CNY_TO_USD"]
            elif currency == 'EUR':
                usd_price = numeric_price * rates["EUR_TO_USD"]
            else:
                usd_price = numeric_price
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
                        
                    try:
                        fiyat_idx = headers.index('FIYAT')
                    except ValueError:
                        fiyat_idx = -1
                        
                    data = []
                    for row in rows[1:]:
                        if all(cell.value is None for cell in row): continue
                        row_data = []
                        for idx, cell in enumerate(row):
                            if idx >= len(headers): break
                            val = cell.value
                            if idx == fiyat_idx and val is not None:
                                fmt = str(cell.number_format).upper()
                                if any(x in fmt for x in ['¥', '￥', 'CNY', '元', '804', '2052', 'E01']):
                                    val = f"¥{val}"
                                elif any(x in fmt for x in ['€', 'EUR', '40C']):
                                    val = f"€{val}"
                            row_data.append(val)
                        while len(row_data) < len(headers):
                            row_data.append(None)
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
    return full_df, pool

df_dashboard, data_pool = get_all_data(rates)

# Sütun Sıralama Düzeltmesi: YUKLEME_TARIHI sütununu en son sütun olacak şekilde taşıyoruz
if not df_dashboard.empty and 'YUKLEME_TARIHI' in df_dashboard.columns:
    cols = [c for c in df_dashboard.columns if c != 'YUKLEME_TARIHI'] + ['YUKLEME_TARIHI']
    df_dashboard = df_dashboard[cols]

# --- NAVİGASYON VE SIDEBAR YÖNETİMİ ---
st.sidebar.title("ZORE SİBER PANEL")
st.sidebar.markdown(f"**Döviz Durumu:** `{rates['PROUNCE']}`")
st.sidebar.text(f"1 EUR = {rates['EUR_TO_USD']:.4f} $")
st.sidebar.text(f"1 CNY = {rates['CNY_TO_USD']:.4f} $")
st.sidebar.markdown("---")

page = st.sidebar.radio("Sayfa Seçimi", ["1. Siber Dashboard", "2. Firma Bazlı Analiz", "3. Ham Veri"])

# --- SAYFA 1: SİBER DASHBOARD (6 GRAFİKLİ 3x2 GRID TASARIMI) ---
if page == "1. Siber Dashboard":
    st.header("📊 ZORE Sipariş Takip Kontrol Paneli")
    
    if df_dashboard.empty:
        st.error("Veri havuzunda işlenecek kayıt bulunamadı.")
    else:
        # Üst Metrik Kartları
        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Sipariş Adedi", f"{int(df_dashboard['ADET'].sum()):,}")
        c2.metric("Toplam Sermaye Yatırımı (USD)", f"{df_dashboard['TOPLAM_SERMAYE'].sum():,.2f} $")
        c3.metric("Çalışılan Firma Sayısı", df_dashboard['FIRMA'].nunique())
        st.markdown("---")
        
        # VERİ HAZIRLIĞI
        df_temp = df_dashboard.copy()
        df_temp['SIPARIS_AY'] = df_temp['SIPARIS_TARIHI'].apply(lambda x: x[:7] if x != "BELİRTİLMEMİŞ" and len(x) >= 7 else "Bilinmeyen Dönem")
        valid_df = df_temp[df_temp['SIPARIS_AY'] != "Bilinmeyen Dönem"].copy()
        months_sequence = sorted(valid_df['SIPARIS_AY'].unique().tolist())
        
        if not months_sequence:
            months_sequence = ["Genel"]
            
        timeline_matrix = {}
        for month in months_sequence:
            df_cum = df_temp[df_temp['SIPARIS_AY'] <= month]
            
            # 1. ve 2. Grafikler için İLK 10 VERİSİ
            c1_df = df_cum.groupby('MALIN CINSI')['ADET'].sum().nlargest(10).reset_index()
            c2_df = df_cum.groupby('MALIN CINSI')['TOPLAM_SERMAYE'].sum().nlargest(10).reset_index()
            
            # 3. ve 4. Grafikler için İLK 5 VERİSİ
            c3_df = df_cum.groupby('FIRMA')['TOPLAM_SERMAYE'].sum().nlargest(5).reset_index()
            c3_data = [{"value": round(row['TOPLAM_SERMAYE'],2), "name": row['FIRMA']} for _, row in c3_df.iterrows()]
            
            c4_df = df_cum.groupby('TUR')['TOPLAM_SERMAYE'].sum().nlargest(5).reset_index()
            c4_data = [{"value": round(row['TOPLAM_SERMAYE'],2), "name": row['TUR']} for _, row in c4_df.iterrows()]
            
            # --- YENİ ÇİZGİ GRAFİKLER İÇİN SON 5 AY VERİSİ ---
            current_idx = months_sequence.index(month) if month in months_sequence else 0
            start_idx = max(0, current_idx - 4)
            display_months = months_sequence[start_idx:current_idx + 1]
            
            # 5. Grafik: 5 Aylık Harcama Trendi
            df_trend = valid_df[valid_df['SIPARIS_AY'].isin(display_months)].groupby('SIPARIS_AY')['TOPLAM_SERMAYE'].sum().reset_index()
            
            # 6. Grafik: Nakliye Türü Oranı (Hava vs Deniz)
            valid_df['NORMAL_NAKLIYE'] = valid_df['NAKLİYE_TÜRÜ'].apply(lambda x: 'HAVA' if 'HAVA' in str(x).upper() else 'DENİZ' if 'DENİZ' in str(x).upper() else 'DİĞER')
            shipping_df = valid_df[valid_df['SIPARIS_AY'].isin(display_months)].groupby(['SIPARIS_AY', 'NORMAL_NAKLIYE'])['ADET'].sum().unstack(fill_value=0)
            
            timeline_matrix[month] = {
                "c1_names": c1_df['MALIN CINSI'].tolist(), "c1_vals": c1_df['ADET'].tolist(),
                "c2_names": c2_df['MALIN CINSI'].tolist(), "c2_vals": c2_df['TOPLAM_SERMAYE'].tolist(),
                "c3_data": c3_data, "c4_data": c4_data,
                "c5_months": df_trend['SIPARIS_AY'].tolist(),
                "c5_vals": df_trend['TOPLAM_SERMAYE'].tolist(),
                "c6_months": shipping_df.index.tolist(),
                "c6_air": shipping_df.get('HAVA', pd.Series([0]*len(shipping_df))).tolist(),
                "c6_sea": shipping_df.get('DENİZ', pd.Series([0]*len(shipping_df))).tolist()
            }

        # HTML VE JAVASCRIPT TEMPLATE
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
            <style>
                body { background-color: #03050a; font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; padding: 10px; overflow-x: hidden; color: #fff; }
                .header-box { text-align: center; border-bottom: 2px solid #00f3ff; box-shadow: 0 5px 25px rgba(0, 243, 255, 0.4); padding-bottom: 15px; margin-bottom: 40px; }
                .matrix-title { color: #fff; font-size: 26px; font-weight: bold; letter-spacing: 2px; margin: 0; text-shadow: 0 0 15px #00f3ff; }
                .matrix-subtitle { color: #00ff66; font-size: 15px; margin-top: 10px; font-weight: bold; letter-spacing: 1px; }
                .period-badge { color: #00f3ff; background: rgba(0, 243, 255, 0.1); padding: 4px 15px; border-radius: 4px; border: 1px solid #00f3ff; font-family: monospace; font-size: 16px; margin-left: 10px; box-shadow: 0 0 8px #00f3ff; }
                
                .grid-container { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; padding: 20px; grid-template-rows: auto auto auto; }
                
                .panel { 
                    background: rgba(2, 6, 19, 0.9);
                    border: 2px solid #00f3ff; 
                    border-radius: 12px; 
                    box-shadow: 0 0 20px rgba(0, 243, 255, 0.5), inset 0 0 15px rgba(0, 243, 255, 0.2);
                    height: 450px; 
                    padding: 20px;
                    overflow: visible;
                }
            </style>
        </head>
        <body>
            <div class="header-box">
                <h2 class="matrix-title">ZORE SİPARİŞ TAKİP KONTROL PANELİ</h2>
                <div class="matrix-subtitle">
                    SİSTEM DURUMU: <span style="color: #00ff66;">AKTİF</span> |
                    GÖSTERİLEN VERİ: <span class="period-badge">GENEL TOPLAM</span>
                </div>
            </div>
            
            <div class="grid-container">
                <div id="c3" class="panel"></div>
                <div id="c4" class="panel"></div>
                
                <div id="c1" class="panel"></div>
                <div id="c2" class="panel"></div>
                
                <div id="c5" class="panel"></div>
                <div id="c6" class="panel"></div>
            </div>

            <script>
                const timelineMatrix = __TIMELINE_MATRIX__;
                const monthsSequence = __MONTHS_SEQUENCE__;
                
                const lastMonth = monthsSequence[monthsSequence.length - 1];
                const data = timelineMatrix[lastMonth];

                const c3_data = data.c3_data;
                const c4_data = data.c4_data;

                const colorPalette = ['#00f3ff', '#ff00ff', '#00ff66', '#ffaa00', '#aa00ff', '#ff3300', '#0011ff'];

                // DİKEY SÜTUN (BAR) GRAFİĞİ FONKSİYONU (BİREBİR KORUNDU)
                function getBarOption(titleText, xData, yData, glowColor) {
                    return {
                        title: { 
                            text: titleText, 
                            textStyle: { color: '#ffffff', fontSize: 16, fontWeight: 'bold' },
                            left: 'center', top: '2%'
                        },
                        tooltip: { 
                            trigger: 'axis', 
                            backgroundColor: 'rgba(0,0,0,0.8)', 
                            textStyle: { color: '#fff' },
                            axisPointer: { type: 'shadow' }
                        },
                        grid: { left: '3%', right: '4%', bottom: '15%', top: '20%', containLabel: true },
                        xAxis: {
                            type: 'category',
                            data: xData,
                            axisLabel: { color: '#00f3ff', interval: 0, rotate: 25, fontSize: 10, width: 80, overflow: 'truncate' },
                            axisLine: { lineStyle: { color: '#00f3ff' } }
                        },
                        yAxis: {
                            type: 'value',
                            splitLine: { lineStyle: { color: 'rgba(0, 243, 255, 0.1)', type: 'dashed' } },
                            axisLabel: { color: '#00f3ff' }
                        },
                        series: [{
                            data: yData,
                            type: 'bar',
                            barWidth: '40%',
                            itemStyle: {
                                color: glowColor,
                                borderRadius: [4, 4, 0, 0],
                                shadowBlur: 15,
                                shadowColor: glowColor
                            },
                            label: {
                                show: true,
                                position: 'top',
                                color: '#fff',
                                fontWeight: 'bold',
                                textShadowBlur: 8,
                                textShadowColor: glowColor,
                                formatter: function(params) {
                                    if (params.value >= 1000) { return (params.value / 1000).toFixed(1) + 'k'; }
                                    return params.value;
                                }
                            },
                            animationDuration: 1500
                        }]
                    };
                }

                // DONUT GRAFİĞİ FONKSİYONU (BİREBİR KORUNDU - DEĞİŞTİRİLMEDİ)
                function getDonutOption(titleText, chartData) {
                    return {
                        title: { 
                            text: titleText, 
                            textStyle: { color: '#ffffff', fontSize: 16, fontWeight: 'bold' },
                            left: 'center', top: '2%'
                        },
                        tooltip: { trigger: 'item', backgroundColor: 'rgba(0,0,0,0.8)', textStyle: { color: '#fff' } },
                        color: colorPalette,
                        series: [
                            {
                                type: 'pie',
                                radius: ['45%', '70%'],
                                center: ['50%', '55%'],
                                itemStyle: {
                                    borderRadius: 4, 
                                    borderColor: '#03050a', 
                                    borderWidth: 2, 
                                    shadowBlur: 15, 
                                    shadowColor: '#00f3ff' 
                                },
                                label: { 
                                    color: '#fff', fontSize: 13, formatter: '{b}\\n{d}%', fontWeight: 'bold',
                                    position: 'outside', textShadowBlur: 8, textShadowColor: '#00f3ff'
                                },
                                labelLine: { lineStyle: { width: 2 }, length: 20, length2: 15 },
                                data: chartData,
                                startAngle: 90,
                                animationDuration: 1000
                            },
                            {
                                type: 'pie',
                                radius: ['34%', '36%'],
                                center: ['50%', '55%'],
                                itemStyle: { color: 'transparent', borderColor: '#ff00ff', borderWidth: 2 },
                                label: { show: false },
                                labelLine: { show: false },
                                data: [{value: 1}],
                                startAngle: 90,
                                animation: false
                            }
                        ]
                    };
                }

                // YENİ FÜTÜRİSTİK ÇİZGİ GRAFİK TASARIMI (Glow & Gradient Alan Desteğiyle)
                function getLineOption(titleText, xData, seriesData) {
                    return {
                        title: { 
                            text: titleText, 
                            textStyle: { color: '#ffffff', fontSize: 16, fontWeight: 'bold' },
                            left: 'center', top: '2%'
                        },
                        tooltip: { trigger: 'axis', backgroundColor: 'rgba(0,0,0,0.8)', textStyle: { color: '#fff' } },
                        legend: { bottom: '2%', textStyle: { color: '#ffffff', fontWeight: 'bold' } },
                        grid: { left: '4%', right: '4%', bottom: '15%', top: '20%', containLabel: true },
                        xAxis: {
                            type: 'category',
                            data: xData,
                            axisLabel: { color: '#00f3ff', fontSize: 11 },
                            axisLine: { lineStyle: { color: '#00f3ff' } }
                        },
                        yAxis: {
                            type: 'value',
                            splitLine: { lineStyle: { color: 'rgba(0, 243, 255, 0.1)', type: 'dashed' } },
                            axisLabel: { color: '#00f3ff' }
                        },
                        series: seriesData.map(s => ({
                            name: s.name,
                            type: 'line',
                            data: s.data,
                            smooth: true,
                            lineStyle: { width: 4, shadowBlur: 10, shadowColor: s.color, color: s.color },
                            symbol: 'circle',
                            symbolSize: 8,
                            itemStyle: { color: s.color },
                            areaStyle: {
                                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                    { offset: 0, color: s.color + '33' },
                                    { offset: 1, color: 'transparent' }
                                ])
                            }
                        }))
                    };
                }

                const charts = {
                    c1: echarts.init(document.getElementById('c1')), c2: echarts.init(document.getElementById('c2')),
                    c3: echarts.init(document.getElementById('c3')), c4: echarts.init(document.getElementById('c4')),
                    c5: echarts.init(document.getElementById('c5')), c6: echarts.init(document.getElementById('c6'))
                };

                // GRAFİKLERİN ÇİZİMİ (İstediğin Gibi Yerleri Değiştirildi)
                charts.c3.setOption(getDonutOption('1. Harcama Yapılan İlk 5 Firma (USD)', c3_data));
                charts.c4.setOption(getDonutOption('2. Tür Bazlı Harcama Dağılımı', c4_data));
                charts.c1.setOption(getBarOption('3. En Çok Sipariş Edilen İlk 10 Ürün (Adet)', data.c1_names, data.c1_vals, '#00f3ff'));
                charts.c2.setOption(getBarOption('4. En Çok Sermaye Yatırılan İlk 10 Ürün ($)', data.c2_names, data.c2_vals, '#ff00ff'));
                
                // 5. Grafik: 5 Aylık Harcama Trend Akışı
                charts.c5.setOption(getLineOption('5. Aylık Toplam Sermaye Akışı (Son 5 Ay)', data.c5_months, [
                    { name: 'Sermaye ($)', data: data.c5_vals, color: '#00ff66' }
                ]));

                // 6. Grafik: Nakliye Oranı (Hava Turuncu, Deniz Mavi Çizgi)
                charts.c6.setOption(getLineOption('6. Nakliye Türü Dağılımı (Hava vs Deniz)', data.c6_months, [
                    { name: 'Hava', data: data.c6_air, color: '#ffaa00' },
                    { name: 'Deniz', data: data.c6_sea, color: '#0011ff' }
                ]));

                // Donut dönme animasyonu sadece c3 ve c4 için korundu
                let currentAngle = 90;
                setInterval(() => {
                    currentAngle = (currentAngle - 0.3) % 360; 
                    const updateOpt = {
                        series: [
                            { startAngle: currentAngle, animation: false },
                            { startAngle: currentAngle, animation: false }
                        ]
                    };
                    charts.c3.setOption(updateOpt);
                    charts.c4.setOption(updateOpt);
                }, 30);

                window.addEventListener('resize', () => {
                    Object.values(charts).forEach(c => c.resize());
                });
            </script>
        </body>
        </html>
        """
        
        html_ready = html_template.replace("__TIMELINE_MATRIX__", json.dumps(timeline_matrix)).replace("__MONTHS_SEQUENCE__", json.dumps(months_sequence))
        st.components.v1.html(html_ready, height=1700, scrolling=False)


# --- SAYFA 2: FİRMA BAZLI ANALİZ ---
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
            
            import plotly.express as px
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
                
            firma_df_temp = firma_df.copy()
            firma_df_temp['SIPARIS_AY'] = firma_df_temp['SIPARIS_TARIHI'].apply(lambda x: x[:7] if x != "BELİRTİLMEMİŞ" and len(x) >= 7 else "Bilinmeyen Dönem")
            trend_data_all = firma_df_temp.groupby('SIPARIS_AY')['TOPLAM_SERMAYE'].sum().reset_index().sort_values('SIPARIS_AY')
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
            st.dataframe(display_df_formatted, use_container_width=True)

# --- SAYFA 3: HAM VERİ ---
elif page == "3. Ham Veri":
    st.header("🗄️ Ham Veri Havuzu")
    if df_dashboard.empty:
        st.error("Veri havuzu boş.")
    else:
        st.markdown("Sistem tarafından çekilen ve birleştirilen tüm temizlenmiş ham veriler aşağıdadır:")
        df_all_formatted = df_dashboard.copy()
        df_all_formatted['FIYAT'] = df_all_formatted['FIYAT'].map('{:,.2f} $'.format)
        df_all_formatted['TOPLAM_SERMAYE'] = df_all_formatted['TOPLAM_SERMAYE'].map('{:,.2f} $'.format)
        
        drop_cols_all = [c for c in ['ORIJINAL_FIYAT', 'PARA_BIRIMI'] if c in df_all_formatted.columns]
        if drop_cols_all:
            df_all_formatted = df_all_formatted.drop(columns=drop_cols_all)
            
        st.dataframe(df_all_formatted, use_container_width=True)