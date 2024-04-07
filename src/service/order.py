from db import DatabaseSession, session


class OrderService:
    def __init__(self, db: DatabaseSession | None = None):
        self.db: DatabaseSession = db or session()
