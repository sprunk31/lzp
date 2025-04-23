import streamlit as st
import pandas as pd
from io import BytesIO
import base64
import os

st.set_page_config(page_title="LZP Vergelijktool", page_icon="📊", layout="centered")

# ✅ Logo laden als base64 (voor Streamlit Cloud)
logo_path = os.path.join("assets", "logo.png")
with open(logo_path, "rb") as image_file:
    encoded = base64.b64encode(image_file.read()).decode()
    logo_html = f"""
        <div class="main-logo">
            <img src="data:image/png;base64,{encoded}" width="300">
        </div>
    """

# ✅ Styling en logo tonen
st.markdown(f"""
    <style>
        .main-logo {{
            display: flex;
            justify-content: center;
            margin-bottom: 1rem;
        }}
        .section-header {{
            font-size: 1.3em;
            margin-top: 2rem;
            color: #34495e;
        }}
        .stButton>button {{
            background-color: #2c3e50;
            color: white;
            border-radius: 8px;
            padding: 0.5em 1em;
        }}
        .stDownloadButton>button {{
            background-color: #27ae60;
            color: white;
            border-radius: 8px;
            padding: 0.5em 1em;
        }}
    </style>
    {logo_html}
""", unsafe_allow_html=True)

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
        prezero_sheets = pd.read_excel(prezero_file, sheet_name=None, engine=None)
        avalex_sheets = pd.read_excel(avalex_file, sheet_name=None, engine=None)
    except Exception as e:
        st.error(f"❌ Fout bij het lezen van de Excelbestanden: {e}")
        st.stop()

    if 'Overslag_import' not in prezero_sheets or 'Blad1' not in avalex_sheets:
        st.error("❌ Vereiste tabbladen ontbreken in één van de bestanden.")
    else:
        df_prezero = prezero_sheets['Overslag_import']
        df_avalex = avalex_sheets['Blad1']

        waarde = "Suez Recycling Services Berkel"
        if 'Bestemming' in df_avalex.columns:
            df_avalex = df_avalex[df_avalex['Bestemming'] == waarde].copy()
        else:
            st.error("❌ Kolom 'Bestemming' ontbreekt in Avalex-bestand.")
            st.stop()

        if all(k in df_prezero.columns for k in ['weegbonnr', 'gewicht']) and \
           all(k in df_avalex.columns for k in ['Weegbonnummer', 'Gewicht(kg)']):

            def normalize_avalex_bon(val):
                try:
                    if pd.isna(val) or str(val).strip() == "":
                        return ""
                    return str(int(float(val)))
                except:
                    return str(val).strip()

            def normalize_prezero_bon(val):
                try:
                    return str(int(float(val)))
                except:
                    return str(val).strip()

            df_avalex['Weegbonnummer_genorm'] = df_avalex['Weegbonnummer'].apply(normalize_avalex_bon)
            df_prezero['weegbonnr_genorm'] = df_prezero['weegbonnr'].apply(normalize_prezero_bon)

            bon_dict = df_prezero.set_index('weegbonnr_genorm')['gewicht'].to_dict()

            resultaten = []
            for _, row in df_avalex.iterrows():
                bon = row['Weegbonnummer_genorm']
                gewicht = row['Gewicht(kg)']

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

            df_avalex['komt voor in PreZero'] = resultaten

            # 📊 Samenvatting
            st.markdown("<div class='section-header'>📊 Resultaatoverzicht</div>", unsafe_allow_html=True)
            st.markdown(f"""
            - ✅ Bon aanwezig: **{resultaten.count("Bon aanwezig")}**
            - ⚖️ Gewicht verschilt: **{sum(isinstance(r, (float, int)) for r in resultaten)}**
            - ❌ Geen bon aanwezig: **{resultaten.count("Geen bon aanwezig")}**
            """)

            # 💾 Resultaat opslaan
            output = BytesIO()

            # ❌ Kolommen niet meesturen in Excel-bestand
            df_avalex_export = df_avalex.drop(columns=['Weegbonnummer_genorm'])
            df_prezero_export = df_prezero.drop(columns=['weegbonnr_genorm'])

            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_prezero_export.to_excel(writer, sheet_name='PreZero', index=False)
                df_avalex_export.to_excel(writer, sheet_name='Avalex', index=False)

            st.success("✅ Verwerking voltooid.")
            st.download_button(
                "📥 Download resultaatbestand",
                data=output.getvalue(),
                file_name="LZP_resultaat.xlsx"
            )
        else:
            st.error("❌ Kolommen ontbreken in de Excelbestanden.")
