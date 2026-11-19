from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg import OperationalError
from psycopg import errors as pg_errors
from psycopg_pool import PoolTimeout


class AppError(Exception):
    status_code = 400

    def __init__(self, error: str, message: str):
        self.error = error
        self.message = message


class NotFound(AppError):
    status_code = 404


class Conflict(AppError):
    status_code = 409


class BusinessRuleError(AppError):
    status_code = 422


# ограничения из migrations/001_init.sql
CONSTRAINT_ERRORS = {
    "companies_bin_key": ("bin_exists", "Компания с таким БИН уже есть"),
    "meetings_manager_overlap": ("manager_busy", "У менеджера уже есть встреча в это время"),
    "meetings_company_active": ("company_has_meeting", "У компании уже есть активная встреча"),
}


def error_response(status_code: int, error: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": error, "message": message})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    def app_error(request: Request, exc: AppError):
        return error_response(exc.status_code, exc.error, exc.message)

    @app.exception_handler(RequestValidationError)
    def validation_error(request: Request, exc: RequestValidationError):
        parts = []
        for err in exc.errors():
            if err["type"] == "json_invalid":
                return error_response(
                    # в loc тут не поле, а номер символа, где сломался JSON
                    422, "invalid_json", f"Тело запроса - некорректный JSON (ошибка на символе {err['loc'][-1]})"
                )
            field = ".".join(str(p) for p in err["loc"] if p != "body")
            msg = err["msg"].removeprefix("Value error, ")
            parts.append(f"{field}: {msg}" if field else msg)
        return error_response(422, "validation_error", "; ".join(parts))

    @app.exception_handler(pg_errors.IntegrityError)
    def integrity_error(request: Request, exc: pg_errors.IntegrityError):
        name = exc.diag.constraint_name
        if name in CONSTRAINT_ERRORS:
            error, message = CONSTRAINT_ERRORS[name]
            return error_response(409, error, message)
        return error_response(409, "conflict", f"Нарушено ограничение БД: {name}")

    # два одновременных запроса на один слот: Postgres может оборвать один из них (deadlock).
    # это наследник OperationalError, поэтому ловим отдельно, иначе ушло бы в 503
    @app.exception_handler(pg_errors.DeadlockDetected)
    @app.exception_handler(pg_errors.SerializationFailure)
    def concurrent_conflict(request: Request, exc: Exception):
        return error_response(409, "concurrent_conflict", "Эти данные одновременно меняет другой запрос, повторите попытку")

    @app.exception_handler(OperationalError)
    @app.exception_handler(PoolTimeout)
    def db_unavailable(request: Request, exc: Exception):
        return error_response(503, "db_unavailable", "База данных недоступна, попробуйте позже")
