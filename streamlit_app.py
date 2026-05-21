import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import io
import openpyxl

# --- AYARLAR VE ANAYASA ---
st.set_page_config(layout="wide", page_title="ZORE Veri Paneli")

# 1. KURAL: Veri çekme ve temizleme mantığı korunacak (Anayasa)
LINKS = [
    "https://docs.google.com/spreadsheets/d/1j819WkX93CkCy3VgZkSff5C_zNX5Z98jfK-FwI4ZWUU/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1hVk6VgMFXWAukoQwMDIoOLrG8SD4UDLFFRH9VmDhXSE/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1S1kTptWUEf705cBLw9P9mL6rrqbVjbcp1xk_hgQ-Ny0/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1VKb6za4Fse5XrGawPG6qvrQZuFhDRGaAysmADGIC7Wc/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=xlsx"
]

TARGET_TABS = ["has_air", "has_sea", "meh_air", "meh_sea", "ist_air", "ist_sea"]
EXPECTED_COLUMNS = ['SIPARIS_TARIHI', 'FIRMA', 'TUR', 'BARKOD', 'MALIN CINSI', 'ADET', 'FIYAT', 'YUKLEME_TARIHI', 'NAKLİYE_TÜRÜ']

# Çoklu Excel dosyalarında kolon kaymalarını sıfırlayan akıllı haritalama sözlüğü
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

def clean_data(df, rates):
    df = df.loc[:, ~df.columns.duplicated()]
    
    # Gün ve ay formatının kaymasını önlemek için dayfirst=True zorunlu kılındı
    for col in ['SIPARIS_TARIHI', 'YUKLEME_TARIHI']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce').dt.date
            
    available_cols = [c for c in EXPECTED_COLUMNS if c in df.columns]
    df = df[available_cols].copy()
    df = df.dropna(how='all')
    
    if 'ADET' in df.columns:
        df['ADET'] = pd.to_numeric(df['ADET'], errors='coerce').fillna(0)
    
    # Çoklu Para Birimi ve Kur Dönüşüm Yönetimi
    if 'FIYAT' in df.columns and 'FIRMA' in df.columns:
        def parse_price_details(row):
            val = row['FIYAT']
            firma_name = str(row['FIRMA']).upper()
            if pd.isna(val):
                return 0.0, 0.0, '$'
            
            val_str = str(val).strip()
            currency = 'USD'
            sym_char = '$'
            
            yuan_symbols = ['¥', '￥', 'CNY', 'RMB', '元']
            euro_symbols = ['€', 'EUR']
            
            # Firma kontrolü veya hücre formatı bazlı akıllı tespit
            if 'CATHY' in firma_name or any(sym in val_str for sym in yuan_symbols) or any(sym in val_str.upper() for sym in yuan_symbols):
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
                    if pd.isna(x):
                        return "BELİRTİLMEMİŞ"
                    if isinstance(x, (int, float)):
                        try:
                            if x == int(x):
                                return str(int(x))
                            return str(x)
                        except:
                            return str(x)
                    s = str(x).strip()
                    if s.endswith('.0'):
                        s = s[:-2]
                    if '.' in s:
                        try:
                            f = float(s)
                            if f == int(f):
                                return str(int(f))
                        except:
                            pass
                    if s in ['nan', 'None', '']:
                        return "BELİRTİLMEMİŞ"
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
            if response.status_code != 200:
                continue
            
            wb = openpyxl.load_workbook(io.BytesIO(response.content), data_only=True)
            
            for tab in TARGET_TABS:
                if tab in wb.sheetnames:
                    sheet = wb[tab]
                    rows = list(sheet.iter_rows(values_only=False))
                    if not rows:
                        continue
                    
                    # Kolon adlarını Türkçeden arındırıp standardize eden temizlik motoru
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
                        if all(cell.value is None for cell in row):
                            continue
                            
                        row_data = []
                        for idx, cell in enumerate(row):
                            if idx >= len(headers): 
                                break
                            val = cell.value
                            
                            if idx == fiyat_idx and val is not None:
                                fmt = str(cell.number_format).upper()
                                if any(x in fmt for x in ['¥', '￥', 'CNY', '元', '804']):
                                    val = f"¥{val}"
                                elif any(x in fmt for x in ['€', 'EUR']):
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
        full_df['SIPARIS_AY'] = pd.to_datetime(full_df['SIPARIS_TARIHI'], errors='coerce').dt.to_period('M').astype(str)
        full_df['SIPARIS_AY'] = full_df['SIPARIS_AY'].replace({'NaT': 'Bilinmeyen Dönem'})
        
    return full_df, pool

df_dashboard, data_pool = get_all_data(rates)

# --- NAVİGASYON VE DÖVİZ BİLGİSİ ---
st.sidebar.title("ZORE YÖNETİM PANELİ")
st.sidebar.markdown(f"**Döviz Durumu:** `{rates['PROUNCE']}`")
st.sidebar.text(f"1 EUR = {rates['EUR_TO_USD']:.4f} $")
st.sidebar.text(f"1 CNY = {rates['CNY_TO_USD']:.4f} $")
st.sidebar.markdown("---")

page = st.sidebar.radio("Sayfa Seçimi", ["1. Genel Dashboard", "2. Firma Bazlı Analiz", "3. Ham Veri"])

# --- SAYFA 1: GENEL DASHBOARD ---
if page == "1. Genel Dashboard":
    st.header("📊 Genel Dashboard")
    
    if df_dashboard.empty:
        st.error("Veri bulunamadı.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Sipariş Adedi", f"{int(df_dashboard['ADET'].sum()):,}")
        c2.metric("Toplam Sermaye Yatırımı (USD)", f"{df_dashboard['TOPLAM_SERMAYE'].sum():,.2f} $")
        c3.metric("Çalışılan Firma Sayısı", df_dashboard['FIRMA'].nunique())

        st.markdown("---")
        
        g1, g2 = st.columns(2)
        top_sips = df_dashboard.groupby('MALIN CINSI')['ADET'].sum().nlargest(10).reset_index()
        fig1 = px.bar(top_sips, x='MALIN CINSI', y='ADET', title="1. En Çok Sipariş Edilen 10 Ürün (Adet)", color='ADET')
        g1.plotly_chart(fig1, use_container_width=True)
        
        top_money = df_dashboard.groupby('MALIN CINSI')['TOPLAM_SERMAYE'].sum().nlargest(10).reset_index()
        fig2 = px.bar(top_money, x='MALIN CINSI', y='TOPLAM_SERMAYE', title="2. En Çok Sermaye Yatırılan 10 Ürün ($)", color='TOPLAM_SERMAYE')
        g2.plotly_chart(fig2, use_container_width=True)

        g3, g4 = st.columns(2)
        top_firma = df_dashboard.groupby('FIRMA')['TOPLAM_SERMAYE'].sum().nlargest(10).reset_index()
        fig3 = px.pie(top_firma, values='TOPLAM_SERMAYE', names='FIRMA', title="3. Harcama Yapılan İlk 10 Firma", hole=0.4)
        fig3.update_traces(textinfo='label+percent')
        g3.plotly_chart(fig3, use_container_width=True)
        
        top_tur = df_dashboard.groupby('TUR')['TOPLAM_SERMAYE'].sum().nlargest(10).reset_index()
        fig4 = px.pie(top_tur, values='TOPLAM_SERMAYE', names='TUR', title="4. Tür Bazlı Harcama Dağılımı (USD)", hole=0.4)
        fig4.update_traces(textinfo='label+percent')
        g4.plotly_chart(fig4, use_container_width=True)

        df_2026 = df_dashboard[df_dashboard['SIPARIS_AY'].str.startswith('2026', na=False)].copy().sort_values('SIPARIS_AY')

        g5, g6 = st.columns(2)
        top_5_firmalar = df_2026.groupby('FIRMA')['TOPLAM_SERMAYE'].sum().nlargest(5).index
        df_trend_firma = df_2026[df_2026['FIRMA'].isin(top_5_firmalar)]
        trend_firma = df_trend_firma.groupby(['SIPARIS_AY', 'FIRMA'])['TOPLAM_SERMAYE'].sum().reset_index().sort_values('SIPARIS_AY')
        fig5 = px.line(trend_firma, x='SIPARIS_AY', y='TOPLAM_SERMAYE', color='FIRMA', title="5. Aylık Firma Harcama Trendi (En Büyük 5 Firma)", markers=True)
        g5.plotly_chart(fig5, use_container_width=True)
        
        top_5_turler = df_2026.groupby('TUR')['TOPLAM_SERMAYE'].sum().nlargest(5).index
        df_trend_tur = df_2026[df_2026['TUR'].isin(top_5_turler)]
        trend_tur = df_trend_tur.groupby(['SIPARIS_AY', 'TUR'])['TOPLAM_SERMAYE'].sum().reset_index().sort_values('SIPARIS_AY')
        fig6 = px.line(trend_tur, x='SIPARIS_AY', y='TOPLAM_SERMAYE', color='TUR', title="6. Aylık Tür Harcama Trendi (En Büyük 5 Tür)", markers=True)
        g6.plotly_chart(fig6, use_container_width=True)

        g7, g8 = st.columns(2)
        trend_total = df_2026.groupby('SIPARIS_AY')['TOPLAM_SERMAYE'].sum().reset_index().sort_values('SIPARIS_AY')
        fig7 = px.line(trend_total, x='SIPARIS_AY', y='TOPLAM_SERMAYE', title="7. Aylık Toplam Sermaye Akışı ($)", markers=True)
        g7.plotly_chart(fig7, use_container_width=True)
        
        df_barkod_temiz = df_dashboard[(df_dashboard['BARKOD'] != "BELİRTİLMEMİŞ") & (df_dashboard['BARKOD'].str.strip() != "")]
        top_barcode = df_barkod_temiz.groupby('BARKOD').agg({'ADET': 'sum', 'MALIN CINSI': 'first'}).nlargest(10, 'ADET').reset_index()
        fig8 = px.bar(top_barcode, x='MALIN CINSI', y='ADET', title="8. Barkod Bazlı Top 10 Ürün (Gerçek Barkodlar)", text='BARKOD', color='ADET')
        g8.plotly_chart(fig8, use_container_width=True)

