
import os
import json
import pandas as pd
import pdfplumber
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)

def call_extraction(text: str, filename: str, leap_schema: dict, cfm_schema: dict) -> tuple:
    is_cfm = "cfm" in filename.lower()
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

def format_output(data: dict, is_cfm: bool, filename: str, output_dir: str = "/mnt/data"):
    safe_name = filename.replace(".pdf", "").replace(" ", "_")
    excel_output_path = os.path.join(output_dir, f"{safe_name}_Parsed.xlsx")

    if is_cfm:
        doc_info = data.get("documentInfo", {})
        reason_info = data.get("reason", {})
        compliance_info = data.get("compliance", {})
        material_info = data.get("materialInformation", {})
        config_changes = data.get("configurationChanges", [])

        meta_flat = {
            "Document Title": doc_info.get("documentTitle"),
            "Service Bulletin Number": doc_info.get("serviceBulletinNumber"),
            "Revision Number": doc_info.get("revisionNumber"),
            "Issue Date": doc_info.get("issueDate"),
            "Revision Date": doc_info.get("revisionDate"),
            "ATA Chapter": doc_info.get("ataChapter"),
            "Engine Models": ", ".join(doc_info.get("engineModels", [])),
            "Category": doc_info.get("category"),
            "Compliance Type": doc_info.get("complianceType"),
            "Objective": reason_info.get("objective"),
            "Condition": reason_info.get("condition"),
            "Cause": reason_info.get("cause"),
            "Improvement": reason_info.get("improvement"),
            "Substantiation": reason_info.get("substantiation"),
            "Compliance Type (Repeat)": compliance_info.get("complianceType"),
            "Manpower Hours": compliance_info.get("manpowerHours"),
            "Weight Impact": compliance_info.get("weightImpact"),
            "Balance Impact": compliance_info.get("balanceImpact"),
            "Approval": data.get("approval"),
            "Industry Support": data.get("industrySupport"),
            "Tooling Required": ", ".join(data.get("tooling", [])),
        }

        meta_df = pd.DataFrame([meta_flat])
        parts_df = pd.DataFrame(material_info.get("parts", []))
        config_df = pd.DataFrame(config_changes)

        with pd.ExcelWriter(excel_output_path, engine="xlsxwriter") as writer:
            meta_df.to_excel(writer, sheet_name="Metadata", index=False)
            if not parts_df.empty:
                parts_df.insert(0, "Document Title", doc_info.get("documentTitle"))
                parts_df.to_excel(writer, sheet_name="Parts List", index=False)
            if not config_df.empty:
                config_df.insert(0, "Document Title", doc_info.get("documentTitle"))
                config_df.to_excel(writer, sheet_name="Configuration Changes", index=False)

    else:
        doc_info = data.get("documentInfo", {})
        planning_info = doc_info.get("planningInformation", {})
        revision_info = doc_info.get("revisionInformation", {})

        meta_flat = {
            "Document Name": doc_info.get("documentName"),
            "Title": doc_info.get("title"),
            "Date": doc_info.get("date"),
            "Reasons for Update": doc_info.get("reasonsForUpdate"),
            "Manufacturer Recommendation": doc_info.get("manufacturerRecommendation"),
            "Task Type": doc_info.get("taskType"),
            "Original Issue Date": doc_info.get("originalIssueDate"),
            "Revision Reason - Issue Number": revision_info.get("revisionReason", [{}])[0].get("issueNumber"),
            "Revision Reason - Text": revision_info.get("revisionReason", [{}])[0].get("revisionReason"),
            "Revision History - Issue Number": revision_info.get("revisionHistory", [{}])[0].get("issueNumber"),
            "Revision History - Issue Date": revision_info.get("revisionHistory", [{}])[0].get("issueDate"),
            "Summary Reason": doc_info.get("summary", {}).get("reason"),
            "Engine Type": planning_info.get("applicability", {}).get("engineType"),
            "Engine Models": ", ".join(planning_info.get("applicability", {}).get("engineModels", [])),
            "Concurrent Requirements": planning_info.get("concurrentRequirements"),
            "Objective": planning_info.get("reason", {}).get("objective"),
            "Condition": planning_info.get("reason", {}).get("condition"),
            "Cause": planning_info.get("reason", {}).get("cause"),
            "Improvement": planning_info.get("reason", {}).get("improvement"),
            "Substantiation": planning_info.get("reason", {}).get("substantiation"),
            "Description": planning_info.get("description"),
            "Compliance Category": planning_info.get("compliance", {}).get("category"),
            "Compliance Impact": planning_info.get("compliance", {}).get("impact"),
            "Compliance Description": planning_info.get("compliance", {}).get("impactDescription"),
            "Approval": planning_info.get("approval"),
            "Manpower": planning_info.get("manpower"),
            "Weight and Balance": planning_info.get("weightAndBalance"),
            "Electrical Load Data": planning_info.get("electricalLoadData"),
            "Software Summary": planning_info.get("softwareAccomplishmentSummary"),
            "Referenced Docs": planning_info.get("referencedDocumentation"),
            "Docs Affected": planning_info.get("documentationAffected"),
            "Industry Support Info": planning_info.get("industrySupportInformation"),
            "Interchangeability": planning_info.get("interchangeability"),
        }

        meta_df = pd.DataFrame([meta_flat])
        spares = doc_info.get("listOfSpares", []) or doc_info.get("materialInformation", {}).get("listOfSpares", [])
        removed_spares = doc_info.get("listOfRemovedSpares", []) or doc_info.get("materialInformation", {}).get("listOfRemovedSpares", [])

        spares_df = pd.DataFrame(spares if isinstance(spares, list) else [])
        removed_spares_df = pd.DataFrame(removed_spares if isinstance(removed_spares, list) else [])

        with pd.ExcelWriter(excel_output_path, engine="xlsxwriter") as writer:
            meta_df.to_excel(writer, sheet_name="Metadata", index=False)
            spares_df.to_excel(writer, sheet_name="ListOfSpares", index=False)
            removed_spares_df.to_excel(writer, sheet_name="RemovedSpares", index=False)

    print(f"📥 Excel created for {filename}: {excel_output_path}")
