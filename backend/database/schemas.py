from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional

class JadwalPenukaranBase(BaseModel):
    id_pengemudi: int
    id_slot_stasiun_penukaran_baterai: int
    waktu_penukaran: datetime
    estimasi_waktu_tunggu: Optional[float] = None
    estimasi_waktu_tempuh: Optional[float] = None
    estimasi_baterai_tempuh: Optional[float] = None
    perkiraan_kapasitas_baterai_yang_ditukar: Optional[float] = None
    perkiraan_kapasitas_baterai_yang_didapat: Optional[float] = None
    perkiraan_siklus_baterai_yang_didapat: Optional[int] = None
    status: Optional[str] = "on going"

class JadwalPenukaranCreate(JadwalPenukaranBase):
    pass

class JadwalPenukaranOut(JadwalPenukaranBase):
    id: int

    class Config:
        orm_mode = True