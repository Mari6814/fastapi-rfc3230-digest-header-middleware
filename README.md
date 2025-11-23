# FastAPI RFC 3230 Digest Header Middleware

## Introduction

This package provides a FastAPI middleware that enforces [RFC 3230 Digest headers](https://datatracker.ietf.org/doc/html/rfc3230) for HTTP requests. It validates the `Digest` header against the request body, ensuring message integrity and allowing you to specify which digest algorithms are accepted.

## Installation

Install via pip:

```bash
pip install fastapi-rfc3230-digest-header-middleware
```

## Usage Example

Add the middleware to your FastAPI app:

```python
from fastapi import FastAPI, Request
from fastapi_rfc3230_digest_header_middleware import Middleware

app = FastAPI()
app.add_middleware(Middleware)

@app.post("/echo")
async def echo(request: Request):
    body = await request.body()
    return body
```

This will require all POST requests to `/echo` to include a valid `Digest`
header matching the request body.  If the client sends an invalid request, the
server will respond with a `422 Unprocessable Entity` error and include details
about the validation failure. The response will also include a `Want-Digest` header
indicating the accepted digest algorithms.

## Client side

### Sending requests with Digest Header
The client must compute the digest of the request body using one of the accepted
algorithms and include it in the `Digest` header. For example, to compute a
SHA-256 digest in Python you can use the `rfc3230-digest-headers` package:

```python
from rfc3230_digest_headers import create_digest

body = b"Hello, World!"
digest_header = create_digest(body)
headers = {"Digest": digest_header.header_value}
```

if you want to manually create the header, you can do it like this:

```python
import hashlib
import base64
body = b"Hello, World!"
sha256_digest = hashlib.sha256(body).digest()
digest_value = base64.b64encode(sha256_digest).decode('utf-8')
digest_header = f"SHA-256={digest_value}"
headers = {"Digest": digest_header}
```

### Client side handling of Want-Digest Header
The client should also be able to handle the `Want-Digest` header in case of a `422` response. The `rfc3230-digest-headers` package can help with parsing this header as well.

```python
from rfc3230_digest_headers import create_digest
want_digest_header = response.headers.get("Want-Digest", "")

# The `digest_value` will include the appropriate digests according to the server's Want-Digest header
digest_header = create_digest(body, want_digest_header)
```

## Configuration

You can customize which digest algorithms are allowed or provide a custom callback to extract the bytes to validate:

### Allow Only Specific Algorithms

```python
from fastapi import FastAPI, Request
from fastapi_rfc3230_digest_header_middleware import Middleware
from rfc3230_digest_headers import DigestHeaderAlgorithm

qvalues = {
    DigestHeaderAlgorithm.SHA256: None,  # allow SHA-256
    DigestHeaderAlgorithm.MD5: 0.0,      # explicitly reject MD5
}

app = FastAPI()
app.add_middleware(Middleware, qvalues=qvalues)

@app.post("/echo")
async def echo(request: Request):
    body = await request.body()
    return body
```

### Custom Instance Bytes Callback
The `instance` are the bytes the server and client agreed on to include in the
digest. By default, this is the entire request body, but `instance` of a request
may not always be the request body. You can provide a custom callback to extract
the bytes to validate:

```python
async def get_instance_bytes(request: Request) -> bytes:
    # Default instance bytes logic
    return await request.body()

app = FastAPI()
app.add_middleware(Middleware, instance_bytes_callback=get_instance_bytes)
```

# License
MIT License