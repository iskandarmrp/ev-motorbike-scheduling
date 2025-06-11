from fastapi import FastAPI
from database.database import Base, engine, seed_admin
from database.routers import jadwal, pengemudi_dan_kendaraan, baterai, admin, stasiun_penukaran_baterai, order

Base.metadata.create_all(bind=engine)

seed_admin()

app = FastAPI()
app.include_router(jadwal.router)
app.include_router(pengemudi_dan_kendaraan.router)
app.include_router(baterai.router)
app.include_router(admin.router)
app.include_router(stasiun_penukaran_baterai.router)
app.include_router(order.router)

@app.get("/")
def root():
    return {"message": "EV Battery Swap Scheduling API"}