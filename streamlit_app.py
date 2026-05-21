import streamlit as st
import pandas as pd
import plotly.express as px
import re

# Sayfa Ayarları
st.set_page_config(page_title="ZORE MASTER PANEL", layout="wide")

# 5 Linki buraya sabitliyorum, senin eklemene gerek yok.
URLS = [
    "https://docs.google.com/spreadsheets/d/1j819WkX93CkCy3VgZkSff5C_zNX5Z98jfK-FwI4ZWUU/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1hVk6VgMFXWAukoQwMDIoOLrG8SD4UDLFFRH9VmDhXSE/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1S1kTptWUEf705cBLw9P9mL6rrqbVjbcp1xk_hgQ-Ny0/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1VKb6za4Fse5XrGawPG6qvrQZuFhDRGaAysmADGIC7Wc/export?format=csv",
    "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
]

@st.cache_data(ttl=600)
def load_and_merge():
    all_dfs = []
    for url in URLS:
        try:
            df = pd.read_csv(url)
            all_dfs.append(df)
        except: continue
    
    # 5 Dosyayı tek bir devasa dataframe'de birleştir
    master_df = pd.concat(all_dfs, ignore_index=True)
    master_df.columns = master_df.columns.str.strip()
    
    # Tarih İşleme
    master_df['SIPARIS_TARIHI'] = pd.to_datetime(master_df['SIPARIS_TARIHI'], dayfirst=True, errors='coerce')
    master_df['AY'] = master_df['SIPARIS_TARIHI'].dt.strftime('%Y-%m')
    
    # Adet Temizleme
    master_df['ADET'] = pd.to_numeric(master_df['ADET'].astype(str).str.replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
    
    # Otomatik Kur Motoru
    def calculate_usd(row):
        val_str = str(row['FIYAT'])
        clean_val = re.sub(r'[^\d.]', '', val_str.replace(',', '.'))
        price = float(clean_val) if clean_val else 0.0
        # ¥ varsa 0.14 ile çarp, yoksa Dolar kabul et
        return (price * 0.14 * row['ADET']) if '¥' in val_str else (price * row['ADET'])

    master_df['TUTAR'] = master_df.apply(calculate_usd, axis=1)
    return master_df

# Veriyi Yükle
df = load_and_merge()

# --- ALTIN ÜÇLÜ PANEL ---
st.sidebar.title("🔍 ZORE KONTROL")
page = st.sidebar.radio("Sayfalar", ["Dashboard", "Firma Detay Analizi", "Ham Veri"])

# Filtreler (Global)
selected_month = st.sidebar.multiselect("Ay Seçimi", sorted(df['AY'].dropna().unique(), reverse=True), default=sorted(df['AY'].dropna().unique(), reverse=True))
df_f = df[df['AY'].isin(selected_month)]

# 1. DASHBOARD
if page == "Dashboard":
    st.title("📈 Genel Özet Paneli")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Ciro (USD)", f"${df_f['TUTAR'].sum():,.2f}")
    c2.metric("Toplam Adet", f"{int(df_f['ADET'].sum()):,}")
    c3.metric("Firma Sayısı", len(df_f['FIRMA'].unique()))
    c4.metric("Kategori Sayısı", len(df_f['TUR'].unique()))
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Firma Bazlı Harcama")
        fig1 = px.bar(df_f.groupby('FIRMA')['TUTAR'].sum().nlargest(10).reset_index(), 
                      x='TUTAR', y='FIRMA', orientation='h', template="plotly_dark", color='TUTAR')
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        st.subheader("Kategori Dağılımı")
        fig2 = px.pie(df_f, values='TUTAR', names='TUR', hole=0.4, template="plotly_dark")
        st.plotly_chart(fig2, use_container_width=True)

# 2. FİRMA DETAY ANALİZİ
elif page == "Firma Detay Analizi":
    st.title("🏢 Firma Detay Analizi")
    firm = st.selectbox("Analiz edilecek firma:", sorted(df['FIRMA'].unique()))
    f_df = df_f[df_f['FIRMA'] == firm]
    
    k1, k2 = st.columns(2)
    k1.metric("Toplam Harcama", f"${f_df['TUTAR'].sum():,.2f}")
    k2.metric("Sipariş Adet", int(f_df['ADET'].sum()))
    
    st.markdown("---")
    st.subheader(f"Sipariş Listesi ({firm})")
    st.dataframe(f_df[['AY', 'BARKOD', 'MALIN CINSI', 'TUR', 'ADET', 'TUTAR']], use_container_width=True)

# 3. HAM VERİ
else:
    st.title("🗄️ Tüm Kayıtlar")
    st.dataframe(df_f, use_container_width=True)