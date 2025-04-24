import streamlit as st
import pandas as pd
from io import BytesIO
import base64
from openpyxl.styles import PatternFill

# Pagina instellingen
st.set_page_config(page_title="LZP Vergelijktool", page_icon="📊", layout="centered")

# Logo laden
with open("assets/logo.png", "rb") as image_file:
    encoded = base64.b64encode(image_file.read()).decode()
    logo_html = f'''
        <div style="text-align: center; margin-bottom: 1rem;">
            <img src="data:image/png;base64,{encoded}" width="300">
        </div>
    '''

# Styling
st.markdown("""
    <style>
        .section-header {
            font-size: 1.3em;
            margin-top: 2rem;
            color: #34495e;
        }
        .stButton>button {
            background-color: #2c3e50;
            color: white;
            border-radius: 8px;
            padding: 0.5em 1em;
        }
        .stDownloadButton>button {
            background-color: #27ae60;
            color: white;
            border-radius: 8px;
            padding: 0.5em 1em;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown(logo_html, unsafe_allow_html=True)

# 🔐 Login-form
gebruikers = st.secrets["auth"]
if "ingelogd" not in st.session_state:
    st.session_state["ingelogd"] = False

with st.form("login_form"):
    st.markdown("<div class='section-header'>🔐 LZP Inloggen</div>", unsafe_allow_html=True)
    username = st.text_input("Gebruikersnaam")
    password = st.text_input("Wachtwoord", type="password")
    login_submitted = st.form_submit_button("Inloggen")

    if login_submitted:
        if gebruikers.get(username) == password:
            st.session_state["ingelogd"] = True
            st.success(f"✅ Ingelogd als {username}")
            st.experimental_rerun()
        else:
            st.error("❌ Ongeldige inloggegevens")

if not st.session_state["ingelogd"]:
    st.stop()

# 📁 Upload-form
with st.form("upload_form"):
    st.markdown("<div class='section-header'>📂 Upload je Excelbestanden</div>", unsafe_allow_html=True)
    prezero_file = st.file_uploader("Upload PreZero Excelbestand (.xlsm, .xlsx, .xls)", type=["xlsm", "xlsx", "xls"], key="prezero")
    avalex_file = st.file_uploader("Upload Avalex Excelbestand (.xlsm, .xlsx, .xls)", type=["xlsm", "xlsx", "xls"], key="avalex")
    upload_submitted = st.form_submit_button("Upload & Verwerk")

if not upload_submitted or not (prezero_file and avalex_file):
    st.stop()

# Data inlezen
try:
    prezero_sheets = pd.read_excel(prezero_file, sheet_name=None, engine='openpyxl')
    avalex_sheets = pd.read_excel(avalex_file, sheet_name=None, engine='openpyxl')
except Exception as e:
    st.error(f"❌ Fout bij het lezen van de Excelbestanden: {e}")
    st.stop()

if 'Overslag_import' not in prezero_sheets or 'Blad1' not in avalex_sheets:
    st.error("❌ Vereiste tabbladen ontbreken (Overslag_import of Blad1).")
    st.stop()

df_prezero = prezero_sheets['Overslag_import']
df_avalex = avalex_sheets['Blad1']

# Spinner+Progress tijdens verwerking
with st.spinner("Data wordt vergeleken…"):
    # Filter op bestemming (maak dit desgewenst dynamisch)
    waarde = "Suez Recycling Services Berkel"
    df_ava_f = df_avalex[df_avalex['Bestemming'] == waarde].copy()
    df_ava_rest = df_avalex[df_avalex['Bestemming'] != waarde].copy()

    # Controle benodigde kolommen
    exp_pre = ['weegbonnr', 'gewicht']
    exp_ava = ['Weegbonnummer', 'Gewicht(kg)']
    missing = [c for c in exp_pre if c not in df_prezero.columns] + \
              [c for c in exp_ava if c not in df_ava_f.columns]
    if missing:
        st.error(f"❌ Ontbrekende kolommen: {', '.join(missing)}")
        st.stop()

    # Normalisatie functies
    def norm(val):
        try:
            return str(int(float(val)))
        except:
            return "" if pd.isna(val) else str(val).strip()

    df_ava_f['bon_norm'] = df_ava_f['Weegbonnummer'].apply(norm)
    df_prezero['bon_norm'] = df_prezero['weegbonnr'].apply(norm)
    ref_dict = df_prezero.set_index('bon_norm')['gewicht'].to_dict()

    # Iteratief vergelijken met progress bar
    resultaten = []
    total = len(df_ava_f)
    progress = st.progress(0)
    for i, row in enumerate(df_ava_f.itertuples(), start=1):
        bon = row.bon_norm
        gewicht = getattr(row, 'Gewicht(kg)', None)

        if bon == "":
            resultaat = "Geen bon aanwezig"
        elif bon in ref_dict:
            g_ref = ref_dict[bon]
            try:
                if round(gewicht,1) != round(g_ref,1):
                    resultaat = g_ref
                else:
                    resultaat = "Bon aanwezig"
            except:
                resultaat = g_ref
        else:
            resultaat = "Geen bon aanwezig"

        resultaten.append(resultaat)
        progress.progress(int((i/total)*100))

    df_ava_f['komt voor in PreZero'] = resultaten
    df_ava_rest['komt voor in PreZero'] = ""
    df_avalex_combined = pd.concat([df_ava_f, df_ava_rest], ignore_index=True)

    # Ontbrekende PreZero-bonnen
    avalex_bonnen = df_avalex_combined['Weegbonnummer'].apply(norm).tolist()
    ontbrekend_mask = ~df_prezero['bon_norm'].isin(avalex_bonnen)

    # Export klaarmaken
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_prezero.drop(columns=['bon_norm'], errors='ignore')\
                  .to_excel(writer, sheet_name='PreZero', index=False)
        df_avalex_combined.drop(columns=['bon_norm'], errors='ignore')\
                          .to_excel(writer, sheet_name='Avalex', index=False)

        # Highlight ontbrekende rijen
        wb = writer.book
        ws = wb['PreZero']
        fill = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")
        for idx, miss in enumerate(ontbrekend_mask, start=2):
            if miss:
                for cell in ws[idx]:
                    cell.fill = fill

    # Samenvatting tonen
    st.markdown("<div class='section-header'>📊 Resultaatoverzicht</div>", unsafe_allow_html=True)
    st.markdown(f"""
    - ✅ Bon aanwezig: **{resultaten.count("Bon aanwezig")}**
    - ⚖️ Gewicht verschilt: **{sum(isinstance(r, (int, float)) for r in resultaten)}**
    - ❌ Geen bon aanwezig: **{resultaten.count("Geen bon aanwezig")}**
    - 🔁 PreZero-bonnen zonder match in Avalex: **{ontbrekend_mask.sum()}**
    """)
    st.success("✅ Verwerking voltooid.")
    st.download_button(
        "📥 Download resultaatbestand",
        data=output.getvalue(),
        file_name="LZP_resultaat.xlsx"
    )
