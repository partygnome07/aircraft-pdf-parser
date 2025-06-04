
import os
import json
import openai
import pdfplumber
import pandas as pd

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)

aircraft_service_bulletin_schema = {
    "name": "parse_aircraft_service_bulletin",
    "description": "Extracts comprehensive document metadata and parts tables from aircraft service bulletins.",
    "parameters": {
        "type": "object",
        "properties": {
            "documentInfo": {
                "type": "object",
                "properties": {
                    "documentName": {"type": ["string", "null"]},
                    "title": {"type": ["string", "null"]},
                    "date": {"type": ["string", "null"]},
                    "taskType": {"type": ["string", "null"]},
                    "originalIssueDate": {"type": ["string", "null"]},
                    "reasonsForUpdate": {"type": ["string", "null"]},
                    "manufacturerRecommendation": {"type": ["string", "null"]},
                    "revisionInformation": {
                        "type": "object",
                        "properties": {
                            "revisionReason": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "issueNumber": {"type": ["string", "null"]},
                                        "revisionReason": {"type": ["string", "null"]}
                                    }
                                }
                            },
                            "revisionHistory": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "issueNumber": {"type": ["string", "null"]},
                                        "issueDate": {"type": ["string", "null"]}
                                    }
                                }
                            }
                        }
                    },
                    "summary": {
                        "type": "object",
                        "properties": {
                            "reason": {"type": ["string", "null"]}
                        }
                    },
                    "planningInformation": {
                        "type": "object",
                        "properties": {
                            "applicability": {
                                "type": "object",
                                "properties": {
                                    "engineType": {"type": ["string", "null"]},
                                    "engineModels": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    }
                                }
                            },
                            "description": {"type": ["string", "null"]},
                            "compliance": {
                                "type": "object",
                                "properties": {
                                    "category": {"type": ["string", "null"]},
                                    "impact": {"type": ["string", "null"]},
                                    "impactDescription": {"type": ["string", "null"]}
                                }
                            }
                        }
                    },
                    "materialInformation": {
                        "type": "object",
                        "properties": {
                            "listOfMaterialSets": {"type": ["string", "null"]},
                            "listOfSupportEquipment": {"type": ["string", "null"]},
                            "listOfSupplies": {"type": ["string", "null"]}
                        }
                    }
                }
            },
            "listOfSpares": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "newPN": {"type": ["string", "null"]},
                        "sin": {"type": ["string", "null"]},
                        "mfr": {"type": ["string", "null"]},
                        "qty": {"type": ["string", "null"]},
                        "unitPrice": {"type": ["string", "null"]},
                        "pkgQty": {"type": ["string", "null"]},
                        "leadTime": {"type": ["string", "null"]},
                        "newPartName": {"type": ["string", "null"]},
                        "csn": {"type": ["string", "null"]},
                        "notes": {"type": ["string", "null"]}
                    }
                }
            },
            "listOfRemovedSpares": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "newPN": {"type": ["string", "null"]},
                        "newSIN": {"type": ["string", "null"]},
                        "newMFR": {"type": ["string", "null"]},
                        "oldPN": {"type": ["string", "null"]},
                        "oldSIN": {"type": ["string", "null"]},
                        "oldMFR": {"type": ["string", "null"]},
                        "oldCSN": {"type": ["string", "null"]},
                        "qty": {"type": ["string", "null"]},
                        "operationCode": {"type": ["string", "null"]},
                        "notes": {"type": ["string", "null"]}
                    }
                }
            }
        },
        "required": ["documentInfo", "listOfSpares", "listOfRemovedSpares"]
    }
}

def call_extraction(text: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.0,
        messages=[
            {"role": "system", "content": "You are a PDF data extractor."},
            {"role": "user", "content": text}
        ],
        functions=[aircraft_service_bulletin_schema],
        function_call={"name": aircraft_service_bulletin_schema["name"]}
    )
    args = response.choices[0].message.function_call.arguments
    return json.loads(args)

def format_output(parsed_json: dict):
    meta_df = pd.json_normalize(parsed_json.get("documentInfo", {}))
    spares_df = pd.DataFrame(parsed_json.get("listOfSpares", []))
    removed_df = pd.DataFrame(parsed_json.get("listOfRemovedSpares", []))
    return meta_df, spares_df, removed_df
