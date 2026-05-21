import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests

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
EXPECTED_COLUMNS = ['SIPARIS_TARIHI', 'FIRMA', 'TUR', 'BARKOD', 'MALIN CINSI', 'ADET', 'FIYAT', 'YUKLEME_TARIHI']

# --- CANLI DÖVİZ KURU MOTORU (GÜVENLİK CORUMALI) ---
@st.cache_data(ttl=3600)  # Kurları saatte bir günceller, uygulamayı yavaşlatmaz
def get_live_rates():
    # İnternet olmaması durumuna karşı 2026 yılı Güvenli Fallback (Yedek) Kurları
    rates = {"EUR_TO_USD": 1.09, "CNY_TO_USD": 0.14, "PROUNCE": "Yedek Kur Panelden Okundu"}
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
        pass  # Herhangi bir hata durumunda yedek kurlar sistemi ayakta tutar
    return rates

rates = get_live_rates()

def clean_data(df, rates):
    # Duplike sütunları temizle
    df = df.loc[:, ~df.columns.duplicated()]
    
    # Tarihleri düzelt
    for col in ['SIPARIS_TARIHI', 'YUKLEME_TARIHI']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
            
    # WHITELIST YÖNTEMİ
    available_cols = [c for c in EXPECTED_COLUMNS if c in df.columns]
    df = df[available_cols].copy()
    df = df.dropna(how='all')
    
    # Adet sütununu sayıya çevir
    if 'ADET' in df.columns:
        df['ADET'] = pd.to_numeric(df['ADET'], errors='coerce').fillna(0)
    
    # Gelişmiş Döviz Temizleme ve USD Değerine Dönüştürme Algoritması
    if 'FIYAT' in df.columns:
        def parse_price_to_usd(val):
            if pd.isna(val):
                return 0.0
            
            val_str = str(val).strip()
            
            # Para Birimi Tespiti
            currency = 'USD'  # Varsayılan
            if '¥' in val_str or 'CNY' in val_str.upper() or 'RMB' in val_str.upper():
                currency = 'CNY'
            elif '€' in val_str or 'EUR' in val_str.upper():
                currency = 'EUR'
            
            # Sembollerin ve harflerin temizlenmesi
            for clean_target in ['¥', '€', '$', 'CNY', 'EUR', 'USD', 'RMB', 'cny', 'eur', 'usd']:
                val_str = val_str.replace(clean_target, '')
            val_str = val_str.strip()
            
            # Türkçe/Yabancı Karışık Sayısal Format Düzeltme (Örn: "4,70" -> "4.70")
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
                
            # Kur Dönüşüm Hesaplaması
            if currency == 'CNY':
                return numeric_price * rates["CNY_TO_USD"]
            elif currency == 'EUR':
                return numeric_price * rates["EUR_TO_USD"]
            return numeric_price

        df['FIYAT'] = df['FIYAT'].apply(parse_price_to_usd)
    
    # Güvenli Sermaye Hesaplaması (Artık tüm girdiler net USD tabanlı)
    df['TOPLAM_SERMAYE'] = df['ADET'] * df['FIYAT']
    
    # Metinsel Alan Sabitleme Katsayısı
    for text_col in ['FIRMA', 'TUR', 'MALIN CINSI', 'BARKOD']:
        if text_col in df.columns:
            df[text_col] = df[text_col].fillna("BELİRTİLMEMİŞ").astype(str).str.strip()
            df[text_col] = df[text_col].replace({'nan': 'BELİRTİLMEMİŞ', 'None': 'BELİRTİLMEMİŞ', '': 'BELİRTİLMEMİŞ'})
            
    return df

# --- VERİ TOPLAMA VE BİRLEŞTİRME ---
@st.cache_data(ttl=600)
def get_all_data(rates):
    all_data_list = []
    pool = {tab: [] for tab in TARGET_TABS}
    
    for link in LINKS:
        try:
            xl = pd.ExcelFile(link)
            for tab in TARGET_TABS:
                if tab in xl.sheet_names:
                    df = pd.read_excel(xl, sheet_name=tab)
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

# Yan menüde aktif kullanılan kurların durumunu şeffafça gösterelim
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
        fig1 = px.bar(top_sips, x='ADET', y='MALIN CINSI', orientation='h', title="1. En Çok Sipariş Edilen 10 Ürün (Adet)", color='ADET')
        g1.plotly_chart(fig1, use_container_width=True)
        
        top_money = df_dashboard.groupby('MALIN CINSI')['TOPLAM_SERMAYE'].sum().nlargest(10).reset_index()
        fig2 = px.bar(top_money, x='TOPLAM_SERMAYE', y='MALIN CINSI', orientation='h', title="2. En Çok Sermaye Yatırılan 10 Ürün ($)", color='TOPLAM_SERMAYE')
        g2.plotly_chart(fig2, use_container_width=True)

        g3, g4 = st.columns(2)
        top_firma = df_dashboard.groupby('FIRMA')['TOPLAM_SERMAYE'].sum().nlargest(10).reset_index()
        fig3 = px.pie(top_firma, values='TOPLAM_SERMAYE', names='FIRMA', title="3. Harcama Yapılan İlk 10 Firma", hole=0.4)
        g3.plotly_chart(fig3, use_container_width=True)
        
        top_tur = df_dashboard.groupby('TUR')['TOPLAM_SERMAYE'].sum().nlargest(10).reset_index()
        fig4 = px.bar(top_tur, x='TUR', y='TOPLAM_SERMAYE', title="4. Tür Bazlı Harcama Dağılımı (USD)", color='TUR')
        g4.plotly_chart(fig4, use_container_width=True)

        g5, g6 = st.columns(2)
        trend_firma = df_dashboard.groupby(['SIPARIS_AY', 'FIRMA'])['TOPLAM_SERMAYE'].sum().reset_index()
        fig5 = px.line(trend_firma, x='SIPARIS_AY', y='TOPLAM_SERMAYE', color='FIRMA', title="5. Aylık Firma Harcama Trendi ($)")
        g5.plotly_chart(fig5, use_container_width=True)
        
        trend_tur = df_dashboard.groupby(['SIPARIS_AY', 'TUR'])['TOPLAM_SERMAYE'].sum().reset_index()
        fig6 = px.area(trend_tur, x='SIPARIS_AY', y='TOPLAM_SERMAYE', color='TUR', title="6. Aylık Tür Harcama Trendi ($)")
        g6.plotly_chart(fig6, use_container_width=True)

        g7, g8 = st.columns(2)
        trend_total = df_dashboard.groupby('SIPARIS_AY')['TOPLAM_SERMAYE'].sum().reset_index()
        fig7 = px.line(trend_total, x='SIPARIS_AY', y='TOPLAM_SERMAYE', title="7. Aylık Toplam Sermaye Akışı ($)", markers=True)
        g7.plotly_chart(fig7, use_container_width=True)
        
        top_barcode = df_dashboard.groupby('BARKOD').agg({'ADET': 'sum', 'MALIN CINSI': 'first'}).nlargest(10, 'ADET').reset_index()
        fig8 = px.bar(top_barcode, x='ADET', y='MALIN CINSI', title="8. Barkod Bazlı Top 10 Ürün", text='BARKOD', color='ADET')
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
                fig_a = px.pie(firma_df, values='TOPLAM_SERMAYE', names='TUR', title=f"{selected_firma} Ürün Kategorisi Dağılımı")
                col_a.plotly_chart(fig_a, use_container_width=True)
            else:
                col_a.info("Grafik için yeterli ciro verisi yok.")
            
            trend_data = firma_df.groupby('SIPARIS_AY')['TOPLAM_SERMAYE'].sum().reset_index()
            if not trend_data.empty and trend_data['TOPLAM_SERMAYE'].sum() > 0:
                fig_b = px.bar(trend_data, x='SIPARIS_AY', y='TOPLAM_SERMAYE', title=f"{selected_firma} Aylık Alım Trendi ($)")
                col_b.plotly_chart(fig_b, use_container_width=True)
            else:
                col_b.info("Zaman trendi grafik verisi bulunamadı.")
            
            st.subheader(f"{selected_firma} Sipariş Geçmişi")
            
            # Gösterilen tablodaki fiyat görünümünü de netleştirmek için formatlayalım
            display_df = firma_df.copy()
            display_df['FIYAT'] = display_df['FIYAT'].map('{:,.2f} $'.format)
            display_df['TOPLAM_SERMAYE'] = display_df['TOPLAM_SERMAYE'].map('{:,.2f} $'.format)
            
            st.dataframe(display_df.sort_values(by='SIPARIS_TARIHI', ascending=False), use_container_width=True, hide_index=True)

# --- SAYFA 3: HAM VERİ ---
elif page == "3. Ham Veri":
    st.header("📋 Ham Veri Havuzu")
    tabs = st.tabs(TARGET_TABS)
    for i, tab_ui in enumerate(tabs):
        with tab_ui:
            tab_name = TARGET_TABS[i]
            df_list = data_pool[tab_name]
            if df_list:
                combined_df = pd.concat(df_list, ignore_index=True)
                combined_df = combined_df.drop_duplicates()
                
                # Ham veri tablosunda da fiyatların optimize halini gösterelim
                raw_display = combined_df.copy()
                raw_display['FIYAT'] = raw_display['FIYAT'].map('{:,.2f} $'.format)
                raw_display['TOPLAM_SERMAYE'] = raw_display['TOPLAM_SERMAYE'].map('{:,.2f} $'.format)
                
                st.dataframe(raw_display, use_container_width=True, hide_index=True)
            else:
                st.warning(f"Bu sekme ({tab_name}) için veri bulunamadı.")