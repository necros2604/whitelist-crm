from fastapi import APIRouter, Depends, status

from app.db import Conn, get_conn
from app.errors import BusinessRuleError, NotFound
from app.schemas import CallCreate, CallOut, CallResult

router = APIRouter(prefix="/calls", tags=["calls"])


def check_meeting_for_call(conn: Conn, meeting_id: int, company_id: int) -> None:
    meeting = conn.execute(
        "SELECT company_id, status FROM meetings WHERE id = %s", (meeting_id,)
    ).fetchone()
    if meeting is None:
        raise BusinessRuleError("meeting_not_found", "Сначала создайте встречу, потом звонок meeting_set")
    if meeting["company_id"] != company_id:
        raise BusinessRuleError("meeting_other_company", "Встреча относится к другой компании")
    if meeting["status"] != "scheduled":
        raise BusinessRuleError("meeting_cancelled", "Встреча отменена")


@router.post("", response_model=CallOut, status_code=status.HTTP_201_CREATED)
def create_call(payload: CallCreate, conn: Conn = Depends(get_conn)):
    if conn.execute("SELECT 1 FROM companies WHERE id = %s", (payload.company_id,)).fetchone() is None:
        raise NotFound("company_not_found", "Компания не найдена")

    # без meeting_id при meeting_set схема уже вернула 422, тут проверяем саму встречу
    if payload.result == CallResult.meeting_set:
        check_meeting_for_call(conn, payload.meeting_id, payload.company_id)

    call = conn.execute(
        """
        INSERT INTO calls (company_id, result, meeting_id, comment)
        VALUES (%(company_id)s, %(result)s, %(meeting_id)s, %(comment)s)
        RETURNING *
        """,
        payload.model_dump(),
    ).fetchone()
    # статус компании = результат последнего звонка
    conn.execute(
        "UPDATE companies SET status = %s WHERE id = %s", (payload.result, payload.company_id)
    )
    return call
