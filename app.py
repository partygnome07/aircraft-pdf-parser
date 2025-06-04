
import streamlit as st
import os
import pandas as pd
import json
from tempfile import NamedTemporaryFile
from your_parser_module import extract_text_from_pdf, call_extraction, format_output

st.set_page_config(page_title="Aircraft PDF Parser", layout="centered")
st.title("🛠️ Aircraft Service Bulletin Parser")

st.markdown("Upload one or more PDFs to extract metadata and spare parts into Excel and JSON.")

uploaded_files = st.file_uploader("Upload PDFs", type="pdf", accept_multiple_files=True)

if uploaded_files:
    all_results = []
    with st.spinner("📤 Extracting and parsing all PDFs..."):
        for file in uploaded_files:
            with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(file.read())
                tmp_file_path = tmp_file.name

            raw_text = extract_text_from_pdf(tmp_file_path)
            structured_json = call_extraction(raw_text)
            meta_df, spares_df, removed_df = format_output(structured_json)

            all_results.append({
                "filename": file.name,
                "meta_df": meta_df,
                "spares_df": spares_df,
                "removed_df": removed_df,
                "raw_json": structured_json
            })

    st.success("✅ Extraction Complete!")

    for result in all_results:
        st.header(f"📄 {result['filename']}")
        st.subheader("Metadata")
        st.dataframe(result["meta_df"])

        st.subheader("List of Spares")
        st.dataframe(result["spares_df"])

        st.subheader("List of Removed Spares")
        st.dataframe(result["removed_df"])

    # Export all results to single Excel and JSON
    excel_path = NamedTemporaryFile(delete=False, suffix=".xlsx").name
    with pd.ExcelWriter(excel_path, engine="xlsxwriter") as writer:
        for result in all_results:
            base = os.path.splitext(result["filename"])[0].replace(" ", "_")[:20]
            result["meta_df"].to_excel(writer, sheet_name=f"{base}_Meta", index=False)
            result["spares_df"].to_excel(writer, sheet_name=f"{base}_Spares", index=False)
            result["removed_df"].to_excel(writer, sheet_name=f"{base}_Removed", index=False)

    # Combine JSONs
    combined_json = {res["filename"]: res["raw_json"] for res in all_results}
    json_bytes = json.dumps(combined_json, indent=2).encode("utf-8")

    st.download_button("📥 Download Excel (All PDFs)", data=open(excel_path, "rb"), file_name="Parsed_Results_Batch.xlsx")
    st.download_button("📥 Download JSON (All PDFs)", data=json_bytes, file_name="Parsed_Results_Batch.json")
