import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import io
import openpyxl
import re
import datetime
import time

# --- AYARLAR VE SİBER ARKA PLAN ---
st.set_page_config(layout="wide", page_title="ZORE Uzay Komuta Paneli")

# Veri bağlantıları ve tab yapıları eksiksiz korunuyor
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

CYBER_PALETTE = ['#00f3ff', '#ff00ff', '#00ff66', '#ffb000', '#7000ff', '#ff0055', '#00ffcc', '#ff5500']

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
    except: pass
    return rates

rates = get_live_rates()

def strict_date_string_parser(val):
    if pd.isna(val) or val == "": return "BELİRTİLMEMİŞ"
    if hasattr(val, 'strftime'): return val.strftime('%Y-%m-%d')
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
        if col in df.columns: df[col] = df[col].apply(strict_date_string_parser)
            
    available_cols = [c for c in EXPECTED_COLUMNS if c in df.columns]
    df = df[available_cols].copy()
    df = df.dropna(how='all')
    
    if 'ADET' in df.columns: df['ADET'] = pd.to_numeric(df['ADET'], errors='coerce').fillna(0)
    
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
            
            if 'CATHY' in firma_name or any(sym in val_str for sym in yuan_symbols) or any(sym in val_str.upper() for sym in yuan_symbols):
                currency = 'CNY'
                sym_char = '¥'
            elif any(sym in val_str for sym in euro_symbols) or any(sym in val_str.upper() for sym in euro_symbols):
                currency = 'EUR'
                sym_char = '€'
            
            for clean_target in yuan_symbols + euro_symbols + ['$', 'usd', 'USD']: val_str = val_str.replace(clean_target, '')
            val_str = val_str.strip()
            
            if ',' in val_str and '.' in val_str:
                if val_str.find(',') > val_str.find('.'): val_str = val_str.replace('.', '').replace(',', '.')
                else: val_str = val_str.replace(',', '')
            elif ',' in val_str: val_str = val_str.replace(',', '.')
                
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
        except: continue
    full_df = pd.concat(all_data_list, ignore_index=True) if all_data_list else pd.DataFrame()
    if not full_df.empty:
        full_df['SIPARIS_AY'] = full_df['SIPARIS_TARIHI'].apply(lambda x: "Bilinmeyen Dönem" if x == "BELİRTİLMEMİŞ" or len(x) < 7 else x[:7])
    return full_df, pool

df_dashboard, data_pool = get_all_data(rates)

def apply_cosmic_style(fig, chart_type="bar"):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(10,14,26,1)",
        plot_bgcolor="rgba(15,22,42,1)",
        transition={'duration': 400, 'easing': 'back-out'}, # Grafik geçiş ivmesi hızlandırıldı (Akan etki için)
        modebar_remove=['zoom', 'pan', 'select', 'lasso2d'],
        font=dict(family="Courier New, monospace", color="#00f3ff", size=12)
    )
    if chart_type == "line":
        fig.update_layout(hovermode="x unified")
        fig.update_traces(line=dict(shape='spline', width=3), marker=dict(size=6))
    return fig

# --- SIDEBAR NAVİGASYON ---
st.sidebar.title("🛸 ZORE KOMUTA MERKEZİ")
page = st.sidebar.radio("Sistem Ekranları", ["1. Genel Dashboard", "2. Firma Bazlı Analiz", "3. Ham Veri"])

