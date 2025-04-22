import streamlit as st
from openpyxl import load_workbook
from io import BytesIO
import pandas as pd

st.title("📊 LZP Vergelijktool")

uploaded_file = st.file_uploader("Upload een LZP Excelbestand (.xlsm)", type=["xlsm"])

if uploaded_file:
    wb = load_workbook(uploaded_file, data_only=True)

    if 'Overslag_import' not in wb.sheetnames or 'Blad1' not in wb.sheetnames:
        st.error("❌ Vereiste tabbladen 'Overslag_import' of 'Blad1' ontbreken.")
    else:
        ws1 = wb['Overslag_import']
        ws2 = wb['Blad1']

        # Haal weegbondata op uit sheet_1
        bon_dict = {}
        for row in ws1.iter_rows(min_row=2, values_only=True):
            weegbonnr, gewicht = row[0], row[1]
            if weegbonnr:
                bon_dict[str(weegbonnr).strip()] = gewicht

        # Zoek kolommen in Blad1
        headers = [cell.value for cell in ws2[1]]
        if 'Weegbonnummer' in headers and 'Gewicht(kg)' in headers:
            col_bon = headers.index("Weegbonnummer")
            col_gewicht = headers.index("Gewicht(kg)")

            nieuwe_kolom = len(headers) + 1
            ws2.cell(row=1, column=nieuwe_kolom).value = "komt voor in sheet_1"

            voorbeeld_output = []

            for i, row in enumerate(ws2.iter_rows(min_row=2, values_only=True), start=2):
                bon_raw = row[col_bon]
                gewicht = row[col_gewicht]

                bon = str(bon_raw).strip() if bon_raw else ""

                if not bon:
                    resultaat = "Geen bon aanwezig"
                elif bon in bon_dict:
                    gew_ref = bon_dict[bon]
                    try:
                        if round(float(gewicht), 1) == round(float(gew_ref), 1):
                            resultaat = "Bon aanwezig"
                        else:
                            resultaat = gew_ref
                    except:
                        resultaat = gew_ref
                else:
                    resultaat = "Geen bon aanwezig"

                ws2.cell(row=i, column=nieuwe_kolom).value = resultaat

                if i <= 6:  # eerste 5 rijen + kop
                    voorbeeld_output.append({
                        "Weegbonnummer": bon,
                        "Gewicht(kg)": gewicht,
                        "komt voor in sheet_1": resultaat
                    })

            # Toon voorbeeldoutput als tabel
            st.subheader("📋 Voorbeeld van resultaten")
            st.dataframe(pd.DataFrame(voorbeeld_output))

            # Downloadlink
            output = BytesIO()
            wb.save(output)
            st.success("✅ Verwerking voltooid.")
            st.download_button("📥 Download resultaatbestand", output.getvalue(), file_name="LZP_resultaat.xlsx")

        else:
            st.error("❌ Kolommen 'Weegbonnummer' of 'Gewicht(kg)' niet gevonden in tabblad Blad1.")
