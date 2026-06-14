class JWException(Exception):
    pass


class Need2FAException(JWException):
    pass


class LoginFailedException(JWException):
    def __init__(self, message="登录失败"):
        super().__init__(message)
