from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from http import HTTPStatus

from db.models import Filament
from service import FilamentService

router = APIRouter(prefix="/filaments", tags=["filaments"])

class FilamentInventory(BaseModel):
    filament: Filament

class FilamentUsage(BaseModel):
    filament_id: int
    length_used_m: float

def get_filament_service() -> FilamentService:
    return FilamentService()

@router.get("/inventory")
async def check_inventory(service: FilamentService = Depends(get_filament_service)):
    inventory = await service.get_inventory()
    return [FilamentInventory(**filament.dict()) for filament in inventory]

@router.post("/inventory", status_code=HTTPStatus.CREATED)
async def add_filament_to_inventory(filament_data: FilamentInventory, service: FilamentService = Depends(get_filament_service)):
    await service.add_filament(filament_data.model_dump(exclude_unset=True))
    return {"message": "Filament added to inventory successfully."}

@router.put("/inventory/{filament_id}", status_code=HTTPStatus.ACCEPTED)
async def update_filament_inventory(usage: FilamentUsage, service: FilamentService = Depends(get_filament_service)):
    success = await service.update_filament(usage.filament_id, usage.length_used_m)
    if not success:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Failed to update filament.")
    return {"message": "Filament inventory updated successfully."}
