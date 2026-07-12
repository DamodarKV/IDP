import os
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from routers.core import get_navigation_structure
import requests
import json

router = APIRouter()
templates = Jinja2Templates(directory="templates")
BASE_DIR = "database"

def fetch_document(id):
    url = f"https://7frs8tj63h.execute-api.us-east-1.amazonaws.com/dev/idpv3-fetch-document?file_name={id}"
    payload = {}
    headers = {}

    response = requests.request("GET", url, headers=headers, data=payload)
    patient_data = json.loads(response.content)
    return patient_data

def update_document(payload):
    url = "https://7frs8tj63h.execute-api.us-east-1.amazonaws.com/dev/idpv3-update-file"
    # Optional: Add headers if your API requires them
    headers = {
        "Content-Type": "application/json"
    }

    # 3. Post the payload using the 'json' parameter
    requests.post(url, headers=headers, json=payload)


# Ordered set of raw metadata keys exposed on the edit form.
# Mirrors the schema used in routers/upload.py's extraction workbench.
EDITABLE_METADATA_FIELDS = [
    "First name", "Last name", "Preferred name", "Gender",
    "Date of birth", "Patient identifier", "ID",
    "Address", "City", "State", "Zip code", "Contact number",
    "Insurance carrier", "Insurance plan", "Policy number", "Group number",
    "Blood type", "Known medical conditions", "Relationship",
    "Ingested Date", "Last updated date"
]



@router.get("/{category}/{subfolder}/{invoice_id}", response_class=HTMLResponse)
async def view_invoice_details(request: Request, category: str, subfolder: str, invoice_id: str):
    menu_structure = get_navigation_structure()

    # Strip whitespace to prevent key mismatch lookups
    target_id = invoice_id.strip()

    MOCK_PROFILES = fetch_document(target_id)

    if target_id not in MOCK_PROFILES:
        raise HTTPException(status_code=404, detail="Document profile log could not be discovered.")

    profile_data = MOCK_PROFILES[target_id]
    mock_meta = profile_data["metadata"]

    # Reconstruct keys exactly as expected by left-properties-sidebar in profile.html
    left_metadata = {
        "Patient Name": f"{mock_meta.get('First name', '')} {mock_meta.get('Last name', '')}".strip(),
        "Patient DOB": mock_meta.get("Date of birth", "Not Available"),
        "Patient MRN": mock_meta.get("Patient identifier", "Not Available"),
        "Ingested Date": mock_meta.get("Ingested Date", "Not Available"),
        "Member ID": mock_meta.get("ID", "Not Available")
    }

    right_summary = profile_data.get("summary", "Not Available")
    pdf_static_route = profile_data.get("file_name", "")

    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={
            "request": request,
            "menu": menu_structure,
            "current_page": f"Record Profile: {target_id}",
            "view_type": "invoice_view",
            "left_metadata": left_metadata,
            "right_summary": right_summary,
            "pdf_url": pdf_static_route,
            "back_url": f"/{category}?card={subfolder}",
            # BIND THESE PATH STRINGS SO YOUR TEMPLATE GENERATES THE CORRECT LINK:
            "category_folder": category,
            "selected_card": subfolder
        }
    )


@router.get("/{category}/{subfolder}/{invoice_id}/edit", response_class=HTMLResponse)
async def edit_invoice_details(request: Request, category: str, subfolder: str, invoice_id: str, saved: bool = False):
    menu_structure = get_navigation_structure()
    target_id = invoice_id.strip()

    MOCK_PROFILES = fetch_document(target_id)

    if target_id not in MOCK_PROFILES:
        raise HTTPException(status_code=404, detail="Document profile log could not be discovered.")

    profile_data = MOCK_PROFILES[target_id]
    mock_meta = profile_data.get("metadata", {})
    print(f"Mock Data:{mock_meta}")
    # Build the editable field list, pulling values straight from raw metadata
    # so nothing is lost to the display-only reshaping used in the read view.
    editable_fields = [
        {"key": key, "value": mock_meta.get(key, "")}
        for key in list(mock_meta.keys())
    ]

    print(f"Editable Fields:{editable_fields}")
    return templates.TemplateResponse(
        request=request,
        name="profile_edit.html",
        context={
            "request": request,
            "menu": menu_structure,
            "current_page": f"Edit Record: {target_id}",
            "view_type": "invoice_edit",
            "editable_fields": editable_fields,
            "summary_text": profile_data.get("summary", ""),
            "pdf_url": profile_data.get("file_name", ""),
            "invoice_id": target_id,
            "category_folder": category,
            "selected_card": subfolder,
            "saved": saved
        }
    )


@router.post("/{category}/{subfolder}/{invoice_id}/edit")
async def save_invoice_details(request: Request, category: str, subfolder: str, invoice_id: str):
    # NOTE: Persistence is not wired up yet. This placeholder captures the
    # submitted form values so the endpoint (and UI round-trip) can be tested
    # before a real save target (API call or local store) is decided on.
    form = await request.form()
    submitted = dict(form)

    print(submitted)

    payload = submitted
    update_document(payload)


    # TODO: replace with an actual save (external API call or local storage)
    # once the persistence approach is decided.

    return RedirectResponse(
        url=f"/{category}/{subfolder}/{invoice_id}",
        status_code=303
    )
