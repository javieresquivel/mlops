from pydantic import BaseModel


class ModelPredictionRequest(BaseModel):
    brokered_by: float | None = None
    status: str | None = None
    bed: float | None = None
    bath: float | None = None
    acre_lot: float | None = None
    street: float | None = None
    city: str | None = None
    state: str | None = None
    zip_code: float | None = None
    house_size: float | None = None
    prev_sold_date: str | None = None
