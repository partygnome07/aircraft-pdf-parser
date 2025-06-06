import os
import json
import pdfplumber
import openai

# ──────────────────────────────────────────────────────────────────────────────
# Configure OpenAI (v1.x client)
client = openai.OpenAI()
if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("❌ Please set OPENAI_API_KEY environment variable before running.")

def extract_text_from_pdf(path: str) -> str:
    full_text = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                full_text.append(t)
    return "\n".join(full_text)

def call_extraction(pdf_text: str, function_schema: dict) -> dict:
    """
    Uses the new openai client (v1.x) to call the function schema.
    """
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.0,
        messages=[
            {"role": "system", "content": "You are a pdf data extractor."},
            {"role": "user",   "content": pdf_text}
        ],
        functions=[function_schema],
        function_call={"name": function_schema["name"]},
    )
    args = resp.choices[0].message.function_call.arguments
    return json.loads(args)

def detect_engine_type_from_filename(pdf_path: str) -> str:
    lower = pdf_path.lower()
    if "cfm" in lower:
        return "CFM"
    return "LEAP"

# ──────────────────────────────────────────────────────────────────────────────
# LEAP schema
leap_schema = {
    "name": "parse_leap_service_bulletin",
    "description": "Extracts metadata and parts info from LEAP service bulletins.",
    "parameters": {
        "type": "object",
        "properties": {
            "documentInfo": {
                "type": "object",
                "properties": {
                    "documentName":            {"type": ["string","null"]},
                    "title":                   {"type": ["string","null"]},
                    "date":                    {"type": ["string","null"]},
                    "reasonsForUpdate":        {"type": ["string","null"]},
                    "manufacturerRecommendation": {"type": ["string","null"]},
                    "taskType":                {"type": ["string","null"]},
                    "originalIssueDate":       {"type": ["string","null"]},
                    "revisionInformation":     {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "revisionReason": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "issueNumber": {"type": ["string","null"]},
                                            "revisionReason": {"type": ["string","null"]}
                                        }
                                    }
                                },
                                "revisionHistory": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "issueNumber": {"type": ["string","null"]},
                                            "issueDate": {"type": ["string","null"]}
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "summary": {
                        "type": "object",
                        "properties": {
                            "reason": {"type": ["string","null"]}
                        }
                    },
                    "planningInformation": {
                        "type": "object",
                        "properties": {
                            "applicability": {
                                "type": "object",
                                "properties": {
                                    "engineType": {"type": ["string","null"]},
                                    "engineModels": {"type": ["array","null"], "items": {"type": "string"}}
                                }
                            },
                            "concurrentRequirements": {"type": ["string","null"]},
                            "reason": {
                                "type": "object",
                                "properties": {
                                    "objective": {"type": ["string","null"]},
                                    "condition": {"type": ["string","null"]},
                                    "cause": {"type": ["string","null"]},
                                    "improvement": {"type": ["string","null"]},
                                    "substantiation": {"type": ["string","null"]}
                                }
                            },
                            "description": {"type": ["string","null"]},
                            "compliance": {
                                "type": "object",
                                "properties": {
                                    "category": {"type": ["string","null"]},
                                    "impact": {"type": ["string","null"]},
                                    "impactDescription": {"type": ["string","null"]}
                                }
                            },
                            "approval": {"type": ["string","null"]},
                            "manpower": {"type": ["string","null"]},
                            "weightAndBalance": {"type": ["string","null"]},
                            "electricalLoadData": {"type": ["string","null"]},
                            "softwareAccomplishmentSummary": {"type": ["string","null"]},
                            "referencedDocumentation": {"type": ["string","null"]},
                            "documentationAffected": {"type": ["string","null"]},
                            "industrySupportInformation": {"type": ["string","null"]},
                            "interchangeability": {"type": ["string","null"]}
                        }
                    },
                    "materialInformation": {
                        "type": "object",
                        "properties": {
                            "listOfSpares": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "partNumber": {"type": ["string","null"]},
                                        "serialNumber": {"type": ["string","null"]},
                                        "quantity": {"type": ["integer","null"]},
                                        "location": {"type": ["string","null"]},
                                        "remarks": {"type": ["string","null"]}
                                    }
                                }
                            },
                            "listOfRemovedSpares": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "partNumber": {"type": ["string","null"]},
                                        "serialNumber": {"type": ["string","null"]},
                                        "quantity": {"type": ["integer","null"]},
                                        "location": {"type": ["string","null"]},
                                        "remarks": {"type": ["string","null"]}
                                    }
                                }
                            }
                        }
                    }
                },
                "required": ["documentInfo", "materialInformation"]
            }
        },
        "required": ["documentInfo"]
    }
}

# ──────────────────────────────────────────────────────────────────────────────
# CFM schema
cfm_schema = {
    "name": "parse_cfm_service_bulletin",
    "description": "Extracts metadata and parts information from CFM56-5B service bulletins.",
    "parameters": {
        "type": "object",
        "properties": {
            "documentInfo": {
                "type": "object",
                "properties": {
                    "documentTitle": {"type": ["string","null"]},
                    "serviceBulletinNumber": {"type": ["string","null"]},
                    "revisionNumber": {"type": ["string","null"]},
                    "issueDate": {"type": ["string","null"]},
                    "revisionDate": {"type": ["string","null"]},
                    "ataChapter": {"type": ["string","null"]},
                    "engineModels": {
                        "type": "array",
                        "items": {"type": ["string","null"]}
                    },
                    "category": {"type": ["string","null"]},
                    "complianceType": {"type": ["string","null"]}
                }
            },
            "reason": {
                "type": "object",
                "properties": {
                    "objective": {"type": ["string","null"]},
                    "condition": {"type": ["string","null"]},
                    "cause": {"type": ["string","null"]},
                    "improvement": {"type": ["string","null"]},
                    "substantiation": {"type": ["string","null"]}
                }
            },
            "compliance": {
                "type": "object",
                "properties": {
                    "complianceType": {"type": ["string","null"]},
                    "manpowerHours": {"type": ["number","null"]},
                    "weightImpact": {"type": ["number","null"]},
                    "balanceImpact": {"type": ["number","null"]}
                }
            },
            "materialInformation": {
                "type": "object",
                "properties": {
                    "parts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "partNumber": {"type": ["string","null"]},
                                "quantity": {"type": ["integer","null"]},
                                "unitCost": {"type": ["number","null"]},
                                "currency": {"type": ["string","null"]},
                                "notes": {"type": ["string","null"]}
                            }
                        }
                    }
                }
            },
            "configurationChanges": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "oldConfig": {"type": ["string","null"]},
                        "newConfig": {"type": ["string","null"]},
                        "notes": {"type": ["string","null"]}
                    }
                }
            },
            "approval": {"type": ["string","null"]},
            "industrySupport": {"type": ["string","null"]},
            "tooling": {
                "type": "array",
                "items": {"type": ["string","null"]}
            }
        },
        "required": ["documentInfo"]
    }
}