if page == "1. Genel Dashboard":
    st.header("🌌 Galaktik Canlı Veri Terminali")
    
    if df_dashboard.empty:
        st.error("Veri matrisi boş.")
    else:
        # Üst Sabit Metrik Panelleri
        m1, m2, m3 = st.columns(3)
        with m1: st.markdown(f"<div style='border:1px solid #00f3ff; padding:15px; border-radius:8px; background-color:#0a0e1a;'><p style='color:#00f3ff; margin:0;'>MÜHİMMAT HACMİ (ADET)</p><h2 style='color:#ffffff; margin:5px 0;'>{int(df_dashboard['ADET'].sum()):,}</h2></div>", unsafe_allow_html=True)
        with m2: st.markdown(f"<div style='border:1px solid #ff00ff; padding:15px; border-radius:8px; background-color:#0a0e1a;'><p style='color:#ff00ff; margin:0;'>TOPLAM ENJEKTE SERMAYE</p><h2 style='color:#ffffff; margin:5px 0;'>{df_dashboard['TOPLAM_SERMAYE'].sum():,.2f} $</h2></div>", unsafe_allow_html=True)
        with m3: st.markdown(f"<div style='border:1px solid #00ff66; padding:15px; border-radius:8px; background-color:#0a0e1a;'><p style='color:#00ff66; margin:0;'>AKTİF ODAKLAR (FİRMA)</p><h2 style='color:#ffffff; margin:5px 0;'>{df_dashboard['FIRMA'].nunique()}</h2></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Sabit Statik Grafikler (Üst Bölüm)
        g1, g2 = st.columns(2)
        top_sips = df_dashboard.groupby('MALIN CINSI')['ADET'].sum().nlargest(10).reset_index()
        fig1 = px.bar(top_sips, x='MALIN CINSI', y='ADET', title="1. En Yüksek Adetli 10 Sevkiyat", color_discrete_sequence=['#00f3ff'])
        g1.plotly_chart(apply_cosmic_style(fig1, "bar"), use_container_width=True)
        
        top_money = df_dashboard.groupby('MALIN CINSI')['TOPLAM_SERMAYE'].sum().nlargest(10).reset_index()
        fig2 = px.bar(top_money, x='MALIN CINSI', y='TOPLAM_SERMAYE', title="2. En Ağır Sermaye Yükü Olan 10 Ürün", color_discrete_sequence=['#ff00ff'])
        g2.plotly_chart(apply_cosmic_style(fig2, "bar"), use_container_width=True)

        st.markdown("---")
        st.subheader("🎬 Canlı Sinematik Döngü Koridoru (Otomatik Film Modu)")

        # --- 🚀 İŞTE SIRRIMIZ: SİZ HİÇBİR ŞEYE BASMADAN ARKA PLANDA SÜREKLİ DÖNEN FRAGMENT MOTORU ---
        # run_every=1.0 saniyede bir bu aşağıdaki fonksiyonu tetikler ve grafikleri canlı video gibi oynatır.
        @st.fragment(run_every=1.0)
        def render_movie_loop_charts():
            df_anim = df_dashboard[df_dashboard['SIPARIS_AY'].str.startswith('2026', na=False)].copy()
            aylar = sorted(df_anim['SIPARIS_AY'].unique())
            
            if not aylar:
                st.info("Canlı döngü için 2026 yılı verisi bulunamadı.")
                return
            
            # Kare (Frame) sayacını session_state üzerinde tutup her saniye bir ileri sarıyoruz
            if 'loop_frame' not in st.session_state:
                st.session_state.loop_frame = 0
                
            current_idx = st.session_state.loop_frame % len(aylar)
            aktif_ay = aylar[current_idx]
            
            # Bir sonraki saniye için kareyi arttırıyoruz (Sonsuz döngü)
            st.session_state.loop_frame += 1
            
            # Ekrandaki neon zaman göstergesi
            st.markdown(f"📡 <span style='color:#00f3ff; font-size:18px; font-family:monospace; font-weight:bold;'>CANLI TARAMA DÖNEMİ: {aktif_ay}</span> &nbsp;&nbsp;&nbsp;&nbsp; [ 🟢 SİSTEM SÜREKLİ DÖNGÜDE - FİLM MODU AKTİF ]", unsafe_allow_html=True)
            
            loop_col1, loop_col2 = st.columns(2)
            
            # --- GRAFİK 3: GERÇEK ZAMANLI KUMULATİF AKAN YARIŞ (VİDEO GİBİ SÜREKLİ DEĞİŞİR) ---
            top_10_overall = df_dashboard.groupby('FIRMA')['TOPLAM_SERMAYE'].sum().nlargest(10).index
            
            # Seçilen aktif aya kadar olan tüm birikimli verileri filtrele (Barların büyüme animasyonu için)
            df_filtered_up_to_now = df_anim[df_anim['SIPARIS_AY'] <= aktif_ay]
            df_race_live = df_filtered_up_to_now.groupby('FIRMA')['TOPLAM_SERMAYE'].sum().reset_index()
            
            # İlk 10 firmayı koru ve sıfırları doldur
            df_race_live = df_race_live[df_race_live['FIRMA'].isin(top_10_overall)]
            missing_firmas = pd.DataFrame({'FIRMA': [f for f in top_10_overall if f not in df_race_live['FIRMA'].values], 'TOPLAM_SERMAYE': 0.0})
            df_race_live = pd.concat([df_race_live, missing_firmas], ignore_index=True)
            
            # Maksimum X ekseni sınırını kilitle ki barlar titremesin, film gibi aksın
            max_x = df_anim.groupby(['SIPARIS_AY', 'FIRMA'])['TOPLAM_SERMAYE'].sum().unstack(fill_value=0).cumsum(axis=0).max().max()
            
            fig3_live = px.bar(
                df_race_live,
                x='TOPLAM_SERMAYE',
                y='FIRMA',
                orientation='h',
                color='FIRMA',
                range_x=[0, max_x * 1.05],
                category_orders={'FIRMA': list(top_10_overall)[::-1]},
                color_discrete_sequence=CYBER_PALETTE,
                title=f"3. Firmaların Aylık Birikimli Güç Yarışı (Durum: {aktif_ay})"
            )
            fig3_live.update_layout(showlegend=False)
            loop_col1.plotly_chart(apply_cosmic_style(fig3_live, "bar"), use_container_width=True)
            
            # --- GRAFİK 4: HER SANİYE ŞEKİL DEĞİŞTİREN RADAR DONUT (VİDEO GİBİ MORPH OLUR) ---
            df_pie_month = df_anim[df_anim['SIPARIS_AY'] == aktif_ay]
            top_tur_month = df_pie_month.groupby('TUR')['TOPLAM_SERMAYE'].sum().nlargest(10).reset_index()
            
            fig4_live = go.Figure(data=[go.Pie(
                labels=top_tur_month['TUR'] if not top_tur_month.empty else ["VERİ AKIŞI YOK"],
                values=top_tur_month['TOPLAM_SERMAYE'] if not top_tur_month.empty else [1],
                hole=0.6,
                marker=dict(colors=CYBER_PALETTE, line=dict(color='#0a0e1a', width=3)),
                hoverinfo='label+percent+value',
                textinfo='percent'
            )])
            fig4_live.update_layout(
                title=f"4. {aktif_ay} Dönemi Tür Dağılım Matrisi",
                annotations=[dict(text='ZORE<br>RADAR', x=0.5, y=0.5, font_size=14, font_color="#00f3ff", showarrow=False)]
            )
            loop_col2.plotly_chart(apply_cosmic_style(fig4_live, "pie"), use_container_width=True)

        # Otomatik döngü alanını çalıştır
        render_movie_loop_charts()

        # Alt Bölüm Trend Grafikleri (Oval Akıcı Spline Hatlar)
        st.markdown("---")
        df_2026 = df_dashboard[df_dashboard['SIPARIS_AY'].str.startswith('2026', na=False)].copy().sort_values('SIPARIS_AY')
        g5, g6 = st.columns(2)
        
        top_5_firmalar = df_2026.groupby('FIRMA')['TOPLAM_SERMAYE'].sum().nlargest(5).index
        df_trend_firma = df_2026[df_2026['FIRMA'].isin(top_5_firmalar)]
        trend_firma = df_trend_firma.groupby(['SIPARIS_AY', 'FIRMA'])['TOPLAM_SERMAYE'].sum().reset_index()
        fig5 = px.line(trend_firma, x='SIPARIS_AY', y='TOPLAM_SERMAYE', color='FIRMA', title="5. Üst Düzey 5 Gücün Aylık İlerleme Spektrumu", markers=True, color_discrete_sequence=CYBER_PALETTE)
        fig5.update_layout(xaxis_type='category')
        g5.plotly_chart(apply_cosmic_style(fig5, "line"), use_container_width=True)
        
        top_5_turler = df_2026.groupby('TUR')['TOPLAM_SERMAYE'].sum().nlargest(5).index
        df_trend_tur = df_2026[df_2026['TUR'].isin(top_5_turler)]
        trend_tur = df_trend_tur.groupby(['SIPARIS_AY', 'TUR'])['TOPLAM_SERMAYE'].sum().reset_index()
        fig6 = px.line(trend_tur, x='SIPARIS_AY', y='TOPLAM_SERMAYE', color='TUR', title="6. Sektörel Kategorilerin Zamansal Akış Grafiği", markers=True, color_discrete_sequence=CYBER_PALETTE)
        fig6.update_layout(xaxis_type='category')
        g6.plotly_chart(apply_cosmic_style(fig6, "line"), use_container_width=True)

        g7, g8 = st.columns(2)
        trend_total = df_2026.groupby('SIPARIS_AY')['TOPLAM_SERMAYE'].sum().reset_index()
        fig7 = px.line(trend_total, x='SIPARIS_AY', y='TOPLAM_SERMAYE', title="7. Kümülatif Aylık Finansal Enerji Akışı", markers=True, color_discrete_sequence=['#00ff66'])
        fig7.update_layout(xaxis_type='category')
        g7.plotly_chart(apply_cosmic_style(fig7, "line"), use_container_width=True)
        
        df_barkod_temiz = df_dashboard[(df_dashboard['BARKOD'] != "BELİRTİLMEMİŞ") & (df_dashboard['BARKOD'].str.strip() != "")]
        top_barcode = df_barkod_temiz.groupby('BARKOD').agg({'ADET': 'sum', 'MALIN CINSI': 'first'}).nlargest(10, 'ADET').reset_index()
        fig8 = px.bar(top_barcode, x='MALIN CINSI', y='ADET', title="8. Gerçek Barkod Kırılımında Top 10 Lojistik Odak", text='BARKOD', color_discrete_sequence=['#7000ff'])
        g8.plotly_chart(apply_cosmic_style(fig8, "bar"), use_container_width=True)

# Diğer sayfalar (Sayfa 2 ve Sayfa 3 şifreleri korunmuştur)
elif page == "2. Firma Bazlı Analiz":
    st.header("🏢 Hedef Odak Merkez Laboratuvarı")
    firmalar = sorted([str(f) for f in df_dashboard['FIRMA'].unique() if str(f) != "BELİRTİLMEMİŞ"])
    if not firmalar: st.warning("Aktör bulunamadı.")
    else:
        selected_firma = st.selectbox("Sinyal Alınacak Firmayı Seçin", firmalar)
        firma_df = df_dashboard[df_dashboard['FIRMA'] == selected_firma]
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f"<div style='border:1px solid #00f3ff; padding:10px; border-radius:6px;'><p style='color:#00f3ff; margin:0;'>ADET</p><h3 style='margin:5px 0;'>{int(firma_df['ADET'].sum()):,}</h3></div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div style='border:1px solid #ff00ff; padding:10px; border-radius:6px;'><p style='color:#ff00ff; margin:0;'>SERMAYE</p><h3 style='margin:5px 0;'>{firma_df['TOPLAM_SERMAYE'].sum():,.2f} $</h3></div>", unsafe_allow_html=True)
        tur_counts = firma_df.groupby('TUR')['ADET'].sum()
        en_cok_tur = tur_counts.idxmax() if not tur_counts.empty and tur_counts.sum() > 0 else "Yok"
        with c3: st.markdown(f"<div style='border:1px solid #00ff66; padding:10px; border-radius:6px;'><p style='color:#00ff66; margin:0;'>DOMİNANT TÜR</p><h3 style='margin:5px 0;'>{en_cok_tur}</h3></div>", unsafe_allow_html=True)
        
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
            fig_a = go.Figure(data=[go.Pie(labels=firma_df_pie['TUR_GRAFIK'], values=firma_df_pie['TOPLAM_SERMAYE'], hole=0.55, marker=dict(colors=CYBER_PALETTE, line=dict(color='#0a0e1a', width=2)))])
            fig_a.update_layout(title=f"{selected_firma} Portföy Spektrumu")
            col_a.plotly_chart(apply_cosmic_style(fig_a, "pie"), use_container_width=True)
        
        trend_data_all = firma_df.groupby('SIPARIS_AY')['TOPLAM_SERMAYE'].sum().reset_index().sort_values('SIPARIS_AY')
        if not trend_data_all.empty and trend_data_all['TOPLAM_SERMAYE'].sum() > 0:
            fig_b = px.bar(trend_data_all, x='SIPARIS_AY', y='TOPLAM_SERMAYE', title=f"{selected_firma} Periyodik Yüklenme Grafiği", color_discrete_sequence=['#00f3ff'])
            fig_b.update_layout(xaxis_type='category')
            col_b.plotly_chart(apply_cosmic_style(fig_b, "bar"), use_container_width=True)
            
        st.markdown("---")
        search_barcode = st.text_input("Sistemde Kontrol Edilecek Barkod Kimliği:", placeholder="Kayıt taraması için barkod girin...").strip()
        display_df = firma_df.copy()
        if search_barcode:
            search_res = display_df[display_df['BARKOD'].str.contains(search_barcode, case=False, na=False)]
            if not search_res.empty:
                st.success(f"🚀 VERİ DOĞRULANDI: {len(search_res)} siber kayıt izole edildi!")
                display_df = search_res  
            else: st.error("🚨 SİNYAL YOK: Barkod aktörün sicilinde mevcut değil.")
        
        display_df_formatted = display_df.copy()
        display_df_formatted['FIYAT'] = display_df_formatted['FIYAT'].map('{:,.2f} $'.format)
        display_df_formatted['TOPLAM_SERMAYE'] = display_df_formatted['TOPLAM_SERMAYE'].map('{:,.2f} $'.format)
        drop_cols = [c for c in ['ORIJINAL_FIYAT', 'PARA_BIRIMI'] if c in display_df_formatted.columns]
        if drop_cols: display_df_formatted = display_df_formatted.drop(columns=drop_cols)
        st.dataframe(display_df_formatted.sort_values(by='SIPARIS_TARIHI', ascending=False), use_container_width=True, hide_index=True)

elif page == "3. Ham Veri":
    st.header("📋 Ana Veri Havuz Odası")
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
                if drop_cols: raw_display = raw_display.drop(columns=drop_cols)
                st.dataframe(raw_display, use_container_width=True, hide_index=True)