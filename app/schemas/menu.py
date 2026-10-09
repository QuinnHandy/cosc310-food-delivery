from pydantic import BaseModel, Field


class MenuItem(BaseModel):
    id: int
    restaurant_id: int
    name: str
    description: str
    price: float = Field(ge=0)
    available: bool = True


class Menu(BaseModel):
    restaurant_id: int
    items: list[MenuItem]