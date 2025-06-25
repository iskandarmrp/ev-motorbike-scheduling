from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from database.database import Base, engine, seed_admin, SessionLocal
from database.routers import jadwal, pengemudi_dan_kendaraan, baterai, admin, stasiun_penukaran_baterai, order
from database.models import Admin
from database import crud
from problem_solving_agent.utils import update_energy_distance_and_travel_time_all, convert_fleet_ev_motorbikes_to_dict, convert_station_dict_to_list, get_fleet_dict_and_station_list
from problem_solving_agent.algorithm import simulated_annealing, alns_ev_scheduler
import time
from typing import Dict, Any, List
from schemas import PenjadwalanRequest
from datetime import datetime, timedelta
import asyncio, json

Base.metadata.create_all(bind=engine)

seed_admin()

app = FastAPI()
app.include_router(jadwal.router)
app.include_router(pengemudi_dan_kendaraan.router)
app.include_router(baterai.router)
app.include_router(admin.router)
app.include_router(stasiun_penukaran_baterai.router)
app.include_router(order.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ganti ke ['http://localhost:3000'] di production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Configuration
SECRET_KEY = "rahasia-super-aman"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Helper
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta=None):
    from datetime import timedelta
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Login endpoint
@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db: Session = SessionLocal()
    user = db.query(Admin).filter(Admin.username == form_data.username).first()

    if not user:
        print("[ERROR] Username tidak ditemukan.")
        db.close()
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    password_valid = verify_password(form_data.password, user.password)

    db.close()

    if not password_valid:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

# Protected route example
@app.get("/me")
def read_users_me(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        return {"username": username}
    except JWTError:
        raise HTTPException(status_code=403, detail="Invalid token")

@app.post("/api/sync-online-transportation-data")
async def sync_online_transportation_data(request: Request):
    data = await request.json()
    db: Session = SessionLocal()
    
    try:
        if "fleet_ev_motorbikes" in data:
            pengemudi_dan_kendaraan.insert_motorbikes(data["fleet_ev_motorbikes"], db=db)

        if "orders" in data:
            order.insert_orders(data["orders"], db=db)

        if "swap_schedules" in data:
            jadwal.insert_swap_schedules(data["swap_schedules"], db=db)

        db.commit()
        return {"message": "Online transportation data synced successfully"}
    
    except Exception as e:
        db.rollback()
        print("[SYNC ERROR]", str(e))
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")
    
    finally:
        db.close()

@app.post("/api/sync-battery-swap-system-data")
async def sync_battery_swap_system_data(request: Request):
    data = await request.json()
    db: Session = SessionLocal()
    
    try:
        if "battery_swap_station" in data:
            stasiun_penukaran_baterai.insert_station(data["battery_swap_station"], db=db)

        if "batteries" in data:
            baterai.insert_batteries(data["batteries"], db=db)

        db.commit()
        return {"message": "Battery swap data synced successfully"}
    
    except Exception as e:
        db.rollback()
        print("[SYNC ERROR]", str(e))
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")
    
    finally:
        db.close()

@app.get("/api/jadwal-penukaran")
async def get_jadwal_penukaran():
    start = time.time()
    db = SessionLocal()
    try:
        fleet_ev_motorbikes = crud.get_all_motorbikes(db)
        schedules = crud.get_all_schedules(db)
        battery_swap_stations = crud.get_all_stations(db)
        batteries = crud.get_all_batteries(db)  # <-- FIXED here
        orders = crud.get_all_orders(db, status="on going")

        ev_dict, station_list = get_fleet_dict_and_station_list(
            fleet_ev_motorbikes, schedules, orders, battery_swap_stations, batteries
        )

        schedule, score, history = alns_ev_scheduler(
            battery_swap_station=station_list,
            ev=ev_dict,
            threshold=15,
            charging_rate=100 / 240,
            required_battery_threshold=80,
            max_iter=200
        )

        execution_time = time.time() - start
        return {
            "schedule": schedule,
            "score": score,
            "execution_time": execution_time
        }
    finally:
        db.close()


@app.post("/penjadwalan")
async def penjadwalan(data: PenjadwalanRequest):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, run_penjadwalan, data)
    return result

#
def run_penjadwalan(data):
    start = time.time()
    fleet_ev_motorbikes = data.fleet_ev_motorbikes
    battery_swap_station = data.battery_swap_station

    update_energy_distance_and_travel_time_all(fleet_ev_motorbikes, battery_swap_station)
    ev_dict = convert_fleet_ev_motorbikes_to_dict(fleet_ev_motorbikes)
    station_list = convert_station_dict_to_list(battery_swap_station)

    # schedule, score = simulated_annealing(
    #     station_list,
    #     ev_dict,
    #     threshold=15,
    #     charging_rate=100/240,
    #     initial_temp=100.0,
    #     alpha=0.95,
    #     T_min=0.001,
    #     max_iter=200
    # )

    schedule, score, history = alns_ev_scheduler(
        battery_swap_station=station_list,
        ev=ev_dict,
        threshold=15,
        charging_rate=100 / 240,
        required_battery_threshold=80,
        max_iter=200
    )

    execution_time = time.time() - start
    return schedule, score, execution_time

# Websocket
connected_clients = set()

@app.websocket("/ws/status")
async def websocket_status(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)

    try:
        while True:
            db = SessionLocal()
            try:
                schedules = crud.get_all_schedules(db)

                valid_waiting_times = [
                    s["waiting_time"] for s in schedules 
                    if s["waiting_time"] is not None and s["waiting_time"] > 0
                ]

                total_waiting = len(valid_waiting_times)
                average_waiting_time = sum(valid_waiting_times) / total_waiting if total_waiting > 0 else 0

                fleet_ev_motorbikes = crud.get_all_motorbikes(db)

                low_battery_idle_motorbikes = [
                    m for m in fleet_ev_motorbikes 
                    if m.get("battery_now") is not None and m["battery_now"] < 10 and m["status"] == "idle"
                ]

                total_low_battery_idle = len(low_battery_idle_motorbikes)

                daily_incomes = [
                    m["daily_income"] for m in fleet_ev_motorbikes 
                    if m.get("daily_income") is not None
                ]

                avg_daily_income = sum(daily_incomes) / len(daily_incomes) if daily_incomes else 0

                data = {
                    "jumlah_ev_motorbike": len(crud.get_all_motorbikes(db)),
                    "jumlah_battery_swap_station": len(crud.get_all_stations(db)),
                    "fleet_ev_motorbikes": fleet_ev_motorbikes,
                    "battery_swap_station": crud.get_all_stations(db),
                    "batteries": crud.get_all_batteries(db),
                    "avg_daily_incomes": avg_daily_income,
                    "order_search_driver": crud.get_all_orders(db, status="searching driver"),
                    "order_active": crud.get_all_orders(db, status="on going"),
                    "order_done": crud.get_all_orders(db, status="done"),
                    "order_failed": crud.get_all_orders(db, status="failed"),
                    "swap_schedules": crud.get_all_schedules(db),
                    "total_order": len(crud.get_all_orders(db)),
                    "total_waiting": total_waiting,  # jumlah waiting_time > 0
                    "average_waiting_time": average_waiting_time,  # rata-rata waiting_time 
                    "total_low_battery_idle": total_low_battery_idle,
                    "time_now": datetime.now().isoformat(),
                }

                if websocket.client_state.name == "CONNECTED":
                    await websocket.send_text(json.dumps(data, default=str))
                else:
                    print("[WebSocket] Client not connected anymore.")
                    break
            except Exception as e:
                print("[WebSocket ERROR]", str(e))
                try:
                    await websocket.close()
                except:
                    pass
                break
            finally:
                db.close()

            await asyncio.sleep(5)

    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        print("WebSocket disconnected")
    except Exception as e:
        print("[WebSocket ERROR - Outer Loop]", str(e))
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)