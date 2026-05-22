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

# --- SAYFA 1: GENEL ANALİZ PANELİ ---
if page == "1. Genel Analiz Paneli":
    st.header("📋 ZORE Sipariş Takip ve Performans Özet Paneli")
    
    if df_dashboard.empty:
        st.error("Veri havuzunda işlenecek kayıt bulunamadı.")
    else:
        # Üst Metrik Kartları
        c1, c2, c3 = st.columns(3)
        c1.metric("Genel Toplam Sipariş Adedi", f"{int(df_dashboard['ADET'].sum()):,}")
        c2.metric("Genel Toplam İşlem Hacmi (USD)", f"{df_dashboard['TOPLAM_SERMAYE'].sum():,.2f} $")
        c3.metric("Aktif Partner Firma Sayısı", df_dashboard['FIRMA'].nunique())
        st.markdown("---")
        
        # TÜM VERİYİ KAPSAYAN GENEL TOPLAM HESAPLAMALARI
        df_genel = df_dashboard.copy()
        
        c1_df = df_genel.groupby('MALIN CINSI')['ADET'].sum().nlargest(5).reset_index()
        c1_data = [{"value": int(row['ADET']), "name": str(row['MALIN CINSI'])} for _, row in c1_df.iterrows()]
        
        c2_df = df_genel.groupby('MALIN CINSI')['TOPLAM_SERMAYE'].sum().nlargest(5).reset_index()
        c2_data = [{"value": round(row['TOPLAM_SERMAYE'], 2), "name": str(row['MALIN CINSI'])} for _, row in c2_df.iterrows()]
        
        c3_df = df_genel.groupby('FIRMA')['TOPLAM_SERMAYE'].sum().nlargest(5).reset_index()
        c3_data = [{"value": round(row['TOPLAM_SERMAYE'],2), "name": str(row['FIRMA'])} for _, row in c3_df.iterrows()]
        
        c4_df = df_genel.groupby('TUR')['TOPLAM_SERMAYE'].sum().nlargest(5).reset_index()
        c4_data = [{"value": round(row['TOPLAM_SERMAYE'],2), "name": str(row['TUR'])} for _, row in c4_df.iterrows()]
        
        c5_df = df_genel.groupby('FIRMA')['ADET'].sum().nlargest(5).reset_index()
        c5_data = [{"value": int(row['ADET']), "name": str(row['FIRMA'])} for _, row in c5_df.iterrows()]
        
        c6_df = df_genel.groupby('TUR')['ADET'].sum().nlargest(5).reset_index()
        c6_data = [{"value": int(row['ADET']), "name": str(row['TUR'])} for _, row in c6_df.iterrows()]
        
        c7_df = df_genel.groupby('NAKLİYE_TÜRÜ')['TOPLAM_SERMAYE'].sum().nlargest(5).reset_index()
        c7_data = [{"value": round(row['TOPLAM_SERMAYE'], 2), "name": str(row['NAKLİYE_TÜRÜ'])} for _, row in c7_df.iterrows()]
        
        df_barkod = df_genel[(df_genel['BARKOD'] != "BELİRTİLMEMİŞ") & (df_genel['BARKOD'].str.strip() != "")]
        c8_df = df_barkod.groupby('BARKOD')['ADET'].sum().nlargest(5).reset_index()
        c8_data = [{"value": int(row['ADET']), "name": str(row['BARKOD'])} for _, row in c8_df.iterrows()]
        
        general_matrix = {
            "c1_data": c1_data, "c2_data": c2_data, "c3_data": c3_data, "c4_data": c4_data,
            "c5_data": c5_data, "c6_data": c6_data, "c7_data": c7_data, "c8_data": c8_data
        }

        # HTML VE KURUMSAL JAVASCRIPT TEMPLATE
        # GIF'teki gibi yazılar dışarıda (labelLine ile bağlı) ve grafik akıcı şekilde dönüyor.
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
            <style>
                body { background-color: #03050a; font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; padding: 10px; overflow-x: hidden; color: #fff; }
                .header-box { text-align: center; border-bottom: 2px solid #00f3ff; box-shadow: 0 5px 25px rgba(0, 243, 255, 0.2); padding-bottom: 15px; margin-bottom: 40px; }
                .matrix-title { color: #fff; font-size: 24px; letter-spacing: 2px; margin: 0; text-shadow: 0 0 10px rgba(0, 243, 255, 0.5); }
                .matrix-subtitle { color: #00ff66; font-size: 16px; margin-top: 8px; font-weight: bold; letter-spacing: 1px; }
                .period-badge { color: #ff00ff; background: rgba(255,0,255,0.1); padding: 4px 15px; border-radius: 4px; border: 1px solid #ff00ff; font-family: monospace; font-size: 16px; margin-left: 15px; }
                
                .grid-container { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; padding: 20px; }
                
                .panel { 
                    background: rgba(2, 6, 19, 0.9); border: 2px solid #00f3ff; 
                    border-radius: 8px; 
                    box-shadow: 0 0 20px rgba(0, 243, 255, 0.4); height: 380px; 
                    padding: 15px; 
                }
            </style>
        </head>
        <body>
            <div class="header-box">
                <h2 class="matrix-title">ZORE GENEL TOPLAM PERFORMANS İZLEME PANELİ</h2>
                <div class="matrix-subtitle">
                    PANEL DURUMU: <span style="color: #00ff66;">AKTİF</span> | İNCELEME DÖNEMİ: <span class="period-badge">TÜM ZAMANLAR (GENEL TOPLAM)</span>
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
                const chartData = __GENERAL_MATRIX__;
                
                const textStyle = { color: '#ffffff', fontSize: 13, fontWeight: 'bold' };
                const chartKeys = ['c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8'];
                
                const titles = {
                    c1: '1. En Çok Sipariş Edilen İlk 5 Ürün (Genel Toplam Adet)',
                    c2: '2. En Yüksek Hacimli İlk 5 Ürün (Genel Toplam USD)',
                    c3: '3. Firma Bazlı Harcama Dağılımı (Genel Toplam USD)',
                    c4: '4. Kategori Bazlı Harcama Dağılımı (Genel Toplam USD)',
                    c5: '5. Firma Bazlı Sipariş Dağılımı (Genel Toplam Adet)',
                    c6: '6. Kategori Bazlı Sipariş Dağılımı (Genel Toplam Adet)',
                    c7: '7. Lojistik ve Nakliye Türü Dağılımı (Genel Toplam USD)',
                    c8: '8. Barkod Bazlı Ürün Dağılımı (Genel Toplam Adet)'
                };

                const colors = {
                    c1: ['#00f3ff', '#00ff66', '#ff00ff', '#ffaa00', '#aa00ff'],
                    c2: ['#ff9f7f', '#ff6464', '#e062ae', '#37a2da', '#67e0e3'],
                    c3: ['#32c5e9', '#67e0e3', '#9fe6b8', '#ffdb5c', '#ff9f7f'],
                    c4: ['#00ff66', '#00f3ff', '#ffaa00', '#ff00ff', '#aa00ff'],
                    c5: ['#e7bcf3', '#e062ae', '#37a2da', '#32c5e9', '#9fe6b8'],
                    c6: ['#ffdb5c', '#ff9f7f', '#fb7293', '#e290d4', '#e7bcf3'],
                    c7: ['#67e0e3', '#37a2da', '#32c5e9', '#9fe6b8', '#ffdb5c'],
                    c8: ['#ff00ff', '#00f3ff', '#00ff66', '#ffaa00', '#aa00ff']
                };

                const charts = {};
                
                chartKeys.forEach(key => {
                    charts[key] = echarts.init(document.getElementById(key));
                    charts[key].setOption({
                        title: { text: titles[key], textStyle: textStyle, top: 15, left: 'center' },
                        tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
                        color: colors[key],
                        series: [
                            // Dış Veri Donut'ı (Dönecek Olan)
                            {
                                type: 'pie',
                                radius: ['48%', '62%'], // Pastaya yer açıldı
                                center: ['50%', '55%'],
                                itemStyle: { borderRadius: 4, borderColor: '#03050a', borderWidth: 2 },
                                // YAZILAR DIŞARIDA VE ÇİZGİLERLE BAĞLI (GIF TASARIMI)
                                label: { 
                                    show: true,
                                    position: 'outside', 
                                    formatter: '{b}', 
                                    color: '#ffffff', 
                                    fontSize: 12, 
                                    fontWeight: 'bold'
                                },
                                labelLine: { 
                                    show: true,
                                    length: 15,
                                    length2: 20,
                                    smooth: true,
                                    lineStyle: { width: 2 }
                                }, 
                                data: chartData[key + '_data'] 
                            },
                            // Ortadaki Sabit Neon Halka
                            {
                                type: 'pie',
                                radius: ['38%', '40%'], // İçeride küçük bir halka
                                center: ['50%', '55%'],
                                itemStyle: { color: 'transparent', borderColor: '#00f3ff', borderWidth: 2, type: 'dashed' },
                                label: { show: false },
                                labelLine: { show: false },
                                data: [{ value: 1 }],
                                silent: true
                            }
                        ]
                    });
                });

                // EKRAN VERİSİ SABİT KALIR, SADECE GRAFİĞİN DIŞ HALKASI YAVAŞÇA DÖNER
                let rotationAngle = 90;
                setInterval(() => {
                    rotationAngle += 0.5; // Saat yönünün tersine GIF'teki gibi pürüzsüz ağır dönüş
                    chartKeys.forEach(key => {
                        charts[key].setOption({
                            series: [
                                { startAngle: rotationAngle }, // index 0 (Dış Veri Donut'ı) döner
                                { startAngle: 90 } // index 1 (Neon Halka) sabit kalır
                            ]
                        });
                    });
                }, 40);
                
                window.addEventListener('resize', () => {
                    chartKeys.forEach(key => charts[key].resize());
                });
            </script>
        </body>
        </html>
        """
        
        html_ready = html_template.replace("__GENERAL_MATRIX__", json.dumps(general_matrix))
        
        st.components.v1.html(html_ready, height=2000, scrolling=False)

# --- SAYFA 2: FİRMA BAZLI ANALİZ ---
elif page == "2. Firma Bazlı Analiz":
    st.header("🏢 Firma Performans ve Barkod Analiz Ekranı")
    if df_dashboard.empty:
        st.error("Veri havuzu boş.")
    else:
        firmalar = sorted([str(f) for f in df_dashboard['FIRMA'].unique() if str(f) != "BELİRTİLMEMİŞ"])
        if not firmalar:
            st.warning("Analiz edilecek geçerli bir firma kaydı bulunamadı.")
        else:
            selected_firma = st.selectbox("Analiz edilecek partner firmayı seçin", firmalar)
            firma_df = df_dashboard[df_dashboard['FIRMA'] == selected_firma]
            
            c1, c2, c3 = st.columns(3)
            c1.metric(f"Toplam Alım Adedi", f"{int(firma_df['ADET'].sum()):,}")
            c2.metric(f"Toplam İşlem Hacmi (USD)", f"{firma_df['TOPLAM_SERMAYE'].sum():,.2f} $")
            tur_counts = firma_df.groupby('TUR')['ADET'].sum()
            en_cok_tur = tur_counts.idxmax() if not tur_counts.empty and tur_counts.sum() > 0 else "Veri Yok"
            c3.metric("Yoğunluklu Ürün Kategorisi", en_cok_tur)
            
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
                
                fig_a = px.pie(firma_df_pie, values='TOPLAM_SERMAYE', names='TUR_GRAFIK', title="Ürün Kategorisi Dağılım Payları", hole=0.4)
                fig_a.update_traces(textinfo='label+percent')
                col_a.plotly_chart(fig_a, use_container_width=True)
            else:
                col_a.info("Grafik için yeterli veri bulunmuyor.")
                
            trend_data_all = firma_df.groupby('SIPARIS_AY')['TOPLAM_SERMAYE'].sum().reset_index().sort_values('SIPARIS_AY')
            if not trend_data_all.empty and trend_data_all['TOPLAM_SERMAYE'].sum() > 0:
                fig_b = px.bar(trend_data_all, x='SIPARIS_AY', y='TOPLAM_SERMAYE', title="Dönemsel Ticari Hacim Dağılımı ($)", color='TOPLAM_SERMAYE')
                fig_b.update_layout(xaxis_type='category')
                col_b.plotly_chart(fig_b, use_container_width=True)
            else:
                col_b.info("Zaman trendi analiz verisi bulunamadı.")
                
            st.markdown("---")
            st.subheader(f"🔍 Firma Sipariş Listesi Barkod Doğrulama")
            search_barcode = st.text_input("Sorgulanacak Barkod No:", placeholder="Aramak istediğiniz ürün barkodunu giriniz...").strip()
            display_df = firma_df.copy()
            
            if search_barcode:
                search_res = display_df[display_df['BARKOD'].str.contains(search_barcode, case=False, na=False)]
                if not search_res.empty:
                    st.success(f"✅ Barkod Doğrulandı! Seçili firmaya ait kayıtlarda {len(search_res)} adet eşleşme sağlandı.")
                    display_df = search_res
                else:
                    st.error("❌ Barkod Bulunamadı! Bu firmanın sipariş kayıtlarında girilen barkoda rastlanmadı.")
                    
            st.markdown(f"**Detaylı Sipariş Dökümü:**")
            display_df_formatted = display_df.copy()
            display_df_formatted['FIYAT'] = display_df_formatted['FIYAT'].map('{:,.2f} $'.format)
            display_df_formatted['TOPLAM_SERMAYE'] = display_df_formatted['TOPLAM_SERMAYE'].map('{:,.2f} $'.format)
            
            drop_cols = [c for c in ['ORIJINAL_FIYAT', 'PARA_BIRIMI'] if c in display_df_formatted.columns]
            if drop_cols:
                display_df_formatted = display_df_formatted.drop(columns=drop_cols)
                
            st.dataframe(display_df_formatted, use_container_width=True)

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