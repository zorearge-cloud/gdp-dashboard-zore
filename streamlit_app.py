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

# --- AYARLAR VE ANAYASA (TAM KAPSAMLI YAPI) ---
st.set_page_config(layout="wide", page_title="ZORE Veri Paneli")

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

# Kolon kaymalarını sıfırlayan akıllı haritalama sözlüğü
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

# --- GELİŞMİŞ TARİH STANDARTLAŞTIRMA MOTORU (SAATLERİ VE NaT HATASINI SİLER) ---
def strict_date_string_parser(val):
    if pd.isna(val) or val == "":
        return "BELİRTİLMEMİŞ"
    
    # openpyxl veya pandas hücreyi otomatik datetime objesi yaptıysa saat bilgisini ezerek temizliyoruz
    if hasattr(val, 'strftime'):
        return val.strftime('%Y-%m-%d')
        
    # Metin olarak gelen verilerde saat imzası varsa (00:00:00 gibi) tamamen buduyoruz
    val_str = str(val).strip()
    if " " in val_str:
        val_str = val_str.split()[0]
        
    # Farklı ayraçları standart nokta karakterine çekiyoruz
    val_str = val_str.replace('/', '.').replace('-', '.')
    
    # Olası tüm tarih varyasyonlarını tek tek süzgeçten geçiriyoruz
    for fmt in ['%Y.%m.%d', '%d.%m.%Y', '%Y.%d.%m']:
        try:
            dt = datetime.datetime.strptime(val_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except:
            continue
            
    # Küresel fallback denemesi
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
    
    # Tarih kolonlarını saatsiz ve temiz metin formatına çekiyoruz
    for col in ['SIPARIS_TARIHI', 'YUKLEME_TARIHI']:
        if col in df.columns:
            df[col] = df[col].apply(strict_date_string_parser)
            
    available_cols = [c for c in EXPECTED_COLUMNS if c in df.columns]
    df = df[available_cols].copy()
    df = df.dropna(how='all')
    
    if 'ADET' in df.columns:
        df['ADET'] = pd.to_numeric(df['ADET'], errors='coerce').fillna(0)
    
    # Çoklu Para Birimi ve Kur Dönüşüm Yönetimi (Tüm Gözden Kaçan Firmalar İçin Güçlendirildi)
    if 'FIYAT' in df.columns and 'FIRMA' in df.columns:
        def parse_price_details(row):
            val = row['FIYAT']
            firma_name = str(row['FIRMA']).upper().strip()
            if pd.isna(val):
                return 0.0, 0.0, '$'
            
            val_str = str(val).strip()
            currency = 'USD'
            sym_char = '$'
            
            # Genişletilmiş döviz sembol listesi
            yuan_symbols = ['¥', '￥', 'CNY', 'RMB', '元', 'CHINESE']
            euro_symbols = ['€', 'EUR', 'EURO']
            
            # Firma isminden, hücre içeriğinden veya gizli karakter kodlarından yakalama mantığı
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
                
            # Canlı kurlarla dolara çevrim adımı
            if currency == 'CNY':
                usd_price = numeric_price * rates["CNY_TO_USD"]
            elif currency == 'EUR':
                usd_price = numeric_price * rates["EUR_TO_USD"]
            else:
                usd_price = numeric_price
                
            return usd_price, numeric_price, sym_char

        res = df.apply(parse_price_details, axis=1)
        # Tüm ara yüzlerde ve raporlarda ANNY firmasında olduğu gibi net USD ($) basılması sağlanıyor
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

# --- COKLU DOSYA VE LINK YÖNETİM MOTORU ---
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
                            
                            # Excel hücre biçimlendirmesinden (Format) Yuan veya Euro tespiti (LCID tabanlı ek koruma)
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
            if x == "BELİRTİLMEMİŞ" or len(x) < 7:
                return "Bilinmeyen Dönem"
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

# --- SAYFA 1: GENEL DASHBOARD (8 GRAFİKLİ CANLI SİNEMATİK DÖNGÜ YAPISI) ---
if page == "1. Genel Dashboard":
    st.header("📊 Genel Dashboard")
    
    if df_dashboard.empty:
        st.error("Veri havuzunda işlenecek kayıt bulunamadı.")
    else:
        # KRONOLOJİK DÖNGÜ ALTYAPISI (GIF Etkisi Yaratır)
        tum_aylar = sorted([str(ay) for ay in df_dashboard['SIPARIS_AY'].unique() if str(ay) != "Bilinmeyen Dönem"])
        if not tum_aylar:
            tum_aylar = ["Bilinmeyen Dönem"]

        # Otomatik akış için Session State durum kilitleri
        if "play_index" not in st.session_state:
            st.session_state.play_index = 0
        if "is_playing" not in st.session_state:
            st.session_state.is_playing = True  # İlk açılışta otomatik GIF gibi hareket etsin

        # Üst Siber Kontrol Paneli Tasarımı
        ctrl_box = st.container()
        with ctrl_box:
            c_ctrl1, c_ctrl2, c_ctrl3 = st.columns([3, 3, 6])
            with c_ctrl1:
                if st.session_state.is_playing:
                    if st.button("⏸️ Hareketi Durdur (Analiz Et)", use_container_width=True):
                        st.session_state.is_playing = False
                        st.rerun()
                else:
                    if st.button("▶️ Canlı GIF Modunu Başlat", use_container_width=True):
                        st.session_state.is_playing = True
                        st.rerun()
            with c_ctrl2:
                # Kullanıcı manuel incelemek isterse açılır kutu
                aktif_secim = st.selectbox("İzleme Dönemi:", tum_aylar, index=min(st.session_state.play_index, len(tum_aylar)-1))
                if not st.session_state.is_playing:
                    st.session_state.play_index = tum_aylar.index(aktif_secim)
            with c_ctrl3:
                st.markdown(f"<div style='font-size:16px; font-weight:bold; color:#00f3ff; text-align:center; padding-top:6px;'>🎬 CANLI DÖNGÜ SEGMENTİ: <span style='color:#ffaa00; background-color:rgba(255,170,0,0.15); padding:4px 10px; border-radius:5px;'>{tum_aylar[st.session_state.play_index]}</span></div>", unsafe_allow_html=True)

        # Aktif Sinematik Veri Dilimlerinin Enjeksiyonu
        current_month = tum_aylar[st.session_state.play_index]
        if current_month == "Bilinmeyen Dönem":
            df_active = df_dashboard.copy()
            df_trend_active = df_dashboard.copy()
        else:
            # Anlık kesit verileri (Barlar, Pastalar ve Metrikler için)
            df_active = df_dashboard[df_dashboard['SIPARIS_AY'] == current_month].copy()
            # Kümülatif trend çizgisi akışı (Çizgi grafiklerinin soldan sağa büyümesi için)
            df_trend_active = df_dashboard[df_dashboard['SIPARIS_AY'] <= current_month].copy()

        # Boş küme korumaları
        df_visual = df_active if not df_active.empty else df_dashboard
        df_trend_visual = df_trend_active if not df_trend_active.empty else df_dashboard

        # --- METRİKLER (Aktif Döneme Göre Canlanır) ---
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Toplam Sipariş Adedi ({current_month})", f"{int(df_visual['ADET'].sum()):,}")
        c2.metric(f"Toplam Sermaye Yatırımı ({current_month})", f"{df_visual['TOPLAM_SERMAYE'].sum():,.2f} $")
        c3.metric(f"Çalışılan Firma Sayısı ({current_month})", df_visual['FIRMA'].nunique())

        st.markdown("---")
        
        # --- 8 GRAFİK MATRİSİNİN SİNEMATİK ÇİZİM ALANI ---
        g1, g2 = st.columns(2)
        top_sips = df_visual.groupby('MALIN CINSI')['ADET'].sum().nlargest(10).reset_index()
        fig1 = px.bar(top_sips, x='MALIN CINSI', y='ADET', title=f"1. En Çok Sipariş Edilen 10 Ürün - Adet ({current_month})", color='ADET')
        g1.plotly_chart(fig1, use_container_width=True)
        
        top_money = df_visual.groupby('MALIN CINSI')['TOPLAM_SERMAYE'].sum().nlargest(10).reset_index()
        fig2 = px.bar(top_money, x='MALIN CINSI', y='TOPLAM_SERMAYE', title=f"2. En Çok Sermaye Yatırılan 10 Ürün - $ ({current_month})", color='TOPLAM_SERMAYE')
        g2.plotly_chart(fig2, use_container_width=True)

        g3, g4 = st.columns(2)
        top_firma = df_visual.groupby('FIRMA')['TOPLAM_SERMAYE'].sum().nlargest(10).reset_index()
        fig3 = px.pie(top_firma, values='TOPLAM_SERMAYE', names='FIRMA', title=f"3. Harcama Yapılan İlk 10 Firma ({current_month})", hole=0.4)
        fig3.update_traces(textinfo='label+percent')
        g3.plotly_chart(fig3, use_container_width=True)
        
        top_tur = df_visual.groupby('TUR')['TOPLAM_SERMAYE'].sum().nlargest(10).reset_index()
        fig4 = px.pie(top_tur, values='TOPLAM_SERMAYE', names='TUR', title=f"4. Tür Bazlı Harcama Dağılımı - USD ({current_month})", hole=0.4)
        fig4.update_traces(textinfo='label+percent')
        g4.plotly_chart(fig4, use_container_width=True)

        # Trend analizi için 2026 kısıtı korunarak kümülatif büyüme sağlanır
        df_2026 = df_trend_visual[df_trend_visual['SIPARIS_AY'].str.startswith('2026', na=False)].copy().sort_values('SIPARIS_AY')
        if df_2026.empty:
            df_2026 = df_trend_visual.copy().sort_values('SIPARIS_AY')

        g5, g6 = st.columns(2)
        # Renk paletlerinin oynamaması için global havuzdan en büyük 5 firma çekilir
        top_5_firmalar = df_dashboard[df_dashboard['SIPARIS_AY'].str.startswith('2026', na=False)].groupby('FIRMA')['TOPLAM_SERMAYE'].sum().nlargest(5).index
        if top_5_firmalar.empty:
            top_5_firmalar = df_dashboard.groupby('FIRMA')['TOPLAM_SERMAYE'].sum().nlargest(5).index

        df_trend_firma = df_2026[df_2026['FIRMA'].isin(top_5_firmalar)]
        if not df_trend_firma.empty:
            trend_firma = df_trend_firma.groupby(['SIPARIS_AY', 'FIRMA'])['TOPLAM_SERMAYE'].sum().reset_index().sort_values('SIPARIS_AY')
            fig5 = px.line(trend_firma, x='SIPARIS_AY', y='TOPLAM_SERMAYE', color='FIRMA', title="5. Aylık Firma Harcama Trendi (Zaman Çizgisinde İlerleyen Akış)", markers=True)
            fig5.update_layout(xaxis_type='category')
            g5.plotly_chart(fig5, use_container_width=True)
        else:
            g5.info("Veri akışı bekleniyor...")
        
        top_5_turler = df_dashboard[df_dashboard['SIPARIS_AY'].str.startswith('2026', na=False)].groupby('TUR')['TOPLAM_SERMAYE'].sum().nlargest(5).index
        if top_5_turler.empty:
            top_5_turler = df_dashboard.groupby('TUR')['TOPLAM_SERMAYE'].sum().nlargest(5).index

        df_trend_tur = df_2026[df_2026['TUR'].isin(top_5_turler)]
        if not df_trend_tur.empty:
            trend_tur = df_trend_tur.groupby(['SIPARIS_AY', 'TUR'])['TOPLAM_SERMAYE'].sum().reset_index().sort_values('SIPARIS_AY')
            fig6 = px.line(trend_tur, x='SIPARIS_AY', y='TOPLAM_SERMAYE', color='TUR', title="6. Aylık Tür Harcama Trendi (Zaman Çizgisinde İlerleyen Akış)", markers=True)
            fig6.update_layout(xaxis_type='category')
            g6.plotly_chart(fig6, use_container_width=True)
        else:
            g6.info("Veri akışı bekleniyor...")

        g7, g8 = st.columns(2)
        trend_total = df_2026.groupby('SIPARIS_AY')['TOPLAM_SERMAYE'].sum().reset_index().sort_values('SIPARIS_AY')
        fig7 = px.line(trend_total, x='SIPARIS_AY', y='TOPLAM_SERMAYE', title="7. Aylık Toplam Sermaye Akışı (Zaman Çizgisinde İlerleyen Akış)", markers=True)
        fig7.update_layout(xaxis_type='category')
        g7.plotly_chart(fig7, use_container_width=True)
        
        df_barkod_temiz = df_visual[(df_visual['BARKOD'] != "BELİRTİLMEMİŞ") & (df_visual['BARKOD'].str.strip() != "")]
        if df_barkod_temiz.empty:
            df_barkod_temiz = df_dashboard[(df_dashboard['BARKOD'] != "BELİRTİLMEMİŞ") & (df_dashboard['BARKOD'].str.strip() != "")]

        top_barcode = df_barkod_temiz.groupby('BARKOD').agg({'ADET': 'sum', 'MALIN CINSI': 'first'}).nlargest(10, 'ADET').reset_index()
        fig8 = px.bar(top_barcode, x='MALIN CINSI', y='ADET', title=f"8. Barkod Bazlı Top 10 Ürün ({current_month})", text='BARKOD', color='ADET')
        g8.plotly_chart(fig8, use_container_width=True)

        # OTOMATİK GIF/FİLM TETİKLEYİCİ
        if st.session_state.is_playing:
            time.sleep(1.3)  # Grafik geçiş hızı kararlılığı (Saniye)
            st.session_state.play_index = (st.session_state.play_index + 1) % len(tum_aylar)
            st.rerun()

# --- SAYFA 2: FİRMA BAZLI ANALİZ (ANAYASAL DEĞİŞMEZ KORUMA ALANI) ---
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

# --- SAYFA 3: HAM VERİ (ANAYASAL DEĞİŞMEZ KORUMA ALANI) ---
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