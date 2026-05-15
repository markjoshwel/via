"""
via: cloudflare workers entrypoint
  SPDX-License-Identifier: Unlicense OR 0BSD
"""

from collections.abc import Awaitable, Callable
from difflib import get_close_matches
from html import escape
from http import HTTPMethod
import inspect
from pathlib import Path
import tomllib
from typing import Final, NamedTuple, TypeAlias, cast
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

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

CONFIG_TOML: Final[str] = """
#:schema ./via.schema.json

# my babies

[surplus]
"/"        = "https://surplus.joshwel.co"
"/docs"    = "https://surplus.joshwel.co/"
"/funding" = "https://links.joshwel.co/donate"
repo       = "https://github.com/markjoshwel/surplus"
forges     = ["https://forge.joshwel.co/mark/surplus"]

[tomlantic]
"/funding" = "https://links.joshwel.co/donate"
repo = "https://github.com/markjoshwel/tomlantic"

[mulipea]
"/" = "https://gist.github.com/markjoshwel/f4fca0427ef98dd4be397acd6c6086d9"

[restepper]
"/" = "https://github.com/markjoshwel/Depot/blob/main/ReStepper/restepper.py"

[sidestepper]
repo = "https://github.com/markjoshwel/SideStepper"
forges = ["https://forge.joshwel.co/mark/sidestepper"]

# school stuff (immersive media)

[colourmeok]
repo      = "https://github.com/markjoshwel/ColourMeOK"
artifacts = ["https://github.com/markjoshwel/ColourMeOK/releases/download/vrelease/ColourMeOK-v3.zip"]

[pokkat]
repo = "https://github.com/markjoshwel/pokkat"

[alookingglass]
repo = "https://github.com/markjoshwel/sota32"

[id-asg1]
"/" = "https://markjoshwel.github.io/id-asg1/"

# secondary school stuff

[portfolio-eae]
"/" = "https://markjoshwel.github.io/portfolio-eae/"

[hounds]
repo = "https://github.com/markjoshwel/hounds"

# experiments

[sinsandvirtues]
"/" = "https://github.com/markjoshwel/Depot/tree/main/sinsandvirtues"

[irodorio4]
"/" = "https://github.com/markjoshwel/Depot/tree/main/irodorio4"

# vibecoded tools and experiments

[raiseattention]
repo = "https://github.com/markjoshwel/RaiseAttention"

[mares]
repo = "https://github.com/markjoshwel/mares"

[meadow]
repo = "https://github.com/markjoshwel/meadow"

[via]
repo = "https://github.com/markjoshwel/via"

# blogs/collections/catalogues

[blog]
"/" = "https://majo.bearblog.dev/"
"/feed" = "https://majo.bearblog.dev/feed/"
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
JsonObject: TypeAlias = dict[str, object]


class DownloadRequest(NamedTuple):
    """
    parsed dynamic download route

    attributes:
        `release: str | None`
            requested release tag, if present
        `target: str | None`
            requested artefact target, if present
    """

    release: str | None = None
    target: str | None = None


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


BUNDLED_CONFIG: Final[Config] = coerce_config(
    cast(dict[object, object], tomllib.loads(CONFIG_TOML))
)


def first_defined(
    work: WorkConfig | dict[str, str], keys: tuple[str, ...]
) -> str | None:
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


def repo_path_parts(repo: str) -> tuple[str, str] | None:
    """
    return owner and repository path parts for a forge repository URL

    arguments:
        `repo: str`
            repository URL

    returns: `tuple[str, str] | None`
        owner and repository name when the URL is usable
    """

    path_parts = [part for part in urlparse(repo).path.split("/") if part]
    if len(path_parts) < 2:
        return None
    return path_parts[0], path_parts[1]


def release_api_url(repo: str, release: str | None) -> str | None:
    """
    return the release API URL for a supported forge

    arguments:
        `repo: str`
            repository URL
        `release: str | None`
            requested release tag, if present

    returns: `str | None`
        release API URL, if the forge is recognised
    """

    repo_parts = repo_path_parts(repo)
    if repo_parts is None:
        return None

    owner, name = repo_parts
    parsed = urlparse(repo)
    kind = forge_kind(repo)
    if kind == "github":
        base = f"https://api.github.com/repos/{owner}/{name}/releases"
    elif kind == "forgejo":
        base = f"{parsed.scheme}://{parsed.netloc}/api/v1/repos/{owner}/{name}/releases"
    else:
        return None

    if release is None:
        return f"{base}/latest"
    return f"{base}/tags/{release}"


def releases_api_url(repo: str) -> str | None:
    """
    return the releases API URL for a supported forge

    arguments:
        `repo: str`
            repository URL

    returns: `str | None`
        releases API URL, if the forge is recognised
    """

    latest_url = release_api_url(repo, None)
    if latest_url is None:
        return None
    return latest_url.removesuffix("/latest")


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


async def response_json(response: Response) -> object:
    """
    read a Worker response body as JSON

    arguments:
        `response: Response`
            fetch response

    returns: `object`
        decoded JSON value
    """

    json_method = cast(Callable[[], object], getattr(response, "json"))
    value = json_method()
    if inspect.isawaitable(value):
        value = await cast(Awaitable[object], value)
    return value


async def response_text(response: Response) -> str:
    """
    read a Worker response body as text

    arguments:
        `response: Response`
            fetch response

    returns: `str`
        response body text
    """

    text_method = cast(Callable[[], object], getattr(response, "text"))
    value = text_method()
    if inspect.isawaitable(value):
        value = await cast(Awaitable[object], value)
    return value if isinstance(value, str) else ""


def release_artifacts_from_json(value: object) -> list[str]:
    """
    extract artefact download URLs from a forge release response

    arguments:
        `value: object`
            decoded release API response

    returns: `list[str]`
        artefact download URLs
    """

    if not isinstance(value, dict):
        return []

    release = cast(JsonObject, value)
    raw_assets = release.get("assets")
    if not isinstance(raw_assets, list):
        return []

    assets = cast(list[object], raw_assets)
    artifacts: list[str] = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue

        raw_asset = cast(JsonObject, asset)
        download_url = raw_asset.get("browser_download_url")
        if not isinstance(download_url, str):
            download_url = raw_asset.get("download_url")

        if isinstance(download_url, str):
            artifacts.append(download_url)

    return artifacts


async def release_artifacts(repo: str, release: str | None) -> list[str]:
    """
    fetch release artefact URLs from a supported forge

    arguments:
        `repo: str`
            repository URL
        `release: str | None`
            requested release tag, if present

    returns: `list[str]`
        release artefact URLs
    """

    api_url = release_api_url(repo, release)
    if api_url is None:
        return []

    try:
        response: Response = await cf_fetch(
            api_url,
            method=HTTPMethod.GET,
            headers={
                "accept": "application/json",
                "user-agent": "via",
            },
        )
        status = getattr(response, "status", 0)
        if not isinstance(status, int) or not 200 <= status < 300:
            return []

        return release_artifacts_from_json(await response_json(response))
    except Exception:
        return []


def release_tags_from_json(value: object) -> list[str]:
    """
    extract release tags from a forge releases response

    arguments:
        `value: object`
            decoded releases API response

    returns: `list[str]`
        release tags
    """

    if not isinstance(value, list):
        return []

    releases = cast(list[object], value)
    tags: list[str] = []
    for release in releases:
        if not isinstance(release, dict):
            continue

        raw_release = cast(JsonObject, release)
        tag = raw_release.get("tag_name")
        if isinstance(tag, str):
            tags.append(tag)

    return tags


async def release_tags(repo: str) -> list[str]:
    """
    fetch release tags from a supported forge

    arguments:
        `repo: str`
            repository URL

    returns: `list[str]`
        release tags
    """

    api_url = releases_api_url(repo)
    if api_url is None:
        return []

    try:
        response: Response = await cf_fetch(
            api_url,
            method=HTTPMethod.GET,
            headers={
                "accept": "application/json",
                "user-agent": "via",
            },
        )
        status = getattr(response, "status", 0)
        if not isinstance(status, int) or not 200 <= status < 300:
            return []

        return release_tags_from_json(await response_json(response))
    except Exception:
        return []


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


def parse_download_route(route: str) -> DownloadRequest:
    """
    parse release and target selectors from a dynamic download route

    arguments:
        `route: str`
            normalised `/download` route

    returns: `DownloadRequest`
        parsed release and target selectors
    """

    parts = [part for part in route.removeprefix("/download").split("/") if part]
    if not parts:
        return DownloadRequest()

    if len(parts) == 1:
        part = parts[0]
        if "." in part:
            return DownloadRequest(target=part)
        return DownloadRequest(release=part)

    return DownloadRequest(release=parts[0], target=parts[-1])


def merge_artifacts(*artifact_groups: list[str]) -> list[str]:
    """
    merge artefact URL groups without duplicates

    arguments:
        `*artifact_groups: list[str]`
            artefact URL groups in preference order

    returns: `list[str]`
        deduplicated artefact URLs
    """

    artifacts: list[str] = []
    for group in artifact_groups:
        for artifact in group:
            if artifact not in artifacts:
                artifacts.append(artifact)
    return artifacts


def artifact_links(
    slug: str,
    artifacts: list[str],
    release: str | None = None,
    target: str | None = None,
) -> str:
    """
    render available artifacts as a link list

    arguments:
        `slug: str`
            work slug
        `artifacts: list[str]`
            artifact URLs
        `release: str | None`
            release tag to preserve in generated links
        `target: str | None`
            unmatched target, if present

    returns: `str`
        HTML list fragment
    """

    if not artifacts:
        return "<p>no download artefacts are known for this work.</p>"

    items: list[str] = []
    for artifact in artifacts:
        name = filename(artifact)
        href = (
            f"/{slug}/download/{release}/{name}"
            if release
            else f"/{slug}/download/{name}"
        )
        items.append(f'<li><a href="{escape(href)}">{escape(name)}</a></li>')

    closest = ""
    if target is not None:
        filenames = [filename(artifact) for artifact in artifacts]
        matches = get_close_matches(target, filenames, n=1)
        if matches:
            match = matches[0]
            href = (
                f"/{slug}/download/{release}/{match}"
                if release
                else f"/{slug}/download/{match}"
            )
            closest = (
                f'<p>closest match: <a href="{escape(href)}">{escape(match)}</a></p>'
            )

    return f"{closest}<p>available artefacts:</p><ul>{''.join(items)}</ul>"


def release_links(slug: str, releases: list[str]) -> str:
    """
    render available releases as a link list

    arguments:
        `slug: str`
            work slug
        `releases: list[str]`
            release tags

    returns: `str`
        HTML list fragment
    """

    if not releases:
        return "<p>no releases are known for this work.</p>"

    items: list[str] = []
    for release in releases:
        href = f"/{slug}/download/{release}"
        items.append(f'<li><a href="{escape(href)}">{escape(release)}</a></li>')
    return f"<p>available releases:</p><ul>{''.join(items)}</ul>"


def element_name(element: ElementTree.Element) -> str:
    """
    return an XML element name without its namespace

    arguments:
        `element: ElementTree.Element`
            XML element

    returns: `str`
        local element name
    """

    return element.tag.rsplit("}", 1)[-1].lower()


def child_text(element: ElementTree.Element, name: str) -> str | None:
    """
    return the first direct child text value by local element name

    arguments:
        `element: ElementTree.Element`
            parent XML element
        `name: str`
            local child element name

    returns: `str | None`
        stripped text value, if present
    """

    for child in element:
        if element_name(child) != name:
            continue

        text = child.text
        if text is not None and text.strip():
            return text.strip()

    return None


def atom_entry_link(entry: ElementTree.Element) -> str | None:
    """
    return the preferred URL from an Atom entry

    arguments:
        `entry: ElementTree.Element`
            Atom entry element

    returns: `str | None`
        entry URL, if present
    """

    fallback: str | None = None
    for child in entry:
        if element_name(child) != "link":
            continue

        href = child.attrib.get("href")
        if href is None or not href.strip():
            continue

        href = href.strip()
        if child.attrib.get("rel", "alternate") == "alternate":
            return href
        fallback = fallback or href

    return fallback or child_text(entry, "id")


def latest_entry_url(feed_xml: str, feed_url: str) -> str | None:
    """
    return the URL for the first RSS item or Atom entry

    arguments:
        `feed_xml: str`
            feed XML document
        `feed_url: str`
            source feed URL, used for resolving relative links

    returns: `str | None`
        latest entry URL, if one can be found
    """

    try:
        root = ElementTree.fromstring(feed_xml)
    except ElementTree.ParseError:
        return None

    for element in root.iter():
        name = element_name(element)
        if name == "item":
            link = child_text(element, "link") or child_text(element, "guid")
            return urljoin(feed_url, link) if link is not None else None
        if name == "entry":
            link = atom_entry_link(element)
            return urljoin(feed_url, link) if link is not None else None

    return None


async def resolve_latest(routes: dict[str, str]) -> RouteResult | Response:
    """
    resolve `/latest` from a configured RSS or Atom feed

    arguments:
        `routes: dict[str, str]`
            expanded route mapping

    returns: `RouteResult | Response`
        latest entry redirect or rendered error response
    """

    feed_url = routes.get("/feed")
    if feed_url is None:
        return html_response(
            "via does not know the latest thing.",
            "<p>no feed is known for this work.</p>",
            404,
        )

    try:
        response: Response = await cf_fetch(
            feed_url,
            method=HTTPMethod.GET,
            headers={"user-agent": "via"},
        )
        status = getattr(response, "status", 0)
        if not isinstance(status, int) or not 200 <= status < 300:
            raise ValueError(f"feed returned HTTP {status}")

        latest_url = latest_entry_url(await response_text(response), feed_url)
        if latest_url is not None:
            return RouteResult(latest_url)
    except Exception:
        pass

    fallback = routes.get("/")
    body = "<p>the latest feed entry could not be resolved.</p>"
    if fallback is not None:
        body += f'<p>you may be led back to <a href="{escape(fallback)}">the work</a>, if you wish.</p>'
    return html_response("via does not know the latest thing.", body, 404)


async def resolve_download(
    slug: str, work: WorkConfig, route: str
) -> RouteResult | Response:
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

    request = parse_download_route(route)
    configured_artifacts = artifacts_for(work)
    matched = match_artifact(configured_artifacts, request.target)

    if matched is not None:
        return RouteResult(matched)

    selected_repo = await choose_repo(work)
    discovered_artifacts = (
        await release_artifacts(selected_repo, request.release)
        if selected_repo is not None
        else []
    )
    artifacts = merge_artifacts(configured_artifacts, discovered_artifacts)
    matched = match_artifact(artifacts, request.target)

    if matched is not None:
        return RouteResult(matched)

    if (
        selected_repo is not None
        and request.release is not None
        and not discovered_artifacts
    ):
        return html_response(
            "via does not know this release.",
            release_links(slug, await release_tags(selected_repo)),
            404,
        )

    return html_response(
        "via does not know which artefact you want.",
        artifact_links(slug, artifacts, request.release, request.target),
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
        return await resolve_download(slug, work, route)

    selected_repo = await choose_repo(work)
    selected_work = with_selected_repo(work, selected_repo)
    routes = expand_routes(selected_work)
    destination = routes.get(route)
    if destination is not None:
        return RouteResult(destination)

    if route in LATEST_ALIASES:
        return await resolve_latest(routes)

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
    result = await resolve_route(slug, route, BUNDLED_CONFIG, parsed.query)

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
