from fastapi import HTTPException, status


class AppException(HTTPException):
    """アプリケーション基底例外。"""

    def __init__(self, status_code: int, detail: str, error_type: str = "app_error"):
        super().__init__(status_code=status_code, detail=detail)
        self.error_type = error_type


class NotFoundError(AppException):
    def __init__(self, resource: str, resource_id: str = ""):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} が見つかりません: {resource_id}",
            error_type="not_found",
        )


class AlreadyExistsError(AppException):
    def __init__(self, resource: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{resource} は既に存在します",
            error_type="already_exists",
        )


class ForbiddenError(AppException):
    def __init__(self, detail: str = "この操作を行う権限がありません"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_type="forbidden",
        )


class UnauthorizedError(AppException):
    def __init__(self, detail: str = "認証が必要です"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_type="unauthorized",
        )


class ValidationError(AppException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_type="validation_error",
        )


class BusinessRuleError(AppException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_type="business_rule_error",
        )


class ConflictError(AppException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_type="conflict",
        )


class RateLimitError(AppException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="リクエスト数が上限を超えました。しばらく待ってから再試行してください。",
            error_type="rate_limit",
        )
