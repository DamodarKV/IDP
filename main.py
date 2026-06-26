import os
import pandas as pd
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

# Mount the folder system database as static files so browsers can render PDFs securely
app.mount("/static_db", StaticFiles(directory="database"), name="static_db")

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


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    menu_structure = get_navigation_structure()
    return templates.TemplateResponse(
        "base.html",
        {"request": request, "menu": menu_structure, "current_page": "Home", "view_type": "home"}
    )


@app.get("/{category}", response_class=HTMLResponse)
async def read_category(request: Request, category: str, card: str = None):
    menu_structure = get_navigation_structure()
    category_path = os.path.join(BASE_DIR, category)

    if not os.path.isdir(category_path):
        raise HTTPException(status_code=404, detail="Category not found")

    cards = []
    for sub_entry in sorted(os.listdir(category_path)):
        if os.path.isdir(os.path.join(category_path, sub_entry)):
            cards.append(sub_entry)

    display_name = category.split("_", 1)[-1] if "_" in category else category
    ui_headers = ["Patient Member ID", "Patient First Name", "Patient Date of Birth", "NPI", "Patient MRN", "Action"]
    cleaned_rows = []

    if card:
        excel_file_path = os.path.join(category_path, card, f"{card}.xlsx")
        if os.path.exists(excel_file_path):
            try:
                df = pd.read_excel(excel_file_path).fillna("")
                col_map = {str(col).strip().lower(): col for col in df.columns}

                # De-duplicate strictly via Unique Patient Member ID Column
                member_id_col = col_map.get("patient_member_id")
                if member_id_col:
                    df[member_id_col] = df[member_id_col].astype(str).str.strip()
                    df = df.drop_duplicates(subset=[member_id_col], keep="first")

                invoice_col_raw = col_map.get("invoice_id")

                for _, row in df.iterrows():
                    mem_id = sanitize_value(row.get(member_id_col)) if member_id_col else "Not Available"

                    first_name = "Not Available"
                    if "patient_first_name" in col_map:
                        first_name = sanitize_value(row[col_map["patient_first_name"]])
                    elif "patient_name" in col_map:
                        full_name = str(row[col_map["patient_name"]]).strip()
                        if full_name and full_name.lower() not in ["nan", "not available"]:
                            first_name = full_name.split(" ")[0]

                    dob = sanitize_value(
                        row.get(col_map.get("patient_date_of_birth", "")) or row.get(col_map.get("patient_dob", "")))
                    npi = sanitize_value(row.get(col_map.get("npi_id", "")) or row.get(col_map.get("npi", "")))
                    mrn = sanitize_value(row.get(col_map.get("patient_mrn", "")))
                    inv_id = str(row.get(invoice_col_raw)).strip() if invoice_col_raw else "N/A"

                    cleaned_rows.append([mem_id, first_name, dob, npi, mrn, inv_id])

            except Exception as e:
                cleaned_rows = [
                    ["Error processing record", str(e), "Not Available", "Not Available", "Not Available", "#"]]
    print('HI')
    return templates.TemplateResponse(
        "base.html",
        {
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


@app.get("/{category}/{subfolder}/{invoice_id}", response_class=HTMLResponse)
async def view_invoice_details(request: Request, category: str, subfolder: str, invoice_id: str):
    menu_structure = get_navigation_structure()
    excel_file_path = os.path.join(BASE_DIR, category, subfolder, f"{subfolder}.xlsx")

    if not os.path.exists(excel_file_path):
        raise HTTPException(status_code=404, detail="Excel data source missing.")

    left_metadata = {}
    right_summary = "Not Available"
    pdf_static_route = ""

    try:
        df = pd.read_excel(excel_file_path).fillna("")
        col_map = {str(col).strip().lower(): col for col in df.columns}

        member_id_col = col_map.get("patient_member_id")
        if member_id_col:
            df[member_id_col] = df[member_id_col].astype(str).str.strip()
            df = df.drop_duplicates(subset=[member_id_col], keep="first")

        target_col = col_map.get("invoice_id")
        if target_col:
            df[target_col] = df[target_col].astype(str).str.strip()
            matched_df = df[df[target_col] == invoice_id.strip()]

            if not matched_df.empty:
                row = matched_df.iloc[0]

                # Compute name fields safely
                first_name = str(row.get(col_map.get("patient_first_name", ""))).strip()
                last_name = str(row.get(col_map.get("patient_last_name", ""))).strip()

                if first_name or last_name:
                    full_computed_name = f"{first_name} {last_name}".strip()
                else:
                    full_computed_name = str(row.get(col_map.get("patient_name", ""))).strip()

                if not full_computed_name or full_computed_name.lower() in ["nan", "null"]:
                    full_computed_name = "Not Available"

                insurance_type = sanitize_value(row.get(col_map.get("patient_insurance_type", "")))
                dob = sanitize_value(
                    row.get(col_map.get("patient_date_of_birth", "")) or row.get(col_map.get("patient_dob", "")))
                npi = sanitize_value(row.get(col_map.get("npi_id", "")) or row.get(col_map.get("npi", "")))
                member_id = sanitize_value(row.get(member_id_col)) if member_id_col else "Not Available"
                mrn = sanitize_value(row.get(col_map.get("patient_mrn", "")))

                left_metadata = {
                    "Patient Name": full_computed_name,
                    "Patient Insurance Type": insurance_type,
                    "Patient DOB": dob,
                    "NPI": npi,
                    "Member ID": member_id,
                    "Patient MRN": mrn
                }

                right_summary = sanitize_value(row.get(col_map.get("summary", "")))

                # Read the actual local file name from the Excel sheet cell (e.g. 'Fax 3.pdf' or '20221219_...pdf')
                local_filename = str(row.get(col_map.get("file_name", ""))).strip()
                print(local_filename)
                if not local_filename or local_filename.lower() in ["nan", "null"]:
                    # Fallback lookup checker
                    local_filename = f"{invoice_id}.pdf"
                    print(f"Local File Name:{local_filename}")
                # Check if the file physically exists inside this specific database subfolder directory
                physical_pdf_path = os.path.join(BASE_DIR, category, subfolder, local_filename)
                if os.path.exists(physical_pdf_path):
                    # Point the source path string straight into our static exposed asset mount point route
                    pdf_static_route = f"/static_db/{category}/{subfolder}/{local_filename}"

    except Exception as e:
        right_summary = f"Error processing file tracking elements: {str(e)}"

    return templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "menu": menu_structure,
            "current_page": f"Record Profile: {invoice_id}",
            "view_type": "invoice_view",
            "left_metadata": left_metadata,
            "right_summary": right_summary,
            "pdf_url": pdf_static_route,  # Serve the local path string
            "back_url": f"/{category}?card={subfolder}"
        }
    )