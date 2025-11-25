import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.responses import Response
from fastapi_rfc3230_digest_header_middleware.middleware import Middleware
from rfc3230_digest_headers import DigestHeaderAlgorithm
import json


@pytest.fixture
def app():
    app = FastAPI()
    app.add_middleware(Middleware)

    @app.post("/echo")
    async def echo(request: Request):
        body = await request.body()
        return Response(content=body)

    return app


def test_valid_digest_header(app: FastAPI):
    client = TestClient(app)
    body = b"hello world"
    digest = DigestHeaderAlgorithm.make_digest_header(
        body, algorithms=[DigestHeaderAlgorithm.SHA256]
    )
    response = client.post(
        "/echo", content=body, headers={digest.header_name: digest.header_value}
    )
    assert response.content == body
    assert response.status_code == 200


def test_invalid_digest_header(app: FastAPI):
    client = TestClient(app)
    body = b"hello world"
    # Invalid digest value
    digest = DigestHeaderAlgorithm.make_digest_header(
        body, algorithms=[DigestHeaderAlgorithm.SHA256]
    )
    response = client.post(
        "/echo",
        content=body,
        headers={digest.header_name: digest.header_value + "invalid"},
    )
    assert response.status_code == 400
    assert b"No Digest value matched" in response.content


def test_missing_digest_header(app: FastAPI):
    client = TestClient(app)
    body = b"hello world"
    response = client.post("/echo", content=body)
    assert response.status_code == 400
    assert b"Missing Digest header" in response.content


def test_reject_disallowed():
    # Accept only sha-256, explicitly reject md5
    qvalues = {
        DigestHeaderAlgorithm.SHA256: None,
        DigestHeaderAlgorithm.MD5: 0.0,
    }
    app = FastAPI()
    app.add_middleware(Middleware, qvalues=qvalues)

    @app.post("/echo")
    async def echo(request: Request):
        body = await request.body()
        return Response(content=body)

    client = TestClient(app)
    body = b"hello world"

    # Send with sha-256, should succeed
    sha256_digest = DigestHeaderAlgorithm.make_digest_header(
        body, algorithms=[DigestHeaderAlgorithm.SHA256]
    )
    response = client.post(
        "/echo",
        content=body,
        headers={sha256_digest.header_name: sha256_digest.header_value},
    )
    assert response.status_code == 200
    assert response.content == body

    # Send with md5, should fail
    md5_digest = DigestHeaderAlgorithm.make_digest_header(
        body, algorithms=[DigestHeaderAlgorithm.MD5]
    )
    response = client.post(
        "/echo", content=body, headers={md5_digest.header_name: md5_digest.header_value}
    )
    assert response.status_code == 400
    assert b"Algorithm md5 not acceptable. qvalue is 0.0." in response.content

    # Send with sha-512, should fail because it is not mentioned
    sha512_digest = DigestHeaderAlgorithm.make_digest_header(
        body, algorithms=[DigestHeaderAlgorithm.SHA512]
    )
    response = client.post(
        "/echo",
        content=body,
        headers={sha512_digest.header_name: sha512_digest.header_value},
    )
    assert response.status_code == 400
    assert b"No acceptable algorithm provided in Digest header." in response.content


def test_instance_bytes_callback_partial_json():
    """
    Test customizing digest calculation to only include part of a JSON request (e.g., only the 'foo' field).
    """

    async def only_foo_field_bytes(request: Request) -> bytes:
        data = await request.json()
        foo_value = data.get("foo", "")
        return str(foo_value).encode()

    app = FastAPI()
    app.add_middleware(Middleware, instance_bytes_callback=only_foo_field_bytes)

    @app.post("/json")
    async def json_echo(request: Request):
        body = await request.body()
        return Response(content=body)

    client = TestClient(app)
    payload = {"foo": "bar", "baz": 123}
    body = json.dumps(payload).encode()
    # Digest only covers the 'foo' field
    digest = DigestHeaderAlgorithm.make_digest_header(
        b"bar", algorithms=[DigestHeaderAlgorithm.SHA256]
    )
    response = client.post(
        "/json", content=body, headers={digest.header_name: digest.header_value}
    )
    assert response.status_code == 200
    assert response.content == body

    # Digest covers wrong value (whole body), should fail
    wrong_digest = DigestHeaderAlgorithm.make_digest_header(
        body, algorithms=[DigestHeaderAlgorithm.SHA256]
    )
    response = client.post(
        "/json",
        content=body,
        headers={wrong_digest.header_name: wrong_digest.header_value},
    )
    assert response.status_code == 400
    assert b"No Digest value matched" in response.content
