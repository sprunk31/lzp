import streamlit as st
from openpyxl import load_workbook
from io import BytesIO

st.title("LZP Vergelijktool")

uploaded_file = st.file_uploader("Upload een LZP Excelbestand (.xlsm)", type=["xlsm"])

if uploaded_file:
    wb = load_workbook(uploaded_file, data_only=True)
    if 'Overslag_import' not in wb.sheetnames or 'Blad1' not in wb.sheetnames:
        st.error("Bestand mist vereiste tabbladen.")
    else:
        ws1 = wb['Overslag_import']
        ws2 = wb['Blad1']

        # Haal bon- en gewichtdata uit sheet_
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

            for i, row in enumerate(ws2.iter_rows(min_row=2, values_only=True), start=2):
                bon = row[col_bon]
                gewicht = row[col_gewicht]

                if not bon:
                    resultaat = "Geen bon aanwezig"
                elif str(bon).strip() in bon_dict:
                    gew_ref = bon_dict[str(bon).strip()]
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

            # Downloadlink aanbieden
            output = BytesIO()
            wb.save(output)
            st.success("Verwerking voltooid.")
            st.download_button("📥 Download resultaatbestand", output.getvalue(), file_name="LZP_resultaat.xlsx")

        else:
            st.error("Kolommen 'Weegbonnummer' en/of 'Gewicht(kg)' ontbreken in Blad1.")
