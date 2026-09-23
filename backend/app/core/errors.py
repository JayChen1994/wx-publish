class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFoundError(AppError):
    def __init__(self, message: str = "资源不存在") -> None:
        super().__init__(message, 404)


class ConflictError(AppError):
    def __init__(self, message: str = "资源冲突") -> None:
        super().__init__(message, 409)


class PublishFailed(AppError):
    def __init__(self, message: str = "发布失败") -> None:
        super().__init__(message, 502)


class PolishFailed(AppError):
    def __init__(self, message: str = "AI 润色失败") -> None:
        super().__init__(message, 502)
