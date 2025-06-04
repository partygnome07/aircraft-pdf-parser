
import streamlit as st
import os
import pandas as pd
import json
from tempfile import NamedTemporaryFile
from your_parser_module import extract_text_from_pdf, call_extraction, format_output

st.set_page_config(page_title="Aircraft PDF Parser", layout="centered")
st.title("🛠️ Aircraft Service Bulletin Parser")

st.markdown("Upload a PDF below to extract metadata and spare parts into Excel and JSON.")

uploaded_file = st.file_uploader("Upload PDF", type="pdf")

if uploaded_file:
    with st.spinner("📄 Extracting text from PDF..."):
        with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_file_path = tmp_file.name

        raw_text = extract_text_from_pdf(tmp_file_path)

    with st.spinner("Extracting Data"):
        structured_json = call_extraction(raw_text)

    with st.spinner("📊 Formatting extracted data..."):
        meta_df, spares_df = format_output(structured_json)

    st.success("Extraction Complete")

    st.subheader("Metadata")
    st.dataframe(meta_df)

    st.subheader("List of Spares")
    st.dataframe(spares_df)

    json_bytes = json.dumps(structured_json, indent=2).encode("utf-8")

    with NamedTemporaryFile(delete=False, suffix=".xlsx") as excel_tmp:
        excel_path = excel_tmp.name
        with pd.ExcelWriter(excel_path, engine="xlsxwriter") as writer:
            meta_df.to_excel(writer, sheet_name="Metadata", index=False)
            spares_df.to_excel(writer, sheet_name="ListOfSpares", index=False)

    st.download_button("📥 Download Excel", data=open(excel_path, "rb"), file_name="Parsed_Output.xlsx")
    st.download_button("📥 Download JSON", data=json_bytes, file_name="Parsed_Output.json")
