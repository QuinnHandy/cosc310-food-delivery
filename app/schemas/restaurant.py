from pydantic import BaseModel, Field


class Restaurant(BaseModel):
    id: int
    name: str
    cuisine: str


class RestaurantCreate(BaseModel):
    name: str = Field(min_length=1)
    cuisine: str = Field(min_length=1)


class RestaurantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    cuisine: str | None = Field(default=None, min_length=1)