"""Bound incoming bodies before multipart parsing, including chunked uploads."""
from starlette.responses import JSONResponse


class BodyTooLarge(Exception):
    pass


class BodyLimitMiddleware:
    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            declared = 0
        error = JSONResponse({"detail": "Request body exceeds the upload budget"}, status_code=413)
        if declared > self.max_bytes:
            return await error(scope, receive, send)
        received = 0

        async def bounded_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise BodyTooLarge()
            return message

        try:
            await self.app(scope, bounded_receive, send)
        except BodyTooLarge:
            await error(scope, receive, send)
