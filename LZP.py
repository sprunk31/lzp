import streamlit as st
import pandas as pd
from io import BytesIO
import base64
from openpyxl.styles import PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows
from datetime import datetime
import os
import socket
import requests

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

def get_ip_and_location():
    try:
        ip = requests.get("https://api.ipify.org").text
        location_data = requests.get(f"https://ipapi.co/{ip}/json/").json()
        location = location_data.get("city", "Onbekend") + ", " + location_data.get("country_name", "Onbekend")
        return ip, location
    except:
        return "Onbekend", "Onbekend"

def log_login(username):
    ip, location = get_ip_and_location()
    log_entry = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},{username},{ip},{location}\n"
    log_path = "log.txt"
    with open(log_path, "a") as f:
        f.write(log_entry)

def login():
    st.markdown("<div class='section-header'>🔐 LZP Vergelijkingstool Inloggen</div>", unsafe_allow_html=True)
    username = st.text_input("Gebruikersnaam")
    password = st.text_input("Wachtwoord", type="password")
    if st.button("Inloggen"):
        if gebruikers.get(username) == password:
            st.session_state["ingelogd"] = True
            st.session_state["gebruiker"] = username
            log_login(username)
            st.success(f"✅ Ingelogd als {username}")
            st.rerun()
        else:
            st.error("❌ Ongeldige inloggegevens")

if "ingelogd" not in st.session_state or not st.session_state["ingelogd"]:
    login()
    st.stop()

# 👁️‍🗨️ Alleen admin mag log zien (ingeklapt)
if st.session_state.get("gebruiker") == "admin":
    with st.expander("📄 Inloglogboek bekijken (alleen admin)"):
        log_path = "log.txt"
        if os.path.exists(log_path):
            df_log = pd.read_csv(log_path, names=["Datumtijd", "Gebruiker", "IP-adres", "Locatie"])
            st.dataframe(df_log)
            log_buffer = BytesIO()
            df_log.to_csv(log_buffer, index=False)
            st.download_button("📥 Download logboek als CSV", data=log_buffer.getvalue(), file_name="login_log.csv")
        else:
            st.info("📭 Nog geen logboek aangemaakt.")

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

        df_avalex_filtered = df_avalex[df_avalex['Bestemming'] == waarde].copy()
        df_avalex_rest = df_avalex[df_avalex['Bestemming'] != waarde].copy()

        if all(k in df_prezero.columns for k in ['weegbonnr', 'gewicht']) and \
           all(k in df_avalex_filtered.columns for k in ['Weegbonnummer', 'Gewicht(kg)']):

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

            df_avalex_filtered['Weegbonnummer_genorm'] = df_avalex_filtered['Weegbonnummer'].apply(normalize_avalex_bon)
            df_prezero['weegbonnr_genorm'] = df_prezero['weegbonnr'].apply(normalize_prezero_bon)

            bon_dict = df_prezero.set_index('weegbonnr_genorm')['gewicht'].to_dict()

            resultaten = []
            for _, row in df_avalex_filtered.iterrows():
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

            df_avalex_filtered['komt voor in PreZero'] = resultaten
            df_avalex_rest['komt voor in PreZero'] = ""
            df_avalex_combined = pd.concat([df_avalex_filtered, df_avalex_rest], ignore_index=True)

            avalex_bonnen = df_avalex_combined['Weegbonnummer'].dropna().apply(normalize_avalex_bon).tolist()
            ontbrekende_mask = ~df_prezero['weegbonnr_genorm'].isin(avalex_bonnen)

            df_avalex_export = df_avalex_combined.drop(columns=['Weegbonnummer_genorm'], errors='ignore')
            df_prezero_export = df_prezero.drop(columns=['weegbonnr_genorm'], errors='ignore')

            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_prezero_export.to_excel(writer, sheet_name='PreZero', index=False)
                df_avalex_export.to_excel(writer, sheet_name='Avalex', index=False)

                wb = writer.book
                ws = wb['PreZero']
                fill = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")
                for row_idx, missing in enumerate(ontbrekende_mask, start=2):
                    if missing:
                        for cell in ws[row_idx]:
                            cell.fill = fill

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
        else:
            st.error("❌ Kolommen ontbreken in de Excelbestanden.")