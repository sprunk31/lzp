import streamlit as st
import pandas as pd
from io import BytesIO

gebruikers = st.secrets["auth"]

def login():
    st.title("🔐 Inloggen")
    username = st.text_input("Gebruikersnaam")
    password = st.text_input("Wachtwoord", type="password")
    if st.button("Inloggen"):
        if gebruikers.get(username) == password:
            st.session_state["ingelogd"] = True
            st.success(f"Ingelogd als {username}")
            st.experimental_rerun()
        else:
            st.error("Ongeldige inloggegevens")

if "ingelogd" not in st.session_state or not st.session_state["ingelogd"]:
    login()
    st.stop()

st.set_page_config(page_title="LZP Vergelijktool")
st.title("📊 LZP Vergelijktool")

uploaded_file = st.file_uploader("Upload een LZP Excelbestand (.xlsm)", type=["xlsm"])

if uploaded_file:
    # Lees alle tabbladen in als DataFrames
    all_sheets = pd.read_excel(uploaded_file, sheet_name=None)

    # Check of benodigde sheets bestaan
    if 'Overslag_import' not in all_sheets or 'Blad1' not in all_sheets:
        st.error("❌ Vereiste tabbladen 'Overslag_import' of 'Blad1' ontbreken.")
    else:
        sheet_1 = all_sheets['Overslag_import']
        sheet_2 = all_sheets['Blad1']

        # Controle op kolommen
        if all(k in sheet_1.columns for k in ['weegbonnr', 'gewicht']) and \
           all(k in sheet_2.columns for k in ['Weegbonnummer', 'Gewicht(kg)']):

            # Maak dictionary van weegbonnr -> gewicht
            bon_dict = sheet_1.set_index('weegbonnr')['gewicht'].to_dict()

            resultaten = []

            for _, row in sheet_2.iterrows():
                bon = row['Weegbonnummer']
                gewicht = row['Gewicht(kg)']

                if pd.isna(bon):
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

            # Voeg kolom toe
            sheet_2['komt voor in sheet_1'] = resultaten

            # Samenvatting berekenen
            aantal_bon_aanwezig = sum(1 for r in resultaten if r == "Bon aanwezig")
            aantal_gewicht_verschil = sum(1 for r in resultaten if isinstance(r, (float, int)))
            aantal_geen_bon = sum(1 for r in resultaten if r == "Geen bon aanwezig")

            # Toon samenvatting
            st.subheader("📊 Resultaatoverzicht")
            st.markdown(f"""
            - ✅ Bon aanwezig: **{aantal_bon_aanwezig}**
            - ⚖️ Gewicht verschilt (getal als resultaat): **{aantal_gewicht_verschil}**
            - ❌ Geen bon aanwezig: **{aantal_geen_bon}**
            """)

            # Opslaan in geheugen en aanbieden als download
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                sheet_1.to_excel(writer, sheet_name='Overslag_import', index=False)
                sheet_2.to_excel(writer, sheet_name='Blad1', index=False)

            st.success("✅ Verwerking voltooid.")
            st.download_button(
                label="📥 Download resultaatbestand",
                data=output.getvalue(),
                file_name="LZP_resultaat.xlsx"
            )

        else:
            st.error("❌ Kolommen 'weegbonnr', 'gewicht', 'Weegbonnummer' of 'Gewicht(kg)' ontbreken.")
