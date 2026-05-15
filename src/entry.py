"""
via: cloudflare workers entrypoint
  SPDX-License-Identifier: Unlicense OR 0BSD
"""

from html import escape
from http import HTTPMethod
from pathlib import Path
import tomllib
from typing import Final, NamedTuple, cast
from urllib.parse import urlparse

from workers import Request, Response, WorkerEntrypoint
from workers._workers import fetch as cf_fetch  # pyright: ignore[reportUnknownVariableType]


HTML: Final[str] = """<!DOCTYPE html>
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
        <h1>{{title}}</h1>
        {{body}}
    </main>
</body>
</html>"""

CONFIG_PATHS: Final[tuple[Path, ...]] = (
    Path("via.toml"),
    Path(__file__).parent.parent / "via.toml",
)
CONFIG_TOML: Final[str] = """
[surplus]
"/"        = "https://surplus.joshwel.co"
repo       = "https://github.com/markjoshwel/surplus"
"/docs"       = "https://surplus.joshwel.co/"
forges     = ["https://forge.joshwel.co/mark/surplus"]
"/funding" = "https://links.joshwel.co/donate"

[colourmeok]
repo      = "https://forge.joshwel.co/mark/colourmeok"
artifacts = ["https://forge.joshwel.co/mark/colourmeok/releases/download/vrelease/ColourMeOK.zip"]

[mulipea]
"/" = "https://gist.github.com/markjoshwel/f4fca0427ef98dd4be397acd6c6086d9"

[restepper]
"/" = "https://github.com/markjoshwel/Depot/blob/main/ReStepper/restepper.py"

[sidestepper]
repo = "https://github.com/markjoshwel/SideStepper"
forges = ["https://forge.joshwel.co/mark/sidestepper"]

[sinsandvirtues]
"/" = "https://github.com/markjoshwel/Depot/tree/main/sinsandvirtues"

[irodorio4]
"/" = "https://github.com/markjoshwel/Depot/tree/main/irodorio4"

[pokkat]
repo = "https://forge.joshwel.co/mark/pokkat"

[alookingglass]
repo = "https://forge.joshwel.co/mark/sota32/"

[raiseattention]
repo = "https://github.com/markjoshwel/RaiseAttention"

[mares]
repo = "https://github.com/markjoshwel/mares"

[meadow]
repo = "https://github.com/markjoshwel/meadow"

[tomlantic]
repo = "https://github.com/markjoshwel/tomlantic"

[via]
repo = "https://github.com/markjoshwel/via"

[hounds]
repo = "https://github.com/markjoshwel/hounds"

[portfolio-eae]
"/" = "https://markjoshwel.github.io/portfolio-eae/"

[id-asg1]
"/" = "https://markjoshwel.github.io/id-asg1/"
"""

FILES_ALIASES: Final[tuple[str, ...]] = (
    "/files",
    "/repo",
    "/source",
    "/src",
    "/assets",
    "/browse",
    "/stuff",
)
FUNDING_ALIASES: Final[tuple[str, ...]] = ("/funding", "/sponsor", "/donate")
DOWNLOADS_ALIASES: Final[tuple[str, ...]] = ("/downloads", "/releases")
LATEST_ALIASES: Final[tuple[str, ...]] = ("/latest", "/newest", "/recent")
ROUTE_GROUPS: Final[tuple[tuple[str, ...], ...]] = (
    FILES_ALIASES,
    FUNDING_ALIASES,
    DOWNLOADS_ALIASES,
    LATEST_ALIASES,
)

ARCH_ALIASES: Final[dict[str, str]] = {
    "amd64": "x86_64",
    "x64": "x86_64",
    "arm64": "aarch64",
}
REPO_DERIVED_ROUTES: Final[tuple[str, ...]] = (
    "/",
    "/files",
    "/issues",
    "/downloads",
    "/feed",
)
PLATFORM_KEYWORDS: Final[dict[str, tuple[str, ...]]] = {
    "windows": ("windows", "win", "win32", "win64", "msvc", ".exe", ".msi"),
    "macos": ("macos", "darwin", "apple", "osx", ".dmg", ".pkg"),
    "linux": ("linux", "gnu", "musl", "manylinux", ".appimage"),
}


class RouteResult(NamedTuple):
    """
    resolved route details

    attributes:
        `url: str`
            destination URL
        `status: int`
            HTTP response status
    """

    url: str
    status: int = 308


ConfigValue = str | list[str]
WorkConfig = dict[str, ConfigValue]
Config = dict[str, WorkConfig]


def html_response(title: str, body: str, status: int) -> Response:
    """
    render a simple HTML response

    arguments:
        `title: str`
            page heading
        `body: str`
            HTML body fragment
        `status: int`
            HTTP response status

    returns: `Response`
        rendered Cloudflare Worker response
    """

    return Response(
        HTML.replace("{{title}}", escape(title)).replace("{{body}}", body),
        headers={"content-type": "text/html;charset=UTF-8"},
        status=status,
    )


def redirect_response(url: str) -> Response:
    """
    create a permanent redirect response

    arguments:
        `url: str`
            destination URL

    returns: `Response`
        HTTP 308 redirect response
    """

    return Response("", headers={"location": url}, status=308)


def load_config() -> Config:
    """
    load the bundled via configuration

    returns: `Config`
        parsed TOML configuration

    raises:
        `FileNotFoundError`
            no bundled via.toml was found
    """

    for path in CONFIG_PATHS:
        if path.exists():
            with path.open("rb") as file:
                return coerce_config(cast(dict[object, object], tomllib.load(file)))

    return coerce_config(cast(dict[object, object], tomllib.loads(CONFIG_TOML)))


def coerce_config(raw_config: dict[object, object]) -> Config:
    """
    narrow raw TOML data into the supported via config shape

    arguments:
        `raw_config: dict[object, object]`
            parsed TOML document

    returns: `Config`
        supported via configuration
    """

    config: Config = {}
    for work, value in raw_config.items():
        if isinstance(work, str) and isinstance(value, dict):
            raw_work = cast(dict[object, object], value)
            config[work] = coerce_work_config(raw_work)
    return config


def coerce_work_config(raw_work: dict[object, object]) -> WorkConfig:
    """
    narrow raw TOML values into the supported via work shape

    arguments:
        `raw_work: dict[object, object]`
            parsed TOML table

    returns: `WorkConfig`
        supported string and string-list entries
    """

    work: WorkConfig = {}
    for key, value in raw_work.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, str):
            work[key] = value
        elif isinstance(value, list):
            items = cast(list[object], value)
            if all(isinstance(item, str) for item in items):
                work[key] = cast(list[str], items.copy())
    return work


def first_defined(work: WorkConfig | dict[str, str], keys: tuple[str, ...]) -> str | None:
    """
    return the first string value for the requested keys

    arguments:
        `work: WorkConfig | dict[str, str]`
            work configuration
        `keys: tuple[str, ...]`
            route aliases to check

    returns: `str | None`
        configured URL, if any
    """

    for key in keys:
        value = work.get(key)
        if isinstance(value, str):
            return value

    return None


def normalise_route(route: str) -> str:
    """
    normalise an incoming route path

    arguments:
        `route: str`
            incoming route path below the work slug

    returns: `str`
        canonical route shape
    """

    if route == "":
        return "/"

    route = "/" + route.strip("/")
    return route or "/"


def forge_kind(repo: str) -> str | None:
    """
    identify a supported source forge URL

    arguments:
        `repo: str`
            repository URL

    returns: `str | None`
        forge identifier, if recognised
    """

    host = urlparse(repo).netloc.lower()
    if host == "github.com":
        return "github"
    if host in {"forge.joshwel.co", "codeberg.org"}:
        return "forgejo"
    return None


def expand_routes(work: WorkConfig) -> dict[str, str]:
    """
    expand helper keys and route aliases into concrete routes

    arguments:
        `work: WorkConfig`
            work configuration

    returns: `dict[str, str]`
        route-to-destination mapping
    """

    routes: dict[str, str] = {}
    repo = work.get("repo")

    if isinstance(repo, str):
        routes["/"] = repo
        routes["/files"] = repo

        kind = forge_kind(repo)
        if kind == "github":
            routes["/issues"] = f"{repo.rstrip('/')}/issues"
            routes["/downloads"] = f"{repo.rstrip('/')}/releases"
            routes["/feed"] = f"{repo.rstrip('/')}/releases.atom"
        elif kind == "forgejo":
            routes["/issues"] = f"{repo.rstrip('/')}/issues"
            routes["/downloads"] = f"{repo.rstrip('/')}/releases"
            routes["/feed"] = f"{repo.rstrip('/')}.rss"

    for key, value in work.items():
        if key.startswith("/") and isinstance(value, str):
            routes[key.rstrip("/") or "/"] = value

    for group in ROUTE_GROUPS:
        destination = first_defined(routes, group)
        if destination is not None:
            for alias in group:
                routes[alias] = destination

    return routes


def repo_candidates(work: WorkConfig) -> list[str]:
    """
    return primary and fallback repository URLs

    arguments:
        `work: WorkConfig`
            work configuration

    returns: `list[str]`
        repository URLs in fallback order
    """

    candidates: list[str] = []
    repo = work.get("repo")
    if isinstance(repo, str):
        candidates.append(repo)

    forges = work.get("forges")
    if isinstance(forges, list):
        candidates.extend(forges)

    deduplicated: list[str] = []
    for candidate in candidates:
        if candidate not in deduplicated:
            deduplicated.append(candidate)
    return deduplicated


async def repo_is_reachable(repo: str) -> bool:
    """
    check whether a repository URL appears reachable

    arguments:
        `repo: str`
            repository URL

    returns: `bool`
        whether the forge returned a non-error response
    """

    try:
        response: Response = await cf_fetch(
            repo,
            method=HTTPMethod.HEAD,
            redirect="follow",
        )
        status = getattr(response, "status", 0)
        return isinstance(status, int) and 200 <= status < 500
    except Exception:
        return False


async def choose_repo(work: WorkConfig) -> str | None:
    """
    choose the first reachable repository URL

    arguments:
        `work: WorkConfig`
            work configuration

    returns: `str | None`
        selected repository URL, if configured
    """

    candidates = repo_candidates(work)
    if not candidates:
        return None

    for candidate in candidates:
        if await repo_is_reachable(candidate):
            return candidate

    return candidates[0]


def with_selected_repo(work: WorkConfig, repo: str | None) -> WorkConfig:
    """
    return a work config using the selected repo URL

    arguments:
        `work: WorkConfig`
            original work configuration
        `repo: str | None`
            selected repository URL

    returns: `WorkConfig`
        work configuration with repo overridden when available
    """

    if repo is None:
        return work

    selected = work.copy()
    selected["repo"] = repo
    return selected


def artifacts_for(work: WorkConfig) -> list[str]:
    """
    return configured artifact URLs

    arguments:
        `work: WorkConfig`
            work configuration

    returns: `list[str]`
        artifact URLs
    """

    value = work.get("artifacts")
    if not isinstance(value, list):
        return []

    return value.copy()


def filename(url: str) -> str:
    """
    return the filename segment of a URL

    arguments:
        `url: str`
            artifact URL

    returns: `str`
        final path segment
    """

    return Path(urlparse(url).path).name


def target_keywords(target: str) -> set[str]:
    """
    split a selective download target into comparable keywords

    arguments:
        `target: str`
            selective target from `/download/...`

    returns: `set[str]`
        normalised keywords
    """

    words = {
        ARCH_ALIASES.get(part, part)
        for part in target.lower().replace("_", "-").split("-")
        if part
    }
    for platform, keywords in PLATFORM_KEYWORDS.items():
        if target.lower() == platform:
            words.update(keywords)
    return words


def match_artifact(artifacts: list[str], target: str | None) -> str | None:
    """
    match a selective target against configured artifacts

    arguments:
        `artifacts: list[str]`
            artifact URLs
        `target: str | None`
            optional target selector

    returns: `str | None`
        matched artifact URL, if any
    """

    if len(artifacts) == 1:
        return artifacts[0]

    if target is None:
        return None

    target_lower = target.lower()
    for artifact in artifacts:
        if filename(artifact).lower() == target_lower:
            return artifact

    keywords = target_keywords(target)
    if not keywords:
        return None

    for artifact in artifacts:
        artifact_name = filename(artifact).lower().replace("_", "-")
        if all(keyword in artifact_name for keyword in keywords):
            return artifact

    return None


def artifact_links(slug: str, artifacts: list[str]) -> str:
    """
    render available artifacts as a link list

    arguments:
        `slug: str`
            work slug
        `artifacts: list[str]`
            artifact URLs

    returns: `str`
        HTML list fragment
    """

    if not artifacts:
        return "<p>no download artefacts are known for this work.</p>"

    items: list[str] = []
    for artifact in artifacts:
        name = filename(artifact)
        href = f"/{slug}/download/{name}"
        items.append(f'<li><a href="{escape(href)}">{escape(name)}</a></li>')
    return f"<p>available artefacts:</p><ul>{''.join(items)}</ul>"


def resolve_download(slug: str, work: WorkConfig, route: str) -> RouteResult | Response:
    """
    resolve a `/download` route

    arguments:
        `slug: str`
            work slug
        `work: WorkConfig`
            work configuration
        `route: str`
            normalised incoming route

    returns: `RouteResult | Response`
        redirect target or rendered error response
    """

    artifacts = artifacts_for(work)
    parts = [part for part in route.removeprefix("/download").split("/") if part]
    target = parts[-1] if parts else None
    matched = match_artifact(artifacts, target)

    if matched is not None:
        return RouteResult(matched)

    return html_response(
        "via does not know which artefact you want.",
        artifact_links(slug, artifacts),
        404,
    )


async def resolve_route(
    slug: str,
    route: str,
    config: Config,
    query: str = "",
) -> RouteResult | Response:
    """
    resolve an incoming via route

    arguments:
        `slug: str`
            work slug
        `route: str`
            route below work slug
        `config: Config`
            parsed via configuration
        `query: str`
            original URL query string

    returns: `RouteResult | Response`
        redirect target or rendered response
    """

    work = config.get(slug)
    if work is None:
        return html_response(
            "via does not know this work.",
            '<p>you may be led back to <a href="https://joshwel.co">home</a>, if you wish.</p>',
            404,
        )

    route = normalise_route(route)
    if route == "/download" or route.startswith("/download/"):
        return resolve_download(slug, work, route)

    selected_repo = await choose_repo(work)
    selected_work = with_selected_repo(work, selected_repo)
    routes = expand_routes(selected_work)
    destination = routes.get(route)
    if destination is not None:
        return RouteResult(destination)

    if selected_repo is not None and route != "/":
        destination = f"{selected_repo.rstrip('/')}{route}"
        if query:
            destination = f"{destination}?{query}"
        return RouteResult(destination)

    fallback = routes.get("/")
    body = "<p>that route is not available for this work.</p>"
    if fallback is not None:
        body += f'<p>you may be led back to <a href="{escape(fallback)}">the work</a>, if you wish.</p>'
    return html_response("via does not know where to take you.", body, 404)


async def handle_request(request: Request) -> Response:
    """
    handle an incoming Worker request

    arguments:
        `request: Request`
            incoming cloudflare workers request

    returns: `Response`
        resolved via response
    """

    method = getattr(request, "method", "GET")
    if method not in {"GET", "HEAD"}:
        return Response(
            "method not allowed",
            headers={"allow": "GET, HEAD"},
            status=405,
        )

    # in this case, parsed.path will always start with a "/"
    parsed = urlparse(request.url)
    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        return html_response(
            "via does not know where to take you.",
            '<p>try a work path such as <a href="/via">/via</a>.</p>',
            404,
        )

    slug = parts[0].lower()
    route = "/".join(parts[1:])
    result = await resolve_route(slug, route, load_config(), parsed.query)

    if isinstance(result, Response):
        return result
    return redirect_response(result.url)


def internal_error_response(exc: Exception) -> Response:
    """
    render an unexpected runtime error

    arguments:
        `exc: Exception`
            unexpected exception

    returns: `Response`
        HTTP 500 error response
    """

    return html_response(
        "via does not know where to take you.",
        (
            "<p>something went wrong: "
            f"{escape(str(exc))} ({escape(exc.__class__.__name__)})</p>"
            '<p>you may be led back to <a href="https://joshwel.co">home</a>, if you wish.</p>'
        ),
        500,
    )


class Default(WorkerEntrypoint):
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

        return await handle_request(request)

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
            return internal_error_response(exc)


Via = Default
"""
backwards-compatible name for the via worker implementation
"""


async def fetch(request: Request) -> Response:
    """
    module-level fetch bridge for runtimes expecting a function export

    arguments:
        `request: Request`
            incoming cloudflare workers request

    returns: `Response`
        resolved via response
    """

    try:
        return await handle_request(request)
    except Exception as exc:
        return internal_error_response(exc)
