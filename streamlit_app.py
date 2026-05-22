import streamlit as st
import pandas as pd
import requests
import io
import openpyxl
import datetime
import json
import re

# --- SİBER UZAY KOMUTA AYARLARI ---
st.set_page_config(layout="wide", page_title="ZORE WAR ROOM SYSTEM")

# Tam Ekran, Arka Plan Stabilizasyonu, Neon Tasarım ve Alt Kesilmeyi Önleme (CSS)
st.markdown("""
<style>
    .reportview-container { background: #060913 !important; }
    .stDeployButton { display:none !important; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    div.block-container { 
        padding-top: 1rem; 
        padding-bottom: 5rem; /* Alt kesilmeyi önlemek için padding artırıldı */
        padding-left: 1.5rem; 
        padding-right: 1.5rem; 
        color: #00f3ff;
        font-family: 'Segoe UI', Tahoma, sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# Canlı Veri Havuzu
LINKS = [
    "https://docs.google.com/spreadsheets/d/1j819WkX93CkCy3VgZkSff5C_zNX5Z98jfK-FwI4ZWUU/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1hVk6VgMFXWAukoQwMDIoOLrG8SD4UDLFFRH9VmDhXSE/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1S1kTptWUEf705cBLw9P9mL6rrqbVjbcp1xk_hgQ-Ny0/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1VKb6za4Fse5XrGawPG6qvrQZuFhDRGaAysmADGIC7Wc/export?format=xlsx",
    "https://docs.google.com/spreadsheets/d/1F71jiUwqvxddv7jwJibisWVaFxQ3oLQPP3CohzK_idk/export?format=xlsx"
]

TARGET_TABS = ["has_air", "has_sea", "meh_air", "meh_sea", "ist_air", "ist_sea"]
HEADER_MAP = {
    'SIPARIS TARIHI': 'SIPARIS_TARIHI', 'SIPARIS_TARIHI': 'SIPARIS_TARIHI',
    'FIRMA': 'FIRMA', 'TUR': 'TUR', 'BARKOD': 'BARKOD',
    'MALIN CINSI': 'MALIN CINSI', 'ADET': 'ADET', 'FIYAT': 'FIYAT',
    'YUKLEME TARIHI': 'YUKLEME_TARIHI', 'YUKLEME_TARIHI': 'YUKLEME_TARIHI'
}

rates = {"EUR_TO_USD": 1.09, "CNY_TO_USD": 0.138}

def strict_date_parser(val):
    if pd.isna(val) or val == "": return "BELİRTİLMEMİŞ"
    if hasattr(val, 'strftime'): return val.strftime('%Y-%m-%d')
    s = str(val).strip().split()[0].replace('/', '.').replace('-', '.')
    for fmt in ['%Y.%m.%d', '%d.%m.%Y']:
        try: return datetime.datetime.strptime(s, fmt).strftime('%Y-%m-%d')
        except: continue
    return "BELİRTİLMEMİŞ"

def clean_and_process(df):
    df = df.loc[:, ~df.columns.duplicated()]
    if 'SIPARIS_TARIHI' in df.columns:
        df['SIPARIS_TARIHI'] = df['SIPARIS_TARIHI'].apply(strict_date_parser)
    if 'ADET' in df.columns:
        df['ADET'] = pd.to_numeric(df['ADET'], errors='coerce').fillna(0)
    if 'FIYAT' in df.columns:
        def parse_price(row):
            v = str(row['FIYAT']).upper().strip()
            firma = str(row.get('FIRMA', '')).upper()
            mult = 1.0
            if 'CATHY' in firma or any(x in v for x in ['¥', '￥', 'CNY']): mult = rates["CNY_TO_USD"]
            elif any(x in v for x in ['€', 'EUR']): mult = rates["EUR_TO_USD"]
            cleaned = re.sub(r'[^\d.,]', '', v)
            if ',' in cleaned and '.' in cleaned:
                if cleaned.find(',') > cleaned.find('.'): cleaned = cleaned.replace('.', '').replace(',', '.')
                else: cleaned = cleaned.replace(',', '')
            else: cleaned = cleaned.replace(',', '.')
            try: return float(cleaned) * mult
            except: return 0.0
        df['TOPLAM_SERMAYE'] = df['ADET'] * df.apply(parse_price, axis=1)
    else:
        df['TOPLAM_SERMAYE'] = 0.0
    return df

@st.cache_data(ttl=300)
def load_war_room_data():
    master_list = []
    error_logs = []
    for idx, link in enumerate(LINKS):
        try:
            res = requests.get(link, timeout=12)
            if res.status_code != 200: 
                error_logs.append(f"Link {idx+1} HTTP Hatası: {res.status_code}")
                continue
            wb = openpyxl.load_workbook(io.BytesIO(res.content), data_only=True)
            for tab in TARGET_TABS:
                if tab in wb.sheetnames:
                    sheet = wb[tab]
                    rows = list(sheet.iter_rows(values_only=False))
                    if not rows or len(rows) < 2: continue
                    headers = [HEADER_MAP.get(str(c.value).strip().upper().replace('İ','I'), str(c.value)) for c in rows[0]]
                    data = [[cell.value for cell in r] for r in rows[1:] if not all(cell.value is None for cell in r)]
                    if not data: continue
                    sub_df = pd.DataFrame(data, columns=headers[:len(data[0])])
                    master_list.append(clean_and_process(sub_df))
        except Exception as e:
            error_logs.append(f"Link {idx+1} İşleme Hatası: {str(e)}")
            continue
    return (pd.concat(master_list, ignore_index=True) if master_list else pd.DataFrame()), error_logs

# Veriyi ve logları çekiyoruz
df_raw, logs = load_war_room_data()

if logs:
    with st.sidebar.expander("🛠️ Sistem Terminal Çıktıları"):
        for log in logs: st.caption(log)

if df_raw.empty:
    st.error("🚨 SİBER VERİ MATRİSİ ALINAMADI. Bağlantıları kontrol edin.")
else:
    # Dönemsel Zaman Eğrisini Çıkarma
    if 'SIPARIS_TARIHI' in df_raw.columns:
        df_raw['AY'] = df_raw['SIPARIS_TARIHI'].str[:7]
    else:
        df_raw['AY'] = "2026-01"
        
    df_2026 = df_raw[df_raw['AY'].str.startswith('2026', na=False)].copy()
    if df_2026.empty:
        df_2026 = df_raw.copy()

    # Kronolojik olarak ayları sırala
    months_sequence = sorted(df_2026['AY'].unique())
    
    # JavaScript Matrix Veri Köprüsü Hazırlığı
    timeline_matrix = {}
    
    for month in months_sequence:
        df_m = df_2026[df_2026['AY'] == month]
        
        # 1. Top 7 Ürün (Adet) - Donat Verisi
        top_sips_df = df_m.groupby('MALIN CINSI')['ADET'].sum().nlargest(7).reset_index()
        pie_data_sips = [{"value": int(row['ADET']), "name": str(row['MALIN CINSI'])} for _, row in top_sips_df.iterrows()]

        # 2. Top 7 Ürün ($) - Donat Verisi
        top_money_df = df_m.groupby('MALIN CINSI')['TOPLAM_SERMAYE'].sum().nlargest(7).reset_index()
        pie_data_money = [{"value": round(row['TOPLAM_SERMAYE'], 2), "name": str(row['MALIN CINSI'])} for _, row in top_money_df.iterrows()]

        # 3. İlk 7 Firma Harcama Dağılımı - Donat Verisi
        if 'FIRMA' in df_m.columns:
            top_firms_df = df_m.groupby('FIRMA')['TOPLAM_SERMAYE'].sum().nlargest(7).reset_index()
            pie_data_firms = [{"value": round(row['TOPLAM_SERMAYE'], 2), "name": str(row['FIRMA'])} for _, row in top_firms_df.iterrows()]
        else:
            pie_data_firms = [{"value": 0, "name": "Firma Verisi Yok"}]

        # 4. Tür Dağılım Matrisi - Donat Verisi
        if 'TUR' in df_m.columns:
            top_cats = df_m.groupby('TUR')['ADET'].sum().nlargest(7).reset_index()
            pie_data_cats = [{"value": int(row['ADET']), "name": str(row['TUR'])} for _, row in top_cats.iterrows()]
        else:
            pie_data_cats = [{"value": 0, "name": "Tür Yok"}]

        # 5, 6, 7 kümülatif donatlarına dönüştürüyorum. 7 grafik için:
        # `c7`'yi aylık kümülatif donat olarak modelleyeceğim.

        # 5. Top 7 Firma Harcama Dağılımı (Kümülatif) - Donat Verisi
        top_firms_cum_df = df_dashboard[df_dashboard['AY'] <= month].groupby('FIRMA')['TOPLAM_SERMAYE'].sum().nlargest(7).reset_index()
        pie_data_firms_cum = [{"value": round(row['TOPLAM_SERMAYE'], 2), "name": str(row['FIRMA'])} for _, row in top_firms_cum_df.iterrows()]

        # 6. Top 7 Tür Harcama Dağılımı (Kümülatif) - Donat Verisi
        top_cats_cum_df = df_dashboard[df_dashboard['AY'] <= month].groupby('TUR')['TOPLAM_SERMAYE'].sum().nlargest(7).reset_index()
        pie_data_cats_cum = [{"value": round(row['TOPLAM_SERMAYE'], 2), "name": str(row['TUR'])} for _, row in top_cats_cum_df.iterrows()]

        # 7. Aylık Kümülatif Toplam Dağılım - Donat Verisi
        pie_data_total_cum = df_dashboard[df_dashboard['AY'] <= month].groupby('AY')['TOPLAM_SERMAYE'].sum().reset_index().nlargest(7, 'TOPLAM_SERMAYE')
        pie_data_total_cum = [{"value": round(row['TOPLAM_SERMAYE'], 2), "name": str(row['AY'])} for _, row in pie_data_total_cum.iterrows()]

        # 8. Top 7 Barkod (Adet) - Donat Verisi
        top_barkods_df = df_m.groupby('BARKOD')['ADET'].sum().nlargest(7).reset_index()
        pie_data_barkods = [{"value": int(row['ADET']), "name": str(row['BARKOD'])} for _, row in top_barkods_df.iterrows()]

        timeline_matrix[month] = {
            "pie_sips": pie_data_sips,
            "pie_money": pie_data_money,
            "pie_firms": pie_data_firms,
            "pie_cats": pie_data_cats,
            "pie_firms_cum": pie_data_firms_cum,
            "pie_cats_cum": pie_data_cats_cum,
            "pie_total_cum": pie_data_total_cum,
            "pie_barkods": pie_data_barkods
        }

    # --- CANVAS & WEBGL SAVAŞ ODASI MATRİS ARAYÜZÜ (HTML5 / ECHARTS) ---
    cinematic_loop_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
        <style>
            body {{
                background-color: #060913;
                color: #00f3ff;
                font-family: 'Segoe UI', Tahoma, sans-serif;
                margin: 0;
                padding: 0px;
                overflow: hidden;
            }}
            .matrix-header {{
                margin-bottom: 15px;
                border-bottom: 1px dashed rgba(0,243,255,0.15); 
                padding-bottom: 10px;
            }}
            .matrix-title {{
                margin: 0;
                font-size: 16px; 
                color: #ffffff; 
                letter-spacing: 1px;
                font-weight: 600;
            }}
            .matrix-subtitle {{
                margin: 5px 0 0 0;
                font-size: 12px; 
                color: #00f3ff; 
                font-weight: 600;
            }}
            .grid-layout {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 20px;
                padding: 20px;
            }}
            .panel-box {{
                background: rgba(4, 11, 28, 0.7);
                border: 1px solid rgba(0, 243, 255, 0.12);
                border-radius: 8px;
                padding: 15px;
                height: 420px; /* Donatlar için uygun yükseklik */
                box-shadow: 0 0 20px rgba(0, 243, 255, 0.2); /* Neon gölge */
            }}
        </style>
    </head>
    <body>

        <div class="matrix-header">
            <h2 class="matrix-title">🎬 Canlı Siber Savaş Odası Donat Matrisi (İlk 7 Dağılım Modu)</h2>
            <p class="matrix-subtitle">
                DÖNEM: <span id="active-period" style="color: #ffaa00; background: rgba(255,170,0,0.15); padding: 2px 8px; border-radius: 4px; font-family: monospace;">---- --</span> 
                <span style="color: #00ff66; margin-left: 10px;">[ 🟢 Sistem SÜREKLİ DÖNGÜDE - FİLM MODU AKTİF ]</span>
            </p>
        </div>

        <div class="grid-layout">
            <div id="doughnut_sips" class="panel-box"></div>
            <div id="doughnut_money" class="panel-box"></div>
            <div id="doughnut_firms" class="panel-box"></div>
            <div id="doughnut_cats" class="panel-box"></div>
            <div id="doughnut_firms_cum" class="panel-box"></div>
            <div id="doughnut_cats_cum" class="panel-box"></div>
            <div id="doughnut_total_cum" class="panel-box"></div>
            <div id="doughnut_barkods" class="panel-box"></div>
        </div>

        <script>
            // Veri Altyapısının Enjeksiyonu
            const timelineMatrix = {json.dumps(timeline_matrix)};
            const monthsSequence = {json.dumps(months_sequence)};
            
            let currentIndex = 0;

            // --- Gelişmiş Donat Grafik Ayarları ---
          
            const labelOption = {{
                show: true,
                color: '#7a92b5',
                fontSize: 11,
                formatter: '{{b}}\\n{{d}}%',
                position: 'outer',
                alignTo: 'edge',
                margin: 10
            }};

            const basePieOption = {{
                backgroundColor: 'transparent',
                tooltip: {{ trigger: 'item', formatter: '{{b}}: {{c}} Adet ({{d}}%)' }},
                series: [{{
                    type: 'pie',
                    roseType: 'radius', // Donanma tipi hareketli donat
                    radius: ['30%', '65%'],
                    center: ['50%', '52%'],
                    itemStyle: {{ borderRadius: 10, borderColor: '#060913', borderWidth: 2, shadowBlur: 10, shadowColor: 'rgba(0, 243, 255, 0.5)' }},
                    label: labelOption,
                    data: [],
                    animationType: 'scale',
                    animationEasing: 'elasticOut',
                    animationDelay: function (idx) {{ return idx * 100; }},
                    color: ['#00f3ff', '#ff00ff', '#00ff66', '#ffaa00', '#9900ff', '#ff0055', '#00cccc']
                }}]
            }};

            // Grafik Instancelarının Başlatılması
            const pieSips = echarts.init(document.getElementById('doughnut_sips'));
            const pieMoney = echarts.init(document.getElementById('doughnut_money'));
            const pieFirms = echarts.init(document.getElementById('doughnut_firms'));
            const pieCats = echarts.init(document.getElementById('doughnut_cats'));
            const pieFirmsCum = echarts.init(document.getElementById('doughnut_firms_cum'));
            const pieCatsCum = echarts.init(document.getElementById('doughnut_cats_cum'));
            const pieTotalCum = echarts.init(document.getElementById('doughnut_total_cum'));
            const pieBarkods = echarts.init(document.getElementById('doughnut_barkods'));

            // Başlıkların Ayarlanması
            function getPieOption(titleText, cum = false) {{
                let option = JSON.parse(JSON.stringify(basePieOption));
                option.title = {{
                    text: titleText,
                    textStyle: {{ color: cum ? '#ff00ff' : '#00f3ff', fontSize: 13, fontWeight: 'normal' }},
                    left: 'left',
                    top: 'top'
                }};
                return option;
            }}

            pieSips.setOption(getPieOption('1. En Çok Sipariş Edilen İlk 7 Ürün (Adet)'));
            pieMoney.setOption(getPieOption('2. En Çok Sermaye Yatırılan İlk 7 Ürün ($)'));
            pieFirms.setOption(getPieOption('3. İlk 7 Firma Harcama Dağılımı (USD)'));
            pieCats.setOption(getPieOption('4. İlk 7 Tür Dağılım Matrisi'));
            pieFirmsCum.setOption(getPieOption('5. Top 7 Firma Harcama Dağılımı (Kümülatif)', true));
            pieCatsCum.setOption(getPieOption('6. Top 7 Tür Harcama Dağılımı (Kümülatif)', true));
            pieTotalCum.setOption(getPieOption('7. Aylık Kümülatif Toplam Dağılım', true));
            pieBarkods.setOption(getPieOption('8. Top 7 Barkod (Adet)'));

            // --- SİNEMATİK DÖNGÜ VE GEÇİŞ MOTORU ---
            function runCinematicFrame() {{
                if (monthsSequence.length === 0) return;

                const activeMonth = monthsSequence[currentIndex];
                const currentData = timelineMatrix[activeMonth];

                // Başlık Panel Güncellemesi
                document.getElementById('active-period').innerText = activeMonth;

                // Grafik Veri Enjeksiyonları (Donatlar)
                pieSips.setOption({{ series: [{{ data: currentData.pie_sips }}] }});
                pieMoney.setOption({{ series: [{{ data: currentData.pie_money }}] }});
                pieFirms.setOption({{ series: [{{ data: currentData.pie_firms }}] }});
                pieCats.setOption({{ series: [{{ data: currentData.pie_cats }}] }});
                pieFirmsCum.setOption({{ series: [{{ data: currentData.pie_firms_cum }}] }});
                pieCatsCum.setOption({{ series: [{{ data: currentData.pie_cats_cum }}] }});
                pieTotalCum.setOption({{ series: [{{ data: currentData.pie_total_cum }}] }});
                pieBarkods.setOption({{ series: [{{ data: currentData.pie_barkods }}] }});

                // Endeksi İlerlet (Döngü Başa Saracak Şekilde)
                currentIndex = (currentIndex + 1) % monthsSequence.length;
            }}

            // 2.5 Saniyede Bir Yumuşak Dönüşüm Akışı
            setInterval(runCinematicFrame, 2500);
            runCinematicFrame(); // İlk kareyi anında tetikle

            // Ekran Boyut Adaptörü
            window.addEventListener('resize', function() {{
                pieSips.resize(); pieMoney.resize(); pieFirms.resize(); pieCats.resize();
                pieFirmsCum.resize(); pieCatsCum.resize(); pieTotalCum.resize(); pieBarkods.resize();
            }});
        </script>
    </body>
    </html>
    """

    # Gelişmiş HTML WebGL Yapısını Ekrana Basıyoruz
    st.components.v1.html(cinematic_loop_html, height=1900, scrolling=False)


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