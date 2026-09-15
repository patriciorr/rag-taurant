# app/services/reservation.py
import json
import os
import uuid
from typing import List, Dict
from app.core.config import settings

def _load_reservations() -> List[Dict]:
    if not os.path.exists(settings.RESERVATIONS_DATA_PATH):
        return []
    with open(settings.RESERVATIONS_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_reservations(data: List[Dict]):
    os.makedirs(os.path.dirname(settings.RESERVATIONS_DATA_PATH), exist_ok=True)
    with open(settings.RESERVATIONS_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def create_reservation(customer_name: str, phone: str, date_time: str, guests: int) -> dict:
    reservations = _load_reservations()
    res_code = f"RES-{str(uuid.uuid4())[:6].upper()}"
    
    new_res = {
        "code": res_code,
        "customer_name": customer_name,
        "phone": phone,
        "date_time": date_time,
        "guests": guests,
        "status": "confirmada"
    }
    reservations.append(new_res)
    _save_reservations(reservations)
    return new_res