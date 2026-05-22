import streamlit as st
import pandas as pd
import requests
import io
import openpyxl
import datetime
import json
import math
import re

# --- AYARLAR VE ANAYASA (TAM KAPSAMLI YAPI) ---
st.set_page_config(layout="wide", page_title="ZORE Veri Paneli")

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
    'MALIN CINSI': 'MALIN CINSI', 'ADET': 'ADET', 'FIYAT': 'FIYAT',
    'YUKLEME TARIHI': 'YUKLEME_TARIHI', 'YUKLEME_TARIHI': 'YUKLEME_TARIHI'
}

# --- GÜVENLİ VERİ DÖNÜŞÜM MOTORU (Grafik Çökmelerini Engeller) ---
def safe_float(v):
    if pd.isna(v): return 0.0
    try:
        val = float(v)
        if math.isnan(val) or math.isinf(val): return 0.0
        return round(val, 2)
    except:
        return 0.0

def safe_str(v):
    if pd.isna(v): return "BELİRTİLMEMİŞ"
    return str(v)

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

# --- SAYFA 1: GENEL DASHBOARD (SİBER SAVAŞ ODASI MATRİSİ) ---
if page == "1. Genel Dashboard":
    st.header("📊 Genel Dashboard - Siber İzleme Merkezi")
    
    if df_dashboard.empty:
        st.error("Veri havuzunda işlenecek kayıt bulunamadı.")
    else:
        # Üst Metrik Kartları
        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Sipariş Adedi", f"{int(df_dashboard['ADET'].sum()):,}")
        c2.metric("Toplam Sermaye Yatırımı (USD)", f"{df_dashboard['TOPLAM_SERMAYE'].sum():,.2f} $")
        c3.metric("Çalışılan Firma Sayısı", df_dashboard['FIRMA'].nunique())
        st.markdown("---")
        
        # SİNEMATİK VERİ HAZIRLIĞI
        valid_df = df_dashboard[df_dashboard['SIPARIS_AY'] != "Bilinmeyen Dönem"].copy()
        months_sequence = sorted(valid_df['SIPARIS_AY'].unique().tolist())
        
        if not months_sequence:
            months_sequence = ["Genel"]
            
        # Ön Hesaplamalar (Line grafikleri için - BURASI DA İLK 5 YAPILDI)
        top_5_firmalar = df_dashboard.groupby('FIRMA')['TOPLAM_SERMAYE'].sum().nlargest(5).index
        trend_firma = df_dashboard[df_dashboard['FIRMA'].isin(top_5_firmalar)].groupby(['SIPARIS_AY', 'FIRMA'])['TOPLAM_SERMAYE'].sum().reset_index()
        
        top_5_turler = df_dashboard.groupby('TUR')['TOPLAM_SERMAYE'].sum().nlargest(5).index
        trend_tur = df_dashboard[df_dashboard['TUR'].isin(top_5_turler)].groupby(['SIPARIS_AY', 'TUR'])['TOPLAM_SERMAYE'].sum().reset_index()
        
        trend_total = df_dashboard.groupby('SIPARIS_AY')['TOPLAM_SERMAYE'].sum().reset_index()
        
        timeline_matrix = {}
        for month in months_sequence:
            df_cum = df_dashboard[df_dashboard['SIPARIS_AY'] <= month]
            
            c1_df = df_cum.groupby('MALIN CINSI')['ADET'].sum().nlargest(5).reset_index().iloc[::-1]
            c2_df = df_cum.groupby('MALIN CINSI')['TOPLAM_SERMAYE'].sum().nlargest(5).reset_index().iloc[::-1]
            c3_df = df_cum.groupby('FIRMA')['TOPLAM_SERMAYE'].sum().nlargest(5).reset_index()
            c4_df = df_cum.groupby('TUR')['TOPLAM_SERMAYE'].sum().nlargest(5).reset_index()
            
            df_barkod = df_cum[(df_cum['BARKOD'] != "BELİRTİLMEMİŞ") & (df_cum['BARKOD'].str.strip() != "")]
            c8_df = df_barkod.groupby('BARKOD').agg({'ADET': 'sum'}).nlargest(5, 'ADET').reset_index().iloc[::-1]
            
            curr_months = [m for m in months_sequence if m <= month]
            
            c5_series = []
            for f in top_5_firmalar:
                f_data = trend_firma[trend_firma['FIRMA'] == f]
                data = [f_data[f_data['SIPARIS_AY'] == m]['TOPLAM_SERMAYE'].sum() if m in f_data['SIPARIS_AY'].values else 0.0 for m in curr_months]
                c5_series.append({"name": safe_str(f), "type": "line", "smooth": True, "showSymbol": False, "data": [safe_float(x) for x in data]})
                
            c6_series = []
            for t in top_5_turler:
                t_data = trend_tur[trend_tur['TUR'] == t]
                data = [t_data[t_data['SIPARIS_AY'] == m]['TOPLAM_SERMAYE'].sum() if m in t_data['SIPARIS_AY'].values else 0.0 for m in curr_months]
                c6_series.append({"name": safe_str(t), "type": "line", "smooth": True, "showSymbol": False, "data": [safe_float(x) for x in data]})
                
            c7_data = [trend_total[trend_total['SIPARIS_AY'] == m]['TOPLAM_SERMAYE'].sum() if m in trend_total['SIPARIS_AY'].values else 0.0 for m in curr_months]
            
            # GÜVENLİ VERİ ATAMASI (NumPy Çökmeleri Engellendi)
            timeline_matrix[month] = {
                "c1_names": [safe_str(x) for x in c1_df['MALIN CINSI']], 
                "c1_vals": [safe_float(x) for x in c1_df['ADET']],
                "c2_names": [safe_str(x) for x in c2_df['MALIN CINSI']], 
                "c2_vals": [safe_float(x) for x in c2_df['TOPLAM_SERMAYE']],
                "c3_data": [{"value": safe_float(row['TOPLAM_SERMAYE']), "name": safe_str(row['FIRMA'])} for _, row in c3_df.iterrows()],
                "c4_data": [{"value": safe_float(row['TOPLAM_SERMAYE']), "name": safe_str(row['TUR'])} for _, row in c4_df.iterrows()],
                "c5_series": c5_series,
                "c6_series": c6_series,
                "c7_months": [safe_str(x) for x in curr_months], 
                "c7_data": [safe_float(x) for x in c7_data],
                "c8_names": [safe_str(x) for x in c8_df['BARKOD']], 
                "c8_vals": [safe_float(x) for x in c8_df['ADET']],
            }

        # HTML VE JAVASCRIPT TEMPLATE (TAMAMEN SABİT 2D, ANİMASYONSUZ/DÖNMESİZ TEMİZ TASARIM)
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
            <style>
                body { background-color: #03050a; font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; padding: 10px; overflow-x: hidden; color: #fff; }
                .header-box { text-align: center; border-bottom: 2px solid #00f3ff; padding-bottom: 15px; margin-bottom: 40px; }
                .matrix-title { color: #fff; font-size: 24px; letter-spacing: 4px; margin: 0; text-shadow: 0 0 10px #00f3ff; }
                .matrix-subtitle { color: #00ff66; font-size: 16px; margin-top: 8px; font-weight: bold; }
                .period-badge { color: #ff00ff; background: rgba(255,0,255,0.15); padding: 5px 18px; border-radius: 6px; border: 1px solid #ff00ff; font-family: monospace; font-size: 18px; margin-left: 15px; }
                
                .grid-container { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; padding: 20px; }
                
                /* 3D DÖNME VEYA ANİMASYON TAMAMEN SİLİNDİ - SABİT TEMİZ PANEL */
                .panel { 
                    background: rgba(2, 6, 19, 0.85); 
                    border: 2px solid #00f3ff; 
                    border-radius: 12px; 
                    box-shadow: 0 0 15px rgba(0, 243, 255, 0.3); 
                    height: 400px; 
                    width: 100%;
                    padding: 15px; 
                    box-sizing: border-box;
                }
            </style>
        </head>
        <body>
            <div class="header-box">
                <h2 class="matrix-title">🎬 ZORE CYBERSPACE DASHBOARD</h2>
                <div class="matrix-subtitle">
                    SİSTEM DURUMU: <span style="color: #00ff66;">AKTİF</span> | 
                    ZAMAN ÇİZELGESİ TARANIYOR: <span id="active-period" class="period-badge">BAŞLIYOR...</span>
                </div>
            </div>
            
            <div class="grid-container">
                <div id="c1" class="panel"></div>
                <div id="c2" class="panel"></div>
                <div id="c3" class="panel"></div>
                <div id="c4" class="panel"></div>
                <div id="c5" class="panel"></div>
                <div id="c6" class="panel"></div>
                <div id="c7" class="panel"></div>
                <div id="c8" class="panel"></div>
            </div>

            <script>
                const timelineMatrix = __TIMELINE_MATRIX__;
                const monthsSequence = __MONTHS_SEQUENCE__;
                let currentIndex = 0;
                
                // Fütüristik Neon ECharts Ayarları
                const textStyle = { color: '#ffffff', fontSize: 13, fontWeight: 'bold' };
                const axisLabelStyle = { color: '#00f3ff', fontSize: 11, width: 120, overflow: 'truncate' };
                const splitLineStyle = { lineStyle: { color: 'rgba(0, 243, 255, 0.2)' } };

                // Grafikleri Başlat
                const charts = {
                    c1: echarts.init(document.getElementById('c1')), c2: echarts.init(document.getElementById('c2')),
                    c3: echarts.init(document.getElementById('c3')), c4: echarts.init(document.getElementById('c4')),
                    c5: echarts.init(document.getElementById('c5')), c6: echarts.init(document.getElementById('c6')),
                    c7: echarts.init(document.getElementById('c7')), c8: echarts.init(document.getElementById('c8'))
                };

                // Sabit Seçenekleri Ayarla
                charts.c1.setOption({ title: { text: '1. En Çok Sipariş Edilen İlk 5 Ürün (Adet)', textStyle: textStyle }, tooltip: { trigger: 'axis' }, grid: { left: '25%', right: '5%', bottom: '5%', top: '15%' }, xAxis: { type: 'value', splitLine: splitLineStyle, axisLabel: axisLabelStyle }, yAxis: { type: 'category', axisLabel: axisLabelStyle } });
                charts.c2.setOption({ title: { text: '2. En Çok Sermaye Yatırılan İlk 5 Ürün ($)', textStyle: textStyle }, tooltip: { trigger: 'axis' }, grid: { left: '25%', right: '5%', bottom: '5%', top: '15%' }, xAxis: { type: 'value', splitLine: splitLineStyle, axisLabel: axisLabelStyle }, yAxis: { type: 'category', axisLabel: axisLabelStyle } });
                
                // Fütüristik Donut Chart - Firma
                charts.c3.setOption({ 
                    title: { text: '3. Harcama Yapılan İlk 5 Firma (USD)', textStyle: textStyle }, 
                    tooltip: { trigger: 'item' },
                    color: ['#00f3ff', '#ff00ff', '#00ff66', '#ffaa00', '#aa00ff'], 
                    series: [
                        { 
                            type: 'pie', radius: ['45%', '70%'], center: ['50%', '55%'], 
                            itemStyle: { borderRadius: 5, borderColor: '#03050a', borderWidth: 2 }, 
                            label: { color: '#fff', fontSize: 11, formatter: '{b}\\n{d}%' },
                            labelLine: { lineStyle: { color: '#00f3ff', width: 2 } }
                        },
                        {
                            type: 'pie', radius: ['35%', '36%'], center: ['50%', '55%'],
                            itemStyle: { color: 'transparent', borderColor: '#ff00ff', borderWidth: 2, type: 'dashed' },
                            label: { show: false }, labelLine: { show: false }, data: [{value: 1}]
                        }
                    ] 
                });
                
                // Fütüristik Donut Chart - Tür
                charts.c4.setOption({ 
                    title: { text: '4. Tür Bazlı Harcama Dağılımı (İlk 5)', textStyle: textStyle }, 
                    tooltip: { trigger: 'item' },
                    color: ['#00ff66', '#00f3ff', '#ffaa00', '#ff00ff', '#aa00ff'], 
                    series: [
                        { 
                            type: 'pie', radius: ['45%', '70%'], center: ['50%', '55%'], 
                            itemStyle: { borderRadius: 5, borderColor: '#03050a', borderWidth: 2 }, 
                            label: { color: '#fff', fontSize: 11, formatter: '{b}\\n{d}%' },
                            labelLine: { lineStyle: { color: '#00ff66', width: 2 } }
                        },
                        {
                            type: 'pie', radius: ['75%', '76%'], center: ['50%', '55%'],
                            itemStyle: { color: 'transparent', borderColor: '#00f3ff', borderWidth: 2, type: 'dotted' },
                            label: { show: false }, labelLine: { show: false }, data: [{value: 1}]
                        }
                    ] 
                });
                
                charts.c5.setOption({ title: { text: '5. Aylık Firma Harcama Trendi (Top 5)', textStyle: textStyle }, tooltip: { trigger: 'axis' }, grid: { left: '10%', right: '5%', bottom: '10%', top: '20%' }, xAxis: { type: 'category', axisLabel: axisLabelStyle }, yAxis: { type: 'value', splitLine: splitLineStyle, axisLabel: axisLabelStyle } });
                charts.c6.setOption({ title: { text: '6. Aylık Tür Harcama Trendi (Top 5)', textStyle: textStyle }, tooltip: { trigger: 'axis' }, grid: { left: '10%', right: '5%', bottom: '10%', top: '20%' }, xAxis: { type: 'category', axisLabel: axisLabelStyle }, yAxis: { type: 'value', splitLine: splitLineStyle, axisLabel: axisLabelStyle } });
                charts.c7.setOption({ title: { text: '7. Aylık Toplam Sermaye Akışı ($)', textStyle: textStyle }, tooltip: { trigger: 'axis' }, grid: { left: '10%', right: '5%', bottom: '10%', top: '15%' }, xAxis: { type: 'category', axisLabel: axisLabelStyle, splitLine: splitLineStyle }, yAxis: { type: 'value', splitLine: splitLineStyle, axisLabel: axisLabelStyle }, series: [{ type: 'line', smooth: true, areaStyle: { color: 'rgba(0, 243, 255, 0.3)' }, lineStyle: { color: '#00f3ff', width: 4 }, itemStyle: { color: '#00f3ff' } }] });
                charts.c8.setOption({ title: { text: '8. Barkod Bazlı İlk 5 Ürün (Adet)', textStyle: textStyle }, tooltip: { trigger: 'axis' }, grid: { left: '20%', right: '5%', bottom: '5%', top: '15%' }, xAxis: { type: 'value', splitLine: splitLineStyle, axisLabel: axisLabelStyle }, yAxis: { type: 'category', axisLabel: axisLabelStyle } });

                // Renk Paletleri
                const gradBlue = new echarts.graphic.LinearGradient(0,0,1,0, [{offset:0, color:'#0011ff'}, {offset:1, color:'#00f3ff'}]);
                const gradOrange = new echarts.graphic.LinearGradient(0,0,1,0, [{offset:0, color:'#ff3300'}, {offset:1, color:'#ffcc00'}]);
                const gradPink = new echarts.graphic.LinearGradient(0,0,1,0, [{offset:0, color:'#aa00ff'}, {offset:1, color:'#ff00ff'}]);

                function updateDashboard() {
                    if (!monthsSequence || monthsSequence.length === 0) return;
                    const month = monthsSequence[currentIndex];
                    const data = timelineMatrix[month];
                    if (!data) return;
                    
                    document.getElementById('active-period').innerText = (currentIndex === monthsSequence.length - 1) ? month + " (GENEL TOPLAM)" : month;

                    charts.c1.setOption({ yAxis: { data: data.c1_names }, series: [{ type: 'bar', data: data.c1_vals, itemStyle: { color: gradBlue, borderRadius: [0,4,4,0] } }] });
                    charts.c2.setOption({ yAxis: { data: data.c2_names }, series: [{ type: 'bar', data: data.c2_vals, itemStyle: { color: gradOrange, borderRadius: [0,4,4,0] } }] });
                    
                    charts.c3.setOption({ series: [{ data: data.c3_data }, {}] });
                    charts.c4.setOption({ series: [{ data: data.c4_data }, {}] });
                    
                    const c5_styled = data.c5_series.map(s => ({...s, lineStyle: {width: 3}}));
                    const c6_styled = data.c6_series.map(s => ({...s, lineStyle: {width: 3}}));

                    charts.c5.setOption({ xAxis: { data: data.c7_months }, series: c5_styled });
                    charts.c6.setOption({ xAxis: { data: data.c7_months }, series: c6_styled });
                    charts.c7.setOption({ xAxis: { data: data.c7_months }, series: [{ data: data.c7_data }] });
                    charts.c8.setOption({ yAxis: { data: data.c8_names }, series: [{ type: 'bar', data: data.c8_vals, itemStyle: { color: gradPink, borderRadius: [0,4,4,0] } }] });
                }

                function loopEngine() {
                    updateDashboard();
                    let delay = 2500;
                    if (currentIndex === monthsSequence.length - 1) {
                        delay = 8000;
                        currentIndex = 0;
                    } else {
                        currentIndex++;
                    }
                    setTimeout(loopEngine, delay);
                }

                setTimeout(loopEngine, 500);

                window.addEventListener('resize', () => {
                    Object.values(charts).forEach(c => c.resize());
                });
            </script>
        </body>
        </html>
        """
        
        # Python tarafında bozuk veri çıkma ihtimaline karşı %100 güvenli JSON transferi yapıldı
        html_ready = html_template.replace("__TIMELINE_MATRIX__", json.dumps(timeline_matrix, ensure_ascii=False)).replace("__MONTHS_SEQUENCE__", json.dumps(months_sequence, ensure_ascii=False))
        
        st.components.v1.html(html_ready, height=1850, scrolling=False)

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
                
            trend_data_all = firma_df.groupby('SIPARIS_AY')['TOPLAM_SERMAYE'].sum().reset_index().sort_values('SIPARIS_AY')
            if not trend_data_all.empty and trend_data_all['TOPLAM_SERMAYE'].sum() > 0:
                fig_b = px.bar(trend_data_all, x='SIPARIS_AY', y='TOPLAM_SERMAYE', title=f"{selected_firma} Dönemsel Alım Trendi ($)", color='TOPLAM_SERMAYE')
                # YARIM KALAN KOD TAMAMLANDI:
                fig_b.update_layout(xaxis_title="Sipariş Ayı", yaxis_title="Toplam Sermaye (USD)", template="plotly_dark")
                col_b.plotly_chart(fig_b, use_container_width=True)

# --- SAYFA 3: HAM VERİ ---
elif page == "3. Ham Veri":
    st.header("🗄️ Tüm Veri Havuzu (Ham)")
    if df_dashboard.empty:
        st.warning("Görüntülenecek veri bulunamadı.")
    else:
        st.dataframe(df_dashboard, use_container_width=True)