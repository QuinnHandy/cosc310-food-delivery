# Command to run:
# uvicorn app.main:app --reload
# http://127.0.0.1:8000/restaurants

from fastapi import FastAPI
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


from app.api.routes import restaurants, menus

STATIC_DIR = Path(__file__).resolve().parent / "static" 


app = FastAPI()

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)    #modified to exclude route from API docs since its a webpage not endpoint
def root():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(restaurants.router)
app.include_router(menus.router)
