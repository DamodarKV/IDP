import os
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")
BASE_DIR = "database"

def get_navigation_structure():
    """Scans only the top-level folders for the navigation links."""
    nav_items = []
    if not os.path.exists(BASE_DIR):
        return nav_items

    for entry in sorted(os.listdir(BASE_DIR)):
        full_path = os.path.join(BASE_DIR, entry)
        if os.path.isdir(full_path):
            display_name = entry.split("_", 1)[-1] if "_" in entry else entry
            nav_items.append({"folder_name": entry, "name": display_name})
    return nav_items

def sanitize_value(val):
    """Normalizes missing values into a standardized 'Not Available' string."""
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ["nan", "null", "not available", "not_available"]:
        return "Not Available"
    return val_str

@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    menu_structure = get_navigation_structure()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "menu": menu_structure,
            "current_page": "Home",
            "view_type": "home"
        }
    )
