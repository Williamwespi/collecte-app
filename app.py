from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routes.publiek import router
from database import init_db

app = FastAPI(title="Collecteteller Diaconie")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router)

@app.on_event("startup")
def startup():
    init_db()
