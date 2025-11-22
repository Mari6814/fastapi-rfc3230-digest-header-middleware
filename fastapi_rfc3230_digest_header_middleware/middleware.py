"""Module that implements a middleware for FastAPI to handle RFC 3230 Digest headers."""

from typing import Callable, MutableMapping, Any, Awaitable
from rfc3230_digest_headers import DigestHeaderAlgorithm, exceptions
from starlette.middleware.base import BaseHTTPMiddleware, DispatchFunction
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class Middleware(BaseHTTPMiddleware):
    """Middleware to add RFC 3230 Digest header support to FastAPI applications."""

    def __init__(
        self,
        app: Callable[
            [
                MutableMapping[str, Any],
                Callable[[], Awaitable[MutableMapping[str, Any]]],
                Callable[[MutableMapping[str, Any]], Awaitable[None]],
            ],
            Awaitable[None],
        ],
        dispatch: (
            Callable[
                [Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]
            ]
            | None
        ) = None,
        instance_bytes_callback: Callable[[Request], Awaitable[bytes]] | None = None,
        qvalues: dict[DigestHeaderAlgorithm, float | None] | None = None,
    ) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application.
            dispatch: Optional custom dispatch function.
            instance_bytes_callback: Optional callback to get the instance bytes from the request. The bytes returned should be the same ones used to initially generate the Digest header.
            qvalues: Optional dictionary of preferred DigestHeaderAlgorithm and their q-values. If not provided, default q-values will be used that only allow SHA512 and SHA256.
        """
        super().__init__(app, dispatch)
        self.instance_bytes_callback = instance_bytes_callback
        self.qvalues = qvalues

    async def dispatch(self, request: Request, call_next) -> Response:
        instance_bytes = await (
            self.instance_bytes_callback(request)
            if self.instance_bytes_callback
            else request.body()
        )
        digest_header = request.headers.get("Digest")
        valid, header_should_be_added = DigestHeaderAlgorithm.verify_request(
            request_headers={"Digest": digest_header} if digest_header else {},
            instance=instance_bytes,
            qvalues=(
                self.qvalues
                or {
                    DigestHeaderAlgorithm.SHA512: None,
                    DigestHeaderAlgorithm.SHA256: None,
                    DigestHeaderAlgorithm.SHA: 0.0,
                    DigestHeaderAlgorithm.MD5: 0.0,
                    DigestHeaderAlgorithm.UNIXCKSUM: 0.0,
                    DigestHeaderAlgorithm.UNIXSUM: 0.0,
                }
            ),
        )
        if not valid and header_should_be_added is not None:
            return Response(
                content=f"Digest header validation failed.",
                status_code=422,
                headers={
                    header_should_be_added.header_name: header_should_be_added.header_value
                },
            )
        return await call_next(request)
