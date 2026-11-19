from datetime import UTC, datetime

from fastapi import APIRouter, Query, status

from app.schemas import CompanyCreate, CompanyOut, CompanyStatus, Page

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
def create_company(payload: CompanyCreate) -> CompanyOut:
    # TODO: БД, дубль БИН -> 409
    return CompanyOut(
        id=1, status=CompanyStatus.new, created_at=datetime.now(UTC), **payload.model_dump()
    )


@router.get("", response_model=Page[CompanyOut])
def list_companies(
    status_: CompanyStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> Page[CompanyOut]:
    # TODO: БД
    return Page(items=[], total=0, limit=limit, offset=offset)
