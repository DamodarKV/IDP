import os
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from routers.core import get_navigation_structure

router = APIRouter()
templates = Jinja2Templates(directory="templates")
BASE_DIR = "database"

import requests
import json

def fetch_documents():
    url = "https://7frs8tj63h.execute-api.us-east-1.amazonaws.com/dev/idpv3-fetch?type=all"
    payload = {}
    headers = {}

    response = requests.request("GET", url, headers=headers, data=payload)
    fetched_data = json.loads(response.content)
    return fetched_data


@router.get("/{category}", response_class=HTMLResponse)
async def read_category(request: Request, category: str, card: str = None):
    menu_structure = get_navigation_structure()
    category_path = os.path.join(BASE_DIR, category)

    if not os.path.isdir(category_path):
        raise HTTPException(status_code=404, detail="Category not found")

    # Keep scanning subdirectories for the UI cards
    cards = []
    for sub_entry in sorted(os.listdir(category_path)):
        if os.path.isdir(os.path.join(category_path, sub_entry)):
            cards.append(sub_entry)

    display_name = category.split("_", 1)[-1] if "_" in category else category

    #calls API to fetch data
    api_data = fetch_documents()

    ui_headers = api_data['injected_headers']

    injected_documents = api_data['injected_documents']
    # Format data rows cleanly to match standard table structure expects:
    # [col1, col2, col3, ..., row_action_id]
    cleaned_rows = []
    if card:
        for doc in injected_documents:
            cleaned_rows.append([
                doc["patient_name"],
                doc["id"],
                doc["date"],
                doc["id"]  # The final element used for the 'View' action link
            ])

    return templates.TemplateResponse(
        request=request,
        name="category.html",
        context={
            "request": request,
            "menu": menu_structure,
            "current_page": display_name,
            "category_folder": category,
            "view_type": "category",
            "cards": cards,
            "selected_card": card,
            "excel_headers": ui_headers,
            "excel_rows": cleaned_rows
        }
    )
