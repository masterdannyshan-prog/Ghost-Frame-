from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import FRONTEND_ORIGIN
from routers import projects, discover, process, profiles

app = FastAPI(title="Ghost Frame API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://localhost:3005", "http://127.0.0.1:3005"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(discover.router)
app.include_router(process.router)
app.include_router(profiles.router)

@app.get("/health")
def health():
    return {"status": "ok"}
