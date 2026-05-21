import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Sayfa Ayarları
st.set_page_config(page_title="ZORE PANEL", layout="wide", initial_sidebar_state="collapsed")

# 2. Veri Yükleme ve Temizleme
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=csv"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip() # Boşlukları temizle
    
    # Sayısal alanları düzenle
    df['ADET'] = pd.to_numeric(df['ADET'], errors='coerce').fillna(0)
    df['FIYAT_NUM'] = df['FIYAT'].astype(str).str.replace('¥', '', regex=False).str.replace(',', '.', regex=False)
    df['FIYAT_NUM'] = pd.to_numeric(df['FIYAT_NUM'], errors='coerce').fillna(0)
    df['TUTAR'] = df['ADET'] * df['FIYAT_NUM']
    return df

df = load_data()

# 3. Durum Yönetimi (Sayfalar arası geçiş için)
if 'page' not in st.session_state:
    st.session_state.page = 'main'
if 'selected_company' not in st.session_state:
    st.session_state.selected_company = None

# --- ANA EKRAN FONKSİYONU ---
def show_main():
    st.title("📊 ZORE SİPARİŞ KONTROL MERKEZİ")
    
    # KPI'lar
    c1, c2, c3 = st.columns(3)
    c1.metric("Toplam Harcama", f"¥{df['TUTAR'].sum():,.2f}")
    c2.metric("Toplam Adet", f"{int(df['ADET'].sum()):,}")
    c3.metric("Toplam Firma", len(df['FIRMA'].unique()))
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Firma Bazlı Harcama")
        fig1 = px.bar(df.groupby('FIRMA')['TUTAR'].sum().reset_index().nlargest(10, 'TUTAR'), 
                      x='FIRMA', y='TUTAR', template="plotly_dark", color_discrete_sequence=['#3b82f6'])
        st.plotly_chart(fig1, use_container_width=True)
        
    with col2:
        st.subheader("Ürün Bazlı Adet (İlk 10)")
        fig2 = px.bar(df.groupby('MALIN CINSI')['ADET'].sum().reset_index().nlargest(10, 'ADET'), 
                      x='MALIN CINSI', y='ADET', template="plotly_dark", color_discrete_sequence=['#a855f7'])
        st.plotly_chart(fig2, use_container_width=True)
    
    st.subheader("Firmalar (Detay İçin Tıklayın)")
    # Grid yapısı
    cols = st.columns(4)
    for i, company in enumerate(df['FIRMA'].unique()):
        with cols[i % 4]:
            if st.button(f"🔍 {company}", key=company):
                st.session_state.selected_company = company
                st.session_state.page = 'detail'
                st.rerun()

# --- DETAY EKRANI FONKSİYONU ---
def show_detail():
    company = st.session_state.selected_company
    if st.button("⬅️ Ana Panele Dön"):
        st.session_state.page = 'main'
        st.rerun()
        
    st.title(f"🏢 {company} Analiz Profili")
    
    # Firma verisi
    comp_df = df[df['FIRMA'] == company]
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Firma Harcaması", f"¥{comp_df['TUTAR'].sum():,.2f}")
    c2.metric("Toplam Sipariş Adet", f"{int(comp_df['ADET'].sum()):,}")
    c3.metric("Ürün Çeşidi", len(comp_df['MALIN CINSI'].unique()))
    
    st.subheader("Bu Firmanın En Çok Sipariş Edilen 5 Ürünü")
    fig = px.bar(comp_df.groupby('MALIN CINSI')['ADET'].sum().nlargest(5).reset_index(), 
                 x='MALIN CINSI', y='ADET', template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Sipariş Kalemleri")
    st.dataframe(comp_df, use_container_width=True)

# 4. Sayfa Yönlendirici
if st.session_state.page == 'main':
    show_main()
else:
    show_detail()