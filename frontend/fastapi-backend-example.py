# Example FastAPI backend configuration for your app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Battery Swap API", version="1.0.0")

# CORS middleware configuration - IMPORTANT for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js development server
        "http://127.0.0.1:3000",
        "http://localhost:3001",  # Alternative port
        "https://your-frontend-domain.com",  # Production domain
        "*"  # Allow all origins (use with caution in production)
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
def root():
    return {"message": "Battery Swap API is running", "status": "ok"}

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "battery-swap-api"}

# Status endpoint (your existing endpoint)
@app.get("/status")
def get_status():
    return {
        "jumlah_ev_motorbike": 100,
        "jumlah_battery_swap_station": 10,
        "fleet_ev_motorbikes": [],
        "battery_swap_station": [],
        "batteries": [],
        "total_order": 45,
        "order_search_driver": [],
        "order_active": [],
        "order_done": [],
        "order_failed": [],
        "time_now": "2024-01-01T12:00:00Z",
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",  # Replace "app" with your actual filename
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload during development
        log_level="info"
    )
