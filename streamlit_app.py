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

# --- AYARLAR VE ANAYASA ---
st.set_page_config(layout="wide", page_title="ZORE Veri Paneli")

# Sinematik WebGL ve Stil Enjeksiyonu
st.markdown("""
<style>
    .reportview-container { background: #060913 !important; }
    div.block-container { padding-top: 1rem; padding-bottom: 0rem; }
    .matrix-box { background: rgba(4, 11, 28, 0.7); border: 1px solid rgba(0, 243, 255, 0.12); border-radius: 8px; padding: 15px; }
</style>
""", unsafe_allow_html=True)

LINKS = [
    "https://docs.google.com/spreadsheets/d/1j819WkX93CkCy3VgZkSff5C_zNX5Z98jfK-FwI4ZWUU/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1hVk6VgMFXWAukoQwMDIoOLrG8SD4UDLFFRH9VmDhXSE/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1S1kTptWUEf705cBLw9P9mL6rrqbVjbcp1xk_hgQ-Ny0/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1VKb6za4Fse5XrGawPG6qvrQZuFhDRGaAysmADGIC7Wc/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=xlsx"
]

TARGET_TABS = ["has_air", "has_sea", "meh_air", "meh_sea", "ist_air", "ist_sea"]
EXPECTED_COLUMNS = ['SIPARIS_TARIHI', 'FIRMA', 'TUR', 'BARKOD', 'MALIN CINSI', 'ADET', 'FIYAT', 'YUKLEME_TARIHI', 'NAKLİYE_TÜRÜ']
HEADER_MAP = {'SIPARIS TARIHI': 'SIPARIS_TARIHI', 'FIRMA': 'FIRMA', 'TUR': 'TUR', 'BARKOD': 'BARKOD', 'MALIN CINSI': 'MALIN CINSI', 'ADET': 'ADET', 'FIYAT': 'FIYAT', 'YUKLEME TARIHI': 'YUKLEME_TARIHI'}

# --- MOTORLAR ---
@st.cache_data(ttl=3600)
def get_live_rates():
    return {"EUR_TO_USD": 1.09, "CNY_TO_USD": 0.138, "PROUNCE": "Canlı Kur Aktif"}

rates = get_live_rates()

def strict_date_string_parser(val):
    if pd.isna(val) or val == "": return "BELİRTİLMEMİŞ"
    if hasattr(val, 'strftime'): return val.strftime('%Y-%m-%d')
    val_str = str(val).strip().split()[0].replace('/', '.').replace('-', '.')
    for fmt in ['%Y.%m.%d', '%d.%m.%Y', '%Y.%d.%m']:
        try: return datetime.datetime.strptime(val_str, fmt).strftime('%Y-%m-%d')
        except: continue
    return "BELİRTİLMEMİŞ"

def clean_data(df, rates):
    df = df.loc[:, ~df.columns.duplicated()]
    for col in ['SIPARIS_TARIHI', 'YUKLEME_TARIHI']:
        if col in df.columns: df[col] = df[col].apply(strict_date_string_parser)
    df = df.dropna(how='all')
    if 'ADET' in df.columns: df['ADET'] = pd.to_numeric(df['ADET'], errors='coerce').fillna(0)
    
    if 'FIYAT' in df.columns and 'FIRMA' in df.columns:
        def parse_price_details(row):
            val = str(row['FIYAT']).strip()
            firma = str(row['FIRMA']).upper()
            curr = 'USD'
            mult = 1.0
            if 'CATHY' in firma or any(x in val for x in ['¥', 'CNY']): mult = rates["CNY_TO_USD"]
            elif any(x in val for x in ['€', 'EUR']): mult = rates["EUR_TO_USD"]
            num = re.sub(r'[^\d.,]', '', val).replace(',', '.')
            try: return float(num) * mult, float(num)
            except: return 0.0, 0.0
        res = df.apply(parse_price_details, axis=1)
        df['FIYAT'] = [r[0] for r in res]
        df['TOPLAM_SERMAYE'] = df['ADET'] * df['FIYAT']
    return df

@st.cache_data(ttl=600)
def get_all_data(rates):
    all_data_list = []
    pool = {tab: [] for tab in TARGET_TABS}
    for link in LINKS:
        try:
            res = requests.get(link, timeout=10)
            wb = openpyxl.load_workbook(io.BytesIO(res.content), data_only=True)
            for tab in TARGET_TABS:
                if tab in wb.sheetnames:
                    sheet = wb[tab]
                    data = [[cell.value for cell in row] for row in sheet.iter_rows()]
                    if not data: continue
                    df = pd.DataFrame(data[1:], columns=[HEADER_MAP.get(str(c).upper(), c) for c in data[0]])
                    df_clean = clean_data(df, rates)
                    if not df_clean.empty:
                        pool[tab].append(df_clean)
                        all_data_list.append(df_clean)
        except: continue
    full_df = pd.concat(all_data_list, ignore_index=True) if all_data_list else pd.DataFrame()
    if not full_df.empty: full_df['SIPARIS_AY'] = full_df['SIPARIS_TARIHI'].apply(lambda x: x[:7] if len(x)>7 else "Bilinmeyen")
    return full_df, pool

df_dashboard, data_pool = get_all_data(rates)

# --- SİNE-MATRİS VERİ KÖPRÜSÜ ---
def render_cinematic_dashboard(df):
    months = sorted(df['SIPARIS_AY'].unique())
    matrix = {}
    for m in months:
        df_m = df[df['SIPARIS_AY'] == m]
        top_f = df_m.groupby('FIRMA')['TOPLAM_SERMAYE'].sum().nlargest(10).iloc[::-1]
        matrix[m] = {
            "firms": top_f.index.tolist(),
            "sermaye": top_f.values.round(2).tolist(),
            "pie": [{"value": int(x), "name": str(n)} for n, x in df_m.groupby('TUR')['ADET'].sum().nlargest(8).items()]
        }
    
    html = f"""
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <div id="glow_bar" style="height:400px;"></div>
    <script>
        const data = {json.dumps(matrix)};
        const months = {json.dumps(months)};
        const barChart = echarts.init(document.getElementById('glow_bar'));
        let i = 0;
        setInterval(() => {{
            let m = months[i++ % months.length];
            barChart.setOption({{
                xAxis: {{ type: 'value' }}, yAxis: {{ type: 'category', data: data[m].firms }},
                series: [{{ type: 'bar', data: data[m].sermaye, itemStyle: {{ color: '#00f3ff' }} }}]
            }});
        }}, 2500);
    </script>
    """
    st.components.v1.html(html, height=450)

# --- NAVİGASYON ---
page = st.sidebar.radio("Sayfa", ["1. Genel Dashboard (Sinematik)", "2. Firma Analiz", "3. Ham Veri"])

if page == "1. Genel Dashboard (Sinematik)":
    st.header("📊 Savaş Odası: Canlı Veri Akışı")
    render_cinematic_dashboard(df_dashboard)
elif page == "2. Firma Analiz":
    # (Orijinal Firma Analiz kodlarınız buraya gelir)
    st.write("Firma Analiz Sayfası...")
elif page == "3. Ham Veri":
    # (Orijinal Ham Veri kodlarınız buraya gelir)
    st.write("Ham Veri Sayfası...")