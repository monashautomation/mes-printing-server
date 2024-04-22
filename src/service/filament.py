from sqlmodel import select
from db.models import Filament
from .db import BaseDbService  

class FilamentService(BaseDbService):
    async def get_inventory(self) -> list:
        statement = select(Filament)
        result = await self.db.exec(statement)
        print(result)
        return result.all()
    
    async def get_filament(self, filament_id: int) -> Filament:
        statement = select(Filament).where(Filament.id == filament_id)
        print(self.db)
        result = await self.db.exec(statement)
        return result.first()

    async def add_filament(self, filament_data: dict) -> None:
        filament = Filament(**filament_data)
        self.db.add(filament)
        await self.db.commit()
        await self.db.refresh(filament) 


    async def update_filament(self, filament_id: int, length_used_m: float) -> bool:
        filament = await self.get_filament(filament_id)
        if not filament or filament.filament_left < length_used_m:
            return False

        filament.filament_left -= length_used_m
        filament.filament_waste += length_used_m
        self.db.add(filament)
        await self.db.commit()
        await self.db.refresh(filament)
        return True

