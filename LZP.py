import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="LZP Vergelijktool")
st.title("📊 LZP Vergelijktool")

# 🔐 Login met gebruikers uit Streamlit secrets
gebruikers = st.secrets["auth"]

def login():
    st.title("🔐 LZP Inloggen")
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
st.subheader("📂 Upload je Excelbestanden")
prezero_file = st.file_uploader("Upload PreZero Excelbestand (.xlsm, .xlsx, .xls)", type=["xlsm", "xlsx", "xls"], key="prezero")
avalex_file = st.file_uploader("Upload Avalex Excelbestand (.xlsm, .xlsx, .xls)", type=["xlsm", "xlsx", "xls"], key="avalex")

if prezero_file and avalex_file:
    # ✅ Inladen van data
    prezero_sheets = pd.read_excel(prezero_file, sheet_name=None, engine='openpyxl')
    avalex_sheets = pd.read_excel(avalex_file, sheet_name=None, engine='openpyxl')

    if 'Overslag_import' not in prezero_sheets or 'Blad1' not in avalex_sheets:
        st.error("❌ Vereiste tabbladen ontbreken in één van de bestanden.")
    else:
        df_prezero = prezero_sheets['Overslag_import']
        df_avalex = avalex_sheets['Blad1']

        # ✅ Filter op kolom 'Bestemming'
        waarde = "Suez Recycling Services Berkel"
        if 'Bestemming' in df_avalex.columns:
            df_avalex = df_avalex[df_avalex['Bestemming'] == waarde].copy()
        else:
            st.error("❌ Kolom 'Bestemming' ontbreekt in Avalex-bestand.")
            st.stop()

        # ✅ Controleer benodigde kolommen
        if all(k in df_prezero.columns for k in ['weegbonnr', 'gewicht']) and \
           all(k in df_avalex.columns for k in ['Weegbonnummer', 'Gewicht(kg)']):

            # 🔧 Normaliseren van bonnummers
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

            # 📘 Maak dictionary van PreZero
            bon_dict = df_prezero.set_index('weegbonnr_genorm')['gewicht'].to_dict()

            # 🔍 Vergelijken
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
            st.subheader("📊 Resultaatoverzicht")
            st.markdown(f"""
            - ✅ Bon aanwezig: **{resultaten.count("Bon aanwezig")}**
            - ⚖️ Gewicht verschilt: **{sum(isinstance(r, (float, int)) for r in resultaten)}**
            - ❌ Geen bon aanwezig: **{resultaten.count("Geen bon aanwezig")}**
            """)

            # 💾 Resultaat opslaan
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_prezero.to_excel(writer, sheet_name='PreZero', index=False)
                df_avalex.to_excel(writer, sheet_name='Avalex', index=False)

            st.success("✅ Verwerking voltooid.")
            st.download_button(
                "📥 Download resultaatbestand",
                data=output.getvalue(),
                file_name="LZP_resultaat.xlsx"
            )
        else:
            st.error("❌ Kolommen ontbreken in de Excelbestanden.")
