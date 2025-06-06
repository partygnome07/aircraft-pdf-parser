
import os
import json
import pandas as pd
import pdfplumber
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)

def call_extraction(text: str, engine_type: str, leap_schema: dict, cfm_schema: dict) -> tuple:
    is_cfm = engine_type.upper() == "CFM"
    schema = cfm_schema if is_cfm else leap_schema
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.0,
        messages=[
            {"role": "system", "content": "You are a pdf data extractor."},
            {"role": "user", "content": text}
        ],
        functions=[schema],
        function_call={"name": schema["name"]}
    )
    args = response.choices[0].message.function_call.arguments
    return json.loads(args), is_cfm
