from fastapi import FastAPI

from app.routers import calls, companies, managers, meetings

app = FastAPI(title="WhiteList CRM", version="0.1.0")

app.include_router(companies.router)
app.include_router(calls.router)
app.include_router(meetings.router)
app.include_router(managers.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
