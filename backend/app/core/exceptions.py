from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400, errors: list = None):
        self.message = message
        self.status_code = status_code
        self.errors = errors or []
        super().__init__(message)


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found", errors: list = None):
        super().__init__(message, status_code=404, errors=errors)


class AuthException(AppException):
    def __init__(self, message: str = "Could not authenticate credentials", errors: list = None):
        super().__init__(message, status_code=401, errors=errors)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Access forbidden", errors: list = None):
        super().__init__(message, status_code=403, errors=errors)


class ValidationException(AppException):
    def __init__(self, message: str = "Input validation failed", errors: list = None):
        super().__init__(message, status_code=400, errors=errors)


# Exception handler hooks setup
def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.message,
                "data": None,
                "errors": exc.errors
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors_list = []
        for error in exc.errors():
            loc = " -> ".join([str(x) for x in error["loc"]])
            errors_list.append(f"{loc}: {error['msg']}")
            
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "Input validation failed",
                "data": None,
                "errors": errors_list
            }
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.detail,
                "data": None,
                "errors": []
            }
        )

    @app.exception_handler(Exception)
    async def unexpected_exception_handler(request: Request, exc: Exception):
        # In a real app, log the stacktrace here
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "An unexpected server error occurred",
                "data": None,
                "errors": [str(exc)]
            }
        )
