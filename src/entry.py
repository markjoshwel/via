"""
cloudflare workers entrypoint for via

defines the `Via` worker class and the `ERROR_HTML` template used for
unexpected runtime failures.
"""

from workers import Response, WorkerEntrypoint, Request
from urllib.parse import urlparse
from typing import Final


ERROR_HTML: Final[str] = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>via</title>
    <style>
        * {
            font-family: system-ui, sans, sans-serif;
        }
    </style>
</head>
<body>
    <main>
        <h1>via does not know where to take you.</h1>
        {{reason}}
        <p>you may be lead back to <a href="https://joshwel.co">home</a>, if you wish.</p>
    </main>
</body>
</html>"""


class Via(WorkerEntrypoint):
    """
    link-rerouting cloudflare worker entrypoint for via

    methods:
        `async def _handle_fetch(self, request: Request) -> Response`
            resolve an incoming request into a response
        `async def fetch(self, request: Request)`
            handle the runtime fetch event with a safety wrapper
    """

    async def _handle_fetch(self, request: Request) -> Response:
        """
        handling logic for link routing and rewriting

        arguments:
            `request: Request`
                incoming cloudflare workers request

        returns: `Response`
            response to redirect the client
        """

        # in this case, url.path will always start with a "/"
        url = urlparse(request.url)  # raiseattention: ignore[TypeError, ValueError]

        return Response(repr(url))

    async def fetch(self, request: Request):
        """
        entrypoint and safety wrapper `_handle_fetch`

        if an unexpected exception escapes, this method returns a
        `500 Internal Server Error` page with said exception

        arguments:
            `request: Request`
                incoming cloudflare workers request

        returns: `Response`
            successful route response or rendered `500` error response
        """
        # The `request` parameter passed `fetch()` JavaScript Request object, exposed via
        # Pyodide's JS foreign function interface (FFI).
        # https://developers.cloudflare.com/workers/runtime-apis/request/

        try:
            response = await self._handle_fetch(request)
            return response

        except Exception as exc:
            return Response(
                ERROR_HTML.replace(
                    "{{reason}}",
                    f"something went wrong: {exc} ({exc.__class__.__name__})",
                ),
                headers={"content-type": "text/html;charset=UTF-8"},
                status=500,
            )
