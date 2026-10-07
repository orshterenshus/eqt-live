"""Application errors. Each maps to an HTTP status and a machine-readable code."""


class AppError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class UpstreamError(AppError):
    status_code = 502
    code = "upstream_unavailable"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class InvalidRequestError(AppError):
    status_code = 422
    code = "invalid_request"


class InsufficientDataError(AppError):
    status_code = 422
    code = "insufficient_data"


class ModelsNotLoadedError(AppError):
    status_code = 503
    code = "models_not_loaded"
