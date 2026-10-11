import asyncio

from app.body_limits import BodyLimitMiddleware


def test_streamed_upload_is_bounded_without_content_length():
    async def scenario():
        async def app(scope, receive, send):
            await receive()
            await receive()
        chunks = iter([{ "type": "http.request", "body": b"1234", "more_body": True }, { "type": "http.request", "body": b"5678", "more_body": False }])
        responses = []
        async def receive(): return next(chunks)
        async def send(message): responses.append(message)
        await BodyLimitMiddleware(app, 5)({"type": "http", "headers": []}, receive, send)
        assert responses[0]["status"] == 413
    asyncio.run(scenario())


def test_declared_oversized_body_is_rejected_before_reading():
    async def scenario():
        async def app(*args): raise AssertionError("Should not run parser")
        async def receive(): raise AssertionError("Should not read oversized body")
        responses = []
        async def send(message): responses.append(message)
        await BodyLimitMiddleware(app, 5)({"type": "http", "headers": [(b"content-length", b"10")]}, receive, send)
        assert responses[0]["status"] == 413
    asyncio.run(scenario())
