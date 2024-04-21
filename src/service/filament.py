from db.models import Filament, FilamentTransaction
from datetime import datetime
from sqlmodel import select

class FilamentService:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    async def get_inventory(self) -> list:
        statement = select(Filament)
        result = await self.session.execute(statement)
        return result.scalars().all()
    
    async def get_filament(self, filament_id: int) -> Filament:
        statement = select(Filament).where(Filament.id == filament_id)
        result = await self.session.execute(statement)
        filament = result.scalars().first()
        return filament

    async def add_filament(self, filament_data: dict) -> None:
        filament = Filament(**filament_data)
        self.session.add(filament)
        await self.session.commit()

    async def update_filament(self, filament_id: int, length_used_m: float, user_id: str) -> bool:
        statement = select(Filament).where(Filament.id == filament_id)
        result = await self.session.execute(statement)
        filament = result.scalars().first()
        if not filament or filament.filament_left < length_used_m:
            return False

        filament.filament_left -= length_used_m
        filament.filament_waste += length_used_m
        transaction = FilamentTransaction(
            filament_id=filament.id,
            user_id=user_id,
            action="Load",
            timestamp=datetime.now()
        )
        self.session.add(transaction)
        try:
            await self.session.commit()
            return True
        except Exception as e:
            await self.session.rollback()
            return False
