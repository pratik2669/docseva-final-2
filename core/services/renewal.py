from __future__ import annotations

from urllib.parse import quote_plus

RENEWAL_REQUIREMENTS = {
    "id": {
        "label": "Government ID renewal",
        "required_documents": [
            "Current/expired ID copy",
            "Recent passport-size photo",
            "Address proof",
            "Identity proof",
            "Mobile number linked with the document",
        ],
        "places": "Aadhaar Seva Kendra or government document renewal center",
    },
    "prescription": {
        "label": "Prescription renewal",
        "required_documents": [
            "Previous prescription",
            "Recent diagnosis or lab report if available",
            "Doctor consultation notes",
            "Patient ID proof",
        ],
        "places": "registered clinic, hospital, or telemedicine consultation",
    },
    "lab": {
        "label": "Lab report refresh",
        "required_documents": [
            "Doctor prescription if required",
            "Previous report copy",
            "Patient ID proof",
            "Fasting/medical preparation details if applicable",
        ],
        "places": "diagnostic lab near me",
    },
    "imaging": {
        "label": "Scan/imaging refresh",
        "required_documents": [
            "Doctor referral/prescription",
            "Previous scan/report copy",
            "Patient ID proof",
            "Implant/allergy information if applicable",
        ],
        "places": "MRI CT scan diagnostic center near me",
    },
    "other": {
        "label": "Document renewal",
        "required_documents": [
            "Current/expired document copy",
            "Identity proof",
            "Address proof if required",
            "Passport-size photo if required",
            "Application/reference number if available",
        ],
        "places": "document renewal center near me",
    },
}


def get_renewal_info(category: str) -> dict:
    return RENEWAL_REQUIREMENTS.get(category, RENEWAL_REQUIREMENTS["other"])


def renewal_map_url(document, location: str = "") -> str:
    info = get_renewal_info(document.category)
    location_part = location.strip() or "near me"
    query = f"{info['places']} for {document.title} {location_part}"
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(query)
