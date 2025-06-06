
import os
import io
import streamlit as st
import pandas as pd
from pathlib import Path
from your_parser_module import extract_text_from_pdf, call_extraction, detect_engine_type_from_filename, leap_schema, cfm_schema

st.set_page_config(page_title="PDF→Excel Parser", layout="wide")

st.title("📄 PDF → Excel Parser")
st.markdown(
    """
Upload a single PDF, choose which schema to run (CFM or LEAP), and get back a downloadable Excel.
"""
)

# Toggle for schema choice
schema_choice = st.radio("Choose engine schema:", ("CFM", "LEAP"))

uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])
if not uploaded_file:
    st.info("Please upload a PDF to get started.")
    st.stop()

if st.button("Process PDF"):
    temp_path = Path("/tmp") / uploaded_file.name
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getvalue())

    try:
        pdf_text = extract_text_from_pdf(str(temp_path))
    except Exception as e:
        st.error(f"Failed to extract text: {e}")
        st.stop()

    if schema_choice == "CFM":
        schema = cfm_schema
        engine_type = "CFM"
    else:
        schema = leap_schema
        engine_type = "LEAP"

    try:
        with st.spinner("Calling LLM to parse PDF..."):
            parsed = call_extraction(pdf_text, schema)
    except Exception as e:
        st.error(f"LLM parse error: {e}")
        st.stop()

    if st.checkbox("Show raw JSON output"):
        st.json(parsed)

    # Build Excel
    meta = parsed.get("documentInfo", {})
    flat_meta = {}
    for key, val in meta.items():
        if isinstance(val, (dict, list)):
            flat_meta[key] = pd.io.json.dumps(val)
        else:
            flat_meta[key] = val
    flat_meta["engine_type"] = engine_type
    flat_meta["filename"] = uploaded_file.name

    meta_df = pd.DataFrame([flat_meta])

    tables = {}
    if engine_type == "LEAP":
        mat = parsed.get("materialInformation", {})
        spares = mat.get("listOfSpares", [])
        removed = mat.get("listOfRemovedSpares", [])
        if isinstance(spares, list) and spares:
            tables["ListOfSpares"] = spares
        if isinstance(removed, list) and removed:
            tables["RemovedSpares"] = removed
    else:
        mat = parsed.get("materialInformation", {})
        parts = mat.get("parts", [])
        config_changes = parsed.get("configurationChanges", [])
        if isinstance(parts, list) and parts:
            tables["Parts"] = parts
        if isinstance(config_changes, list) and config_changes:
            tables["ConfigurationChanges"] = config_changes

    output_buffer = io.BytesIO()
    with pd.ExcelWriter(output_buffer, engine="xlsxwriter") as writer:
        meta_df.to_excel(writer, sheet_name="Metadata", index=False)
        for sheet_name, rows in tables.items():
            df = pd.DataFrame(rows)
            if "documentTitle" in meta:
                df.insert(0, "DocumentTitle", meta.get("documentTitle", ""))
            elif "documentName" in meta:
                df.insert(0, "DocumentName", meta.get("documentName", ""))
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    output_buffer.seek(0)

    download_name = f"{Path(uploaded_file.name).stem}_{engine_type}.xlsx"
    st.download_button(
        label="⬇️ Download Excel",
        data=output_buffer,
        file_name=download_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
