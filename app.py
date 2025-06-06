
import streamlit as st
import tempfile
import os
from your_parser_module import extract_text_from_pdf, call_extraction
from json_to_excel_formatters import json_to_excel_leap, json_to_excel_cfm
from schemas import leap_schema, cfm_schema

st.set_page_config(page_title="Aircraft PDF Parser", layout="wide")

st.title("✈️ Aircraft Service Bulletin Parser")

# Engine type toggle
engine_type = st.radio(
    "Select Engine Type:",
    options=["CFM", "LEAP"],
    index=0,
    horizontal=True,
    help="Choose the engine type for parsing configuration"
)
st.markdown(f"**Selected Engine Type:** {engine_type}")

uploaded_files = st.file_uploader("Upload PDF(s)", type="pdf", accept_multiple_files=True)

if uploaded_files is not None and len(uploaded_files) > 0:
    for uploaded_file in uploaded_files:
        filename = uploaded_file.name
        st.markdown(f"#### 📄 Processing: `{filename}`")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name

        try:
            raw_text = extract_text_from_pdf(tmp_path)
            structured_json, is_cfm = call_extraction(raw_text, engine_type, leap_schema, cfm_schema)

            # Save results
            out_dir = "/mnt/data/json_outputs"
            os.makedirs(out_dir, exist_ok=True)

            json_path = os.path.join(out_dir, filename.replace(".pdf", ".json"))
            with open(json_path, "w") as f:
                f.write(json.dumps(structured_json, indent=2))

            st.success("✅ Extraction complete")
            st.download_button("📄 Download JSON", data=json.dumps(structured_json, indent=2), file_name=filename.replace(".pdf", ".json"))

            if is_cfm:
                excel_path = json_to_excel_cfm(structured_json, filename)
            else:
                excel_path = json_to_excel_leap(structured_json, filename)

            with open(excel_path, "rb") as f:
                st.download_button("📊 Download Excel", data=f, file_name=os.path.basename(excel_path))

        except Exception as e:
            st.error(f"❌ Error processing {filename}: {e}")
        finally:
            os.unlink(tmp_path)
