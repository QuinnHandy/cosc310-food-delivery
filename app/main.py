# Command to run:
# uvicorn app.main:app --reload
# http://127.0.0.1:8000/restaurants

from fastapi import FastAPI

from app.api.routes import restaurants


app = FastAPI()


@app.get("/")
def root():
    return {"message": "Food Delivery API"}


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(restaurants.router)