# --- SAYFA 2: FİRMA BAZLI ANALİZ ---
elif page == "2. Firma Bazlı Analiz":
    st.header("🏢 Firma Bazlı Analiz")
    
    if df_dashboard.empty:
        st.error("Veri bulunamadı.")
    else:
        firmalar = sorted([str(f) for f in df_dashboard['FIRMA'].unique() if str(f) != "BELİRTİLMEMİŞ"])
        
        if not firmalar:
            st.warning("Analiz edilecek geçerli bir firma kaydı bulunamadı.")
        else:
            selected_firma = st.selectbox("Analiz edilecek firmayı seçin", firmalar)
            firma_df = df_dashboard[df_dashboard['FIRMA'] == selected_firma]
            
            c1, c2, c3 = st.columns(3)
            c1.metric(f"{selected_firma} Toplam Alım", f"{int(firma_df['ADET'].sum()):,}")
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
                col_a.info("Grafik için yeterli ciro verisi yok.")
            
            firma_df_2026 = firma_df[firma_df['SIPARIS_AY'].str.startswith('2026', na=False)].copy().sort_values('SIPARIS_AY')
            trend_data = firma_df_2026.groupby('SIPARIS_AY')['TOPLAM_SERMAYE'].sum().reset_index()
            
            if not trend_data.empty and trend_data['TOPLAM_SERMAYE'].sum() > 0:
                fig_b = px.bar(trend_data, x='SIPARIS_AY', y='TOPLAM_SERMAYE', title=f"{selected_firma} 2026 Yılı Aylık Alım Trendi ($)")
                col_b.plotly_chart(fig_b, use_container_width=True)
            else:
                col_b.info("2026 yılına ait zaman trendi grafik verisi bulunamadı.")
            
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
            
            # BLANKET YERİNE AKILLI SATIR BAZLI PARA BİRİMİ BASTIRMA MOTORU
            display_df_formatted['FIYAT'] = display_df.apply(lambda r: f"{r['ORIJINAL_FIYAT']:,.2f} {r['PARA_BIRIMI']}" if 'ORIJINAL_FIYAT' in r else f"{r['FIYAT']:,.2f} $", axis=1)
            display_df_formatted['TOPLAM_SERMAYE'] = display_df_formatted['TOPLAM_SERMAYE'].map('{:,.2f} $'.format)
            
            # Orijinal ara takip sütunlarını son tabloda kalabalık yapmasın diye gizleyelim
            drop_cols = [c for c in ['ORIJINAL_FIYAT', 'PARA_BIRIMI'] if c in display_df_formatted.columns]
            if drop_cols:
                display_df_formatted = display_df_formatted.drop(columns=drop_cols)
                
            st.dataframe(display_df_formatted.sort_values(by='SIPARIS_TARIHI', ascending=False), use_container_width=True, hide_index=True)

# --- SAYFA 3: HAM VERİ ---
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
                raw_display['FIYAT'] = combined_df.apply(lambda r: f"{r['ORIJINAL_FIYAT']:,.2f} {r['PARA_BIRIMI']}" if 'ORIJINAL_FIYAT' in r else f"{r['FIYAT']:,.2f} $", axis=1)
                raw_display['TOPLAM_SERMAYE'] = raw_display['TOPLAM_SERMAYE'].map('{:,.2f} $'.format)
                
                drop_cols = [c for c in ['ORIJINAL_FIYAT', 'PARA_BIRIMI'] if c in raw_display.columns]
                if drop_cols:
                    raw_display = raw_display.drop(columns=drop_cols)
                    
                st.dataframe(raw_display, use_container_width=True, hide_index=True)
            else:
                st.warning(f"Bu sekme ({tab_name}) için veri bulunamadı.")