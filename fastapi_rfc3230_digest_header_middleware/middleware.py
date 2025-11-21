"""Module that implements a middleware for FastAPI to handle RFC 3230 Digest headers."""

from rfc3230_digest_headers import DigestHeaderAlgorithm, exceptions
from starlette.middleware.base import BaseHTTPMiddleware, DispatchFunction
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class Middleware(BaseHTTPMiddleware):
    """Middleware to add RFC 3230 Digest header support to FastAPI applications."""

    async def dispatch(self, request: Request, call_next) -> Response:
        body = await request.body()
        digest_header = request.headers.get("Digest")
        valid, header_should_be_added = DigestHeaderAlgorithm.verify_request(
            request_headers={"Digest": digest_header} if digest_header else {},
            instance=body,
            qvalues={
                DigestHeaderAlgorithm.SHA512: 1.0,
                DigestHeaderAlgorithm.SHA256: 1.0,
                DigestHeaderAlgorithm.SHA: 0.5,
                DigestHeaderAlgorithm.MD5: 0.0,
                DigestHeaderAlgorithm.UNIXCKSUM: 0.0,
                DigestHeaderAlgorithm.UNIXSUM: 0.0,
            },
        )
        if not valid and header_should_be_added is not None:
            header_name = header_should_be_added.header_name
            header_value = header_should_be_added.header_value
            return Response(
                content=f"Digest header validation failed.",
                status_code=422,
                headers={header_name: header_value},
            )
        return await call_next(request)
