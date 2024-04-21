from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List
from http import HTTPStatus

from db.models import Filament, FilamentTransaction
from service import FilamentService

router = APIRouter(prefix="/filaments", tags=["filaments"])

class FilamentInventory(BaseModel):
    filament: Filament
    # id: int
    # supplier: str
    # material: str
    # color: str
    # net_material: float
    # filament_left: float
    # filament_waste: float

class FilamentUsage(BaseModel):
    filament_id: int
    length_used_m: float
    user_id: str

@router.get("/inventory", response_model=List[FilamentInventory])
async def check_inventory(service: FilamentService = Depends(FilamentService)):
    inventory = await service.get_inventory()
    return inventory

@router.post("/inventory/add", status_code=HTTPStatus.CREATED)
async def add_filament_to_inventory(filament_data: FilamentInventory, service: FilamentService = Depends(FilamentService)):
    await service.add_filament(filament_data.dict())
    return {"message": "Filament added to inventory successfully."}

@router.put("/inventory/{filament_id}/update", status_code=HTTPStatus.ACCEPTED)
async def update_filament_inventory(usage: FilamentUsage, service: FilamentService = Depends(FilamentService)):
    try:
        result = await service.update_filament(usage.filament_id, usage.length_used_m, usage.user_id)
        return {"message": "Filament inventory updated successfully.", "result": result}
    except Exception as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e))