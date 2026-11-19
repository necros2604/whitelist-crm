from fastapi import APIRouter, Depends, Query, status

from app.db import Conn, get_conn
from app.schemas import CompanyCreate, CompanyOut, CompanyStatus, Page

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
def create_company(payload: CompanyCreate, conn: Conn = Depends(get_conn)):
    # если дубль БИН - UNIQUE в БД, вернётся 409 (см. errors.py)
    return conn.execute(
        "INSERT INTO companies (name, bin, phone) VALUES (%(name)s, %(bin)s, %(phone)s) RETURNING *",
        payload.model_dump(),
    ).fetchone()


@router.get("", response_model=Page[CompanyOut])
def list_companies(
    status_: CompanyStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    conn: Conn = Depends(get_conn),
):
    params = {"status": status_, "limit": limit, "offset": offset}
    where = "WHERE status = %(status)s" if status_ else ""

    total = conn.execute(f"SELECT count(*) AS n FROM companies {where}", params).fetchone()["n"]
    items = conn.execute(
        f"SELECT * FROM companies {where} ORDER BY id LIMIT %(limit)s OFFSET %(offset)s",
        params,
    ).fetchall()
    return {"items": items, "total": total, "limit": limit, "offset": offset}
