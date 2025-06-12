from pydantic import BaseModel
from typing import List, Dict, Any

class PenjadwalanRequest(BaseModel):
    fleet_ev_motorbikes: Dict[Any, Dict[str, Any]]
    battery_swap_station: Dict[Any, Dict[str, Any]]
