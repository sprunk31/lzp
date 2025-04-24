import streamlit as st
import pandas as pd
from io import BytesIO
import base64
from openpyxl.styles import PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows

# Pagina instellingen
st.set_page_config(page_title="LZP Vergelijktool", page_icon="📊", layout="centered")

# ✅ Logo laden vanuit assets/logo.png (voor Streamlit Cloud én lokaal gebruik)
with open("assets/logo.png", "rb") as image_file:
    encoded = base64.b64encode(image_file.read()).decode()
    logo_html = f'''
        <div style="text-align: center; margin-bottom: 1rem;">
            <img src="data:image/png;base64,{encoded}" width="300">
        </div>
    '''

# ✅ Styling en logo tonen
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

# 🔐 Login met gebruikers uit Streamlit secrets
gebruikers = st.secrets["auth"]

def login():
    st.markdown("<div class='section-header'>🔐 LZP Inloggen</div>", unsafe_allow_html=True)
    username = st.text_input("Gebruikersnaam")
    password = st.text_input("Wachtwoord", type="password")
    if st.button("Inloggen"):
        if gebruikers.get(username) == password:
            st.session_state["ingelogd"] = True
            st.success(f"✅ Ingelogd als {username}")
            st.rerun()
        else:
            st.error("❌ Ongeldige inloggegevens")

if "ingelogd" not in st.session_state or not st.session_state["ingelogd"]:
    login()
    st.stop()

# 📁 Upload twee bestanden
st.markdown("<div class='section-header'>📂 Upload je Excelbestanden</div>", unsafe_allow_html=True)
prezero_file = st.file_uploader("Upload PreZero Excelbestand (.xlsm, .xlsx, .xls)", type=["xlsm", "xlsx", "xls"], key="prezero")
avalex_file = st.file_uploader("Upload Avalex Excelbestand (.xlsm, .xlsx, .xls)", type=["xlsm", "xlsx", "xls"], key="avalex")

if prezero_file and avalex_file:
    try:
        prezero_sheets = pd.read_excel(prezero_file, sheet_name=None)
        avalex_sheets = pd.read_excel(avalex_file, sheet_name=None)
    except Exception as e:
        st.error(f"❌ Fout bij het lezen van de Excelbestanden: {e}")
        st.stop()

    if 'Overslag_import' not in prezero_sheets or 'Blad1' not in avalex_sheets:
        st.error("❌ Vereiste tabbladen ontbreken in één van de bestanden.")
    else:
        df_prezero = prezero_sheets['Overslag_import']
        df_avalex = avalex_sheets['Blad1']

        # Dropdown voor bestemming
        unieke_bestemmingen = df_avalex['Bestemming'].dropna().unique().tolist()
        waarde = st.selectbox("Selecteer bestemming", unieke_bestemmingen)

        df_avalex_filtered = df_avalex[df_avalex['Bestemming'] == waarde].copy()
        df_avalex_rest = df_avalex[df_avalex['Bestemming'] != waarde].copy()

        # Check vereiste kolommen
        required_pre = ['weegbonnr', 'gewicht']
        required_ava = ['Weegbonnummer', 'Gewicht(kg)']
        missing = [c for c in required_pre if c not in df_prezero.columns] + \
                  [c for c in required_ava if c not in df_avalex_filtered.columns]
        if missing:
            st.error(f"❌ Ontbrekende kolommen: {', '.join(missing)}")
            st.stop()

        # Genormaliseerde bonnummers
        def normalize_bon(val):
            try:
                return "" if pd.isna(val) or str(val).strip()=="" else str(int(float(val)))
            except:
                return str(val).strip()

        df_prezero['weegbonnr_genorm'] = df_prezero['weegbonnr'].apply(normalize_bon)
        df_avalex_filtered['Weegbonnummer_genorm'] = df_avalex_filtered['Weegbonnummer'].apply(normalize_bon)

        bon_dict = df_prezero.set_index('weegbonnr_genorm')['gewicht'].to_dict()

        # Spinner + progress bar rondom matching
        with st.spinner("Verwerken van weegbonnen…"):
            total = len(df_avalex_filtered)
            progress = st.progress(0)
            resultaten = []
            for idx, row in enumerate(df_avalex_filtered.itertuples(), start=1):
                bon = row.Weegbonnummer_genorm
                gewicht = row._asdict().get('Gewicht(kg)', None)

                if bon == "":
                    resultaat = "Geen bon aanwezig"
                elif bon in bon_dict:
                    gewicht_ref = bon_dict[bon]
                    try:
                        if pd.isna(gewicht) or round(gewicht, 1) != round(gewicht_ref, 1):
                            resultaat = gewicht_ref
                        else:
                            resultaat = "Bon aanwezig"
                    except:
                        resultaat = gewicht_ref
                else:
                    resultaat = "Geen bon aanwezig"

                resultaten.append(resultaat)
                # update progress bar
                progress.progress(int(idx/total * 100))

        df_avalex_filtered['komt voor in PreZero'] = resultaten
        df_avalex_rest['komt voor in PreZero'] = ""
        df_avalex_combined = pd.concat([df_avalex_filtered, df_avalex_rest], ignore_index=True)

        # … (de rest van je export, styling en samenvatting blijft ongewijzigd)
        # Bijvoorbeeld:
        ontbrekende_mask = ~df_prezero['weegbonnr_genorm'].isin(
            df_avalex_combined['Weegbonnummer'].apply(normalize_bon)
        )

        # Samenvatting
        st.markdown("<div class='section-header'>📊 Resultaatoverzicht</div>", unsafe_allow_html=True)
        st.markdown(f"""
        - ✅ Bon aanwezig: **{resultaten.count("Bon aanwezig")}**
        - ⚖️ Gewicht verschilt: **{sum(isinstance(r, (float, int)) for r in resultaten)}**
        - ❌ Geen bon aanwezig: **{resultaten.count("Geen bon aanwezig")}**
        - 🔁 PreZero-bonnen zonder match in Avalex: **{ontbrekende_mask.sum()}**
        """)
        st.success("✅ Verwerking voltooid.")
        st.download_button(
            "📥 Download resultaatbestand",
            data=output.getvalue(),
            file_name="LZP_resultaat.xlsx"
        )
