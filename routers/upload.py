import os
import requests
from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from routers.core import get_navigation_structure
import time
from uuid import uuid4
import json
import requests

router = APIRouter(prefix="/upload")
templates = Jinja2Templates(directory="templates")



# Define allowed validation target file formats
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

# Maps a file extension to the Content-Type expected by the bucket endpoint
CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}

# The API Gateway route that fronts the storage bucket. Files are uploaded
# with PUT https://.../dev/{bucket_name}/{file_name}
UPLOAD_API_ROOT = "https://7frs8tj63h.execute-api.us-east-1.amazonaws.com/dev"
UPLOAD_BUCKET_NAME = "idpv3.0-pdf-trigger"

def raw_process(payload):
    print(payload)
    url = "https://7frs8tj63h.execute-api.us-east-1.amazonaws.com/dev/idpv3-rawprocess"

    body = {"selected keys": payload}
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.request("POST", url, headers=headers, json=body)

    print(response.text)
    return response



def fetch_keys(file_name):

    print("Hi")
    url = f"https://7frs8tj63h.execute-api.us-east-1.amazonaws.com/dev/idpv3-fetch-keys?filename={file_name}"

    payload = {}
    headers = {}

    response = requests.request("POST", url, headers=headers, data=payload)
    extracted_keys = json.loads(response.content)

    print(f"Extracted Keys:{extracted_keys}")
    return extracted_keys["Available Keys"]


def upload_file_to_bucket(filename: str, file_bytes: bytes, content_type: str) -> str:
    """PUTs raw file bytes to the bucket-backed API Gateway endpoint.

    Returns the object's URL, e.g.
    https://7frs8tj63h.execute-api.us-east-1.amazonaws.com/dev/idpv3.0-pdf-trigger/document4.pdf
    which doubles as the preview/source URL for the uploaded file.
    """
    filename = str(uuid4()).replace('-','')
    print(filename)
    url = f"{UPLOAD_API_ROOT}/{UPLOAD_BUCKET_NAME}/{filename}.pdf"
    headers = {"Content-Type": content_type}

    response = requests.put(url, headers=headers, data=file_bytes)
    response.raise_for_status()
    print("Document is getting Pocessed for 300 seconds")
    #time.sleep(360)
    return url

@router.post("/process", response_class=HTMLResponse)
async def process_file_upload(request: Request, file: UploadFile = File(...)):
    filename = file.filename
    _, ext = os.path.splitext(filename.lower())

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Only PDF, JPG, and PNG configurations are allowed."
        )

    file_bytes = await file.read()
    content_type = CONTENT_TYPES.get(ext, file.content_type or "application/octet-stream")

    try:

        preview_url = upload_file_to_bucket(filename, file_bytes, content_type)

    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to upload '{filename}' to the storage bucket: {exc}"
        )

    # Redirect back to workbench displaying live preview frame, now backed
    # by the bucket-hosted file rather than a local temp copy.
    return await upload_workspace(request, file_path=preview_url)



@router.get("/workspace", response_class=HTMLResponse)
async def upload_workspace(request: Request, file_path: str = None):
    menu_structure = get_navigation_structure()

    # Pre-defined schema extraction checklist keys displayed on the right-hand workbench panel

    extraction_keys = ["Please Upload the file to Get the Keys"]
    if file_path != None:
        file_name = f"{file_path.split('/')[-1].split('.')[0]}"
        print(file_name)

        extraction_keys = [
        "Patient Name",
        "Preferred Name",
        "Patient Identifier",
        "Gender",
        "Date of Birth",
        "Blood Type",
        "Last Updated Date",
        "Address",
        "Emergency Contacts",
        "Insurance Information",
        "Physicians",
        "Known Medical Conditions",
        "Allergies",
        "Ingestion Date",
            f"ID_{file_name}"
    ]

    return templates.TemplateResponse(
        request=request,
        name="upload.html",
        context={
            "request": request,
            "menu": menu_structure,
            "current_page": "Upload Documents",
            "view_type": "upload_view",
            "preview_url": file_path,
            "extraction_keys": extraction_keys
        }
    )



# Add this import at the top of your routers/upload.py file
from pydantic import BaseModel
from typing import List


# Define the expected JSON payload schema mapping structure
class ExtractionPayload(BaseModel):
    keys: List[str]


# Append this new endpoint to the bottom of routers/upload.py
@router.post("/extract-parameters")
async def extract_parameters(payload: ExtractionPayload):
    print(type(payload))
    print(payload)
    raw_process(payload.keys)
    #time.sleep(180)
    print("\n" + "=" * 50)
    print("🚀 INCOMING EXTRACTION PARAMETERS RECEIVED IN BACKEND:")
    for index, key in enumerate(payload.keys, 1):
        print(f"  [{index}] -> {key}")
    print("=" * 50 + "\n")

    return {"status": "success", "processed_keys_count": len(payload.keys)}
