from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.db import Conn, get_conn, pool
from app.errors import register_error_handlers
from app.routers import calls, companies, managers, meetings


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open()
    yield
    pool.close()


app = FastAPI(title="WhiteList CRM", version="0.1.0", lifespan=lifespan)

register_error_handlers(app)

app.include_router(companies.router)
app.include_router(calls.router)
app.include_router(meetings.router)
app.include_router(managers.router)


@app.get("/health", tags=["health"])
def health(conn: Conn = Depends(get_conn)) -> dict[str, str]:
    conn.execute("SELECT 1")
    return {"status": "ok"}
