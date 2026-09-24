from fastapi import FastAPI
from app.schemas.restaurant import Restaurant


app = FastAPI()


@app.get("/")
def root():
    return {"message": "Food Delivery API"}


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/restaurants", response_model=list[Restaurant])
def get_restaurants():
    return [
        Restaurant(
            id=1,
            name="Golden Dragon",
            cuisine="Chines"
        ),
        Restaurant(
            id=2,
            name="Spice Garden",
            cuisine="Indian"
        )
    ]