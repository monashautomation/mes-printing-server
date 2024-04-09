from typing import NamedTuple

from pydantic import BaseModel


class _Job(BaseModel):
    file: str
    time_estimated: int = 100
    time_used: int = 0
    stopped: bool = False

    @property
    def printing(self) -> bool:
        return not self.stopped and self.time_used < self.time_estimated

    @property
    def progress(self) -> float:
        return self.time_used / self.time_estimated * 100

    @property
    def time_left(self) -> int:
        return self.time_estimated - self.time_used


class _HeadPos(NamedTuple):
    x: float
    y: float
    z: float
