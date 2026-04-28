from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional, Any

app = FastAPI(title="ASTRO ARIES STUDIO Automation")


class OrderRequest(BaseModel):
    first_name: str
    last_name: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    service_name: str
    price_rsd: Optional[float] = None
    birth_date: str
    birth_time: str
    birth_place: str
    marital_status: Optional[str] = None
    questions: Optional[Any] = None
    message: Optional[str] = None


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/order")
def create_order(order: OrderRequest):
    if not order.first_name.strip():
        raise HTTPException(status_code=400, detail="First name is required.")

    if not order.service_name.strip():
        raise HTTPException(status_code=400, detail="Service name is required.")

    return {
        "success": True,
        "message": "Order received successfully.",
        "order": order.model_dump()
    }
