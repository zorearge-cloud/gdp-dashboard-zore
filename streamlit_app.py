import streamlit as st
import pandas as pd
import requests
import io
import openpyxl
import datetime
import json
import re

# --- AYARLAR VE ANAYASA ---
st.set_page_config(layout="wide", page_title="ZORE Veri Paneli")

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

def strict_date_string_parser(val):
    if pd.isna(val) or val == "":
        return "BELİRTİLMEMİŞ"
    if hasattr(val, 'strftime'):
        return val.strftime('%Y-%m-%d')
    
    val_str = str(val).strip()
    if " " in val_str: val_str = val_str.split()[0]
    val_str = val_str.replace('/', '.').replace('-', '.')
    
    for fmt in ['%Y.%m.%d', '%d.%m.%Y', '%Y.%d.%m']:
        try:
            dt = datetime.datetime.strptime(val_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except: continue
            
    try:
        dt = pd.to_datetime(val_str, dayfirst=True, errors='coerce')
        if not pd.isna(dt): return dt.strftime('%Y-%m-%d')
    except: pass
    return "BELİRTİLMEMİŞ"

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
        
            if pd.isna(val): return 0.0, 0.0, '$'
            
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
        except: continue
            
    full_df = pd.concat(all_data_list, ignore_index=True) if all_data_list else pd.DataFrame()
    if not full_df.empty:
        def get_clean_period(x):
            if x == "BELİRTİLMEMİŞ" or len(x) < 7: return "Bilinmeyen Dönem"
            return x[:7]
        full_df['SIPARIS_AY'] = full_df['SIPARIS_TARIHI'].apply(get_clean_period)
        
    return full_df, pool

df_dashboard, data_pool = get_all_data(rates)

st.sidebar.title("ZORE KURUMSAL PANEL")
st.sidebar.markdown(f"**Finansal Kur Durumu:** `{rates['PROUNCE']}`")
st.sidebar.text(f"1 EUR = {rates['EUR_TO_USD']:.4f} $")
st.sidebar.text(f"1 CNY = {rates['CNY_TO_USD']:.4f} $")
st.sidebar.markdown("---")

page = st.sidebar.radio("Menü", ["1. Genel Analiz Paneli", "2. Firma Bazlı Analiz", "3. Ham Veri"])

# --- SAYFA 1: GENEL DASHBOARD (KURUMSAL VE SABİT TASARIM) ---
if page == "1. Genel Dashboard":
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
        valid_df = df_dashboard[df_dashboard['SIPARIS_AY'] != "Bilinmeyen Dönem"].copy()
        months_sequence = sorted(valid_df['SIPARIS_AY'].unique().tolist())
        
        if not months_sequence:
            months_sequence = ["Genel"]
            
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
            c3_data = [{"value": round(row['TOPLAM_SERMAYE'],2), "name": row['FIRMA']} for _, row in c3_df.iterrows()]
            
            c4_df = df_cum.groupby('TUR')['TOPLAM_SERMAYE'].sum().nlargest(5).reset_index()
            c4_data = [{"value": round(row['TOPLAM_SERMAYE'],2), "name": row['TUR']} for _, row in c4_df.iterrows()]
            
            df_barkod = df_cum[(df_cum['BARKOD'] != "BELİRTİLMEMİŞ") & (df_cum['BARKOD'].str.strip() != "")]
            c8_df = df_barkod.groupby('BARKOD').agg({'ADET': 'sum'}).nlargest(5, 'ADET').reset_index().iloc[::-1]
            
            curr_months = [m for m in months_sequence if m <= month]
            
            c5_series = []
            for f in top_5_firmalar:
                f_data = trend_firma[trend_firma['FIRMA'] == f]
                data = [f_data[f_data['SIPARIS_AY'] == m]['TOPLAM_SERMAYE'].sum() if m in f_data['SIPARIS_AY'].values else 0 for m in curr_months]
                c5_series.append({"name": f, "data": [round(x,2) for x in data]})
                
            c6_series = []
            for t in top_5_turler:
                t_data = trend_tur[trend_tur['TUR'] == t]
                data = [t_data[t_data['SIPARIS_AY'] == m]['TOPLAM_SERMAYE'].sum() if m in t_data['SIPARIS_AY'].values else 0 for m in curr_months]
                c6_series.append({"name": t, "data": [round(x,2) for x in data]})
                
            c7_data = [round(trend_total[trend_total['SIPARIS_AY'] == m]['TOPLAM_SERMAYE'].sum(), 2) if m in trend_total['SIPARIS_AY'].values else 0 for m in curr_months]
            
            timeline_matrix[month] = {
                "c1_names": c1_df['MALIN CINSI'].tolist(), "c1_vals": c1_df['ADET'].tolist(),
                "c2_names": c2_df['MALIN CINSI'].tolist(), "c2_vals": c2_df['TOPLAM_SERMAYE'].tolist(),
                "c3_data": c3_data, "c4_data": c4_data,
                "c5_series": c5_series, "c6_series": c6_series,
                "c7_months": curr_months, "c7_data": c7_data,
                "c8_names": c8_df['BARKOD'].tolist(), "c8_vals": c8_df['ADET'].tolist(),
            }

        # HTML VE JAVASCRIPT TEMPLATE (KURUMSAL VE DÖNEN DONUT TASARIMI)
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
                
                .grid-container { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; padding: 20px; }
                
                .panel { 
                    background: rgba(2, 6, 19, 0.9);
                    border: 2px solid #00f3ff; 
                    border-radius: 12px; 
                    box-shadow: 0 0 20px rgba(0, 243, 255, 0.5), inset 0 0 15px rgba(0, 243, 255, 0.2);
                    height: 420px; 
                    padding: 15px; 
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
                
                // Genel Toplam verilerini sabitlemek için sadece dizideki "Son Ay" verisini çekiyoruz.
                const lastMonth = monthsSequence[monthsSequence.length - 1];
                const data = timelineMatrix[lastMonth];

                // Bütün grafik tiplerini Echarts Donut yapısına (isim ve değer objesi) uygun hale getiriyoruz
                const c1_data = data.c1_names.map((n, i) => ({name: n, value: data.c1_vals[i]}));
                const c2_data = data.c2_names.map((n, i) => ({name: n, value: data.c2_vals[i]}));
                const c3_data = data.c3_data;
                const c4_data = data.c4_data;
                const c5_data = data.c5_series.map(s => ({name: s.name, value: Number(s.data.reduce((a,b)=>a+b, 0).toFixed(2))}));
                const c6_data = data.c6_series.map(s => ({name: s.name, value: Number(s.data.reduce((a,b)=>a+b, 0).toFixed(2))}));
                const c7_data = data.c7_months.map((m, i) => ({name: m, value: data.c7_data[i]}));
                const c8_data = data.c8_names.map((n, i) => ({name: n, value: data.c8_vals[i]}));

                // Görseldeki Neon Renk Paleti
                const colorPalette = ['#00f3ff', '#ff00ff', '#00ff66', '#ffaa00', '#aa00ff', '#ff3300', '#0011ff'];

                function getDonutOption(titleText, chartData) {
                    return {
                        title: { 
                            text: titleText, 
                            textStyle: { color: '#ffffff', fontSize: 14, fontWeight: 'bold' },
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
                                label: { color: '#fff', fontSize: 12, formatter: '{b}\\n{d}%', fontWeight: 'bold' },
                                labelLine: { lineStyle: { width: 2 } },
                                data: chartData,
                                startAngle: 90,
                                animationDuration: 1000
                            },
                            {
                                // Resimdeki gibi içeride bulunan ince dekoratif neon halka
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

                const charts = {
                    c1: echarts.init(document.getElementById('c1')), c2: echarts.init(document.getElementById('c2')),
                    c3: echarts.init(document.getElementById('c3')), c4: echarts.init(document.getElementById('c4')),
                    c5: echarts.init(document.getElementById('c5')), c6: echarts.init(document.getElementById('c6')),
                    c7: echarts.init(document.getElementById('c7')), c8: echarts.init(document.getElementById('c8'))
                };

                charts.c1.setOption(getDonutOption('1. En Çok Sipariş Edilen İlk 5 Ürün (Adet)', c1_data));
                charts.c2.setOption(getDonutOption('2. En Çok Sermaye Yatırılan İlk 5 Ürün ($)', c2_data));
                charts.c3.setOption(getDonutOption('3. Harcama Yapılan İlk 5 Firma (USD)', c3_data));
                charts.c4.setOption(getDonutOption('4. Tür Bazlı Harcama Dağılımı', c4_data));
                charts.c5.setOption(getDonutOption('5. Firma Harcama Dağılımı Özeti', c5_data));
                charts.c6.setOption(getDonutOption('6. Kategori Harcama Dağılımı Özeti', c6_data));
                charts.c7.setOption(getDonutOption('7. Aylara Göre Toplam Sermaye Payı ($)', c7_data));
                charts.c8.setOption(getDonutOption('8. Barkod Bazlı İlk 5 Ürün (Adet)', c8_data));

                // İstenilen Yavaş ve Pürüzsüz Dönme Efekti Motoru
                let currentAngle = 90;
                setInterval(() => {
                    currentAngle = (currentAngle - 0.3) % 360; 
                    const updateOpt = {
                        series: [
                            { startAngle: currentAngle, animation: false },
                            { startAngle: currentAngle, animation: false }
                        ]
                    };
                    Object.values(charts).forEach(c => c.setOption(updateOpt));
                }, 30);

                window.addEventListener('resize', () => {
                    Object.values(charts).forEach(c => c.resize());
                });
            </script>
        </body>
        </html>
        """
        
        html_ready = html_template.replace("__TIMELINE_MATRIX__", json.dumps(timeline_matrix)).replace("__MONTHS_SEQUENCE__", json.dumps(months_sequence))
        
        # Ekran sığmama sorunu için yükseklik 1700'den 2100'e çıkarıldı.
        st.components.v1.html(html_ready, height=2100, scrolling=False)
        
# --- SAYFA 3: HAM VERİ ---
elif page == "3. Ham Veri":
    st.header("🗄️ Konsolide Ham Veri Deposu")
    if df_dashboard.empty:
        st.warning("Görüntülenecek ham veri bulunamadı.")
    else:
        st.markdown(f"Tüm kaynaklardan çekilen ve standartlaştırılan toplam **{len(df_dashboard)}** adet kayıt listelenmektedir.")
        
        search_all = st.text_input("Genel Arama (Firma, Ürün Cinsi veya Barkod):", placeholder="Tabloda filtrelemek istediğiniz kelimeyi yazın...")
        df_final_display = df_dashboard.copy()
        
        if search_all:
            mask = df_final_display.astype(str).apply(lambda row: row.str.contains(search_all, case=False).any(), axis=1)
            df_final_display = df_final_display[mask]
            st.info(f"Filtreleme Sonucu: {len(df_final_display)} kayıt listeleniyor.")
            
        df_final_formatted = df_final_display.copy()
        df_final_formatted['FIYAT'] = df_final_formatted['FIYAT'].map('{:,.2f} $'.format)
        df_final_formatted['TOPLAM_SERMAYE'] = df_final_formatted['TOPLAM_SERMAYE'].map('{:,.2f} $'.format)
        
        drop_cols_raw = [c for c in ['ORIJINAL_FIYAT', 'PARA_BIRIMI'] if c in df_final_formatted.columns]
        if drop_cols_raw:
            df_final_formatted = df_final_formatted.drop(columns=drop_cols_raw)
            
        st.dataframe(df_final_formatted, use_container_width=True)