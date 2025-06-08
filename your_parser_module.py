
import os
import json
import openai
import pandas as pd
import pdfplumber

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)

# ---------------- SCHEMAS ----------------

cfm_schema = {
    "name": "parse_cfm_service_bulletin",
    "description": "Extracts CFM bulletin info.",
    "parameters": {
        "type": "object",
        "properties": {
            "documentInfo": {
                "type": "object",
                "properties": {
                    "documentTitle": {"type": ["string", "null"]},
                    "serviceBulletinNumber": {"type": ["string", "null"]},
                    "revisionNumber": {"type": ["string", "null"]},
                    "issueDate": {"type": ["string", "null"]},
                    "revisionDate": {"type": ["string", "null"]},
                    "ataChapter": {"type": ["string", "null"]},
                    "engineModels": {"type": "array", "items": {"type": "string"}},
                    "category": {"type": ["string", "null"]},
                    "complianceType": {"type": ["string", "null"]}
                }
            },
            "reason": {"type": "object"},
            "materialInformation": {"type": "object"},
            "configurationChanges": {"type": "array"},
            "compliance": {"type": "object"},
            "tooling": {"type": "array"},
            "approval": {"type": "string"},
            "industrySupport": {"type": ["string", "null"]}
        },
        "required": ["documentInfo", "reason", "materialInformation"]
    }
}

leap_schema = {
    "name": "parse_leap_service_bulletin",
    "description": "Extracts LEAP bulletin info.",
    "parameters": {
        "type": "object",
        "properties": {
            "documentInfo": {
                "type": "object"
            },
            "listOfSpares": {
                "type": "array",
                "items": {"type": "object"}
            },
            "listOfRemovedSpares": {
                "type": "array",
                "items": {"type": "object"}
            }
        },
        "required": ["documentInfo", "listOfSpares", "listOfRemovedSpares"]
    }
}

# ---------------- CALL LOGIC ----------------

def call_extraction(text: str, filename: str):
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

# ---------------- FORMATTERS ----------------

def format_output(json_data: dict, is_cfm: bool):
    if is_cfm:
        doc_info = json_data.get("documentInfo", {})
        reason_info = json_data.get("reason", {})
        compliance_info = json_data.get("compliance", {})
        material_info = json_data.get("materialInformation", {})
        config_changes = json_data.get("configurationChanges", [])

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
            "Approval": json_data.get("approval"),
            "Industry Support": json_data.get("industrySupport"),
            "Tooling Required": ", ".join(json_data.get("tooling", [])),
        }

        meta_df = pd.DataFrame([meta_flat])
        parts_df = pd.DataFrame(material_info.get("parts", []))
        config_df = pd.DataFrame(config_changes)
        return meta_df, parts_df, config_df

    else:
        doc_info = json_data.get("documentInfo", {})
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
        spares_df = pd.DataFrame(doc_info.get("listOfSpares", []))
        removed_df = pd.DataFrame(doc_info.get("listOfRemovedSpares", []))
        return meta_df, spares_df, removed_df
