import streamlit as st
import pandas as pd

# Sayfa ayarları
st.set_page_config(layout="wide")
st.title("ZORE MERKEZİ VERİ HAVUZU")

# Link listesi
LINKS = [
    "https://docs.google.com/spreadsheets/d/1j819WkX93CkCy3VgZkSff5C_zNX5Z98jfK-FwI4ZWUU/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1hVk6VgMFXWAukoQwMDIoOLrG8SD4UDLFFRH9VmDhXSE/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1S1kTptWUEf705cBLw9P9mL6rrqbVjbcp1xk_hgQ-Ny0/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1VKb6za4Fse5XrGawPG6qvrQZuFhDRGaAysmADGIC7Wc/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=xlsx"
]

TARGET_TABS = ["has_air", "has_sea", "meh_air", "meh_sea", "ist_air", "ist_sea"]

def clean_data(df):
    # 1. Aynı isimli sütunlar varsa (örneğin TÜR) ilkini tut, sonrakileri sil
    df = df.loc[:, ~df.columns.duplicated()]
    
    # 2. 'Unnamed' olan sütunları komple at
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    # 3. Tarih sütunlarından saatleri temizle
    date_cols = ['SIPARIS_TARIHI', 'YUKLEME_TARIHI']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
    
    # 4. YUKLEME_TARIHI sütununu bul ve ondan sonrasını tamamen at
    if 'YUKLEME_TARIHI' in df.columns:
        col_index = df.columns.get_loc('YUKLEME_TARIHI')
        # İlk sütundan, YUKLEME_TARIHI'ne kadar olanları al (gerisini kes)
        df = df.iloc[:, :col_index + 1]
    
    # 5. Boş satırları ve sütunları temizle
    df = df.dropna(how='all')
    df = df.dropna(axis=1, how='all')
    
    return df

# Veri havuzunu hazırla
data_pool = {tab: [] for tab in TARGET_TABS}

# Linkleri tara
for link in LINKS:
    try:
        xl = pd.ExcelFile(link)
        for tab in TARGET_TABS:
            if tab in xl.sheet_names:
                df = pd.read_excel(xl, sheet_name=tab)
                # Temizleme işleminden geçir
                df_clean = clean_data(df)
                if not df_clean.empty:
                    data_pool[tab].append(df_clean)
    except Exception as e:
        pass

# Arayüzü oluştur
tabs = st.tabs(TARGET_TABS)

for i, tab_ui in enumerate(tabs):
    with tab_ui:
        tab_name = TARGET_TABS[i]
        df_list = data_pool[tab_name]
        
        if df_list:
            # Tüm verileri birleştir
            combined_df = pd.concat(df_list, ignore_index=True)
            # Mükerrer satırları temizle
            combined_df = combined_df.drop_duplicates()
            
            st.write(f"Toplam {len(combined_df)} satır veri.")
            st.dataframe(combined_df, use_container_width=True, hide_index=True)
        else:
            st.warning(f"Bu sekme ({tab_name}) için veri bulunamadı.")