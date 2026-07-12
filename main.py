from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routers import core, categories, profiles, upload

app = FastAPI()

# Mount the folder system database as static files so browsers can render PDFs securely
app.mount("/static_db", StaticFiles(directory="database"), name="static_db")

# Include routers - Order ensures specialized routes execute prior to category catch-alls
app.include_router(core.router)
app.include_router(profiles.router)
app.include_router(categories.router)
app.include_router(upload.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
