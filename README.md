# via

place your hand in theirs, [and be led into the mist](#where-will-you-take-me-via)

```text
via.joshwel.co/surplus                     # to read
via.joshwel.co/surplus/files               # to browse
git clone https://via.joshwel.co/surplus   # to take, and to give
```

## table of contents

- [why are you, via?](#why-are-you-via)
- [where will you take me, via?](#where-will-you-take-me-via)
  - [the usual places](#the-usual-places)
  - [files, source, assets, stuff](#files-source-assets-stuff)
  - [downloads and artefacts](#downloads-and-artefacts)
    - [when there is only one thing](#when-there-is-only-one-thing)
    - [when there are many things](#when-there-are-many-things)
  - [when via cannot take you there](#when-via-cannot-take-you-there)
- [how does via know?](#how-does-via-know)
  - [helper keys](#helper-keys)
  - [route groups and aliases](#route-groups-and-aliases)
  - [dynamic routes](#dynamic-routes)
- [developing](#developing)
- [licensing](#licensing)

## why are you, via?

because a project may be on one git forge, or another

because i'd quite like pretty links for my resume hyperlinks

because short vanity links, especially ones for download, are pretty swell

and as such, via is a tiny router for my works:
pages, repos, docs, and adjacent little spaces and places

## where will you take me, via?

via can take you many places, but usually:

### the usual places

- `/`  
  dedicated webpage if available,
  else the repo for software projects

- `/issues`  
  the issue or bug tracker page for the usually-software project,
  or something adjacent like a status page for a service

- `/docs`  
  the documentation or help page for the usually-software project,
  if different from the project homepage (`/`)

- `/funding`  
  the funding or sponsorship page for the project if any

  **aliased and reachable by:** `/sponsor` and `/donate`

- `/feed`  
  the RSS or Atom feed for the work (project, blog, catalogue) if available

- `/latest`  
  the latest thing for blogs, catalogues, or an adjacent collection work,

  **aliased and reachable by:** `/newest` and `/recent`

### files, source, assets, stuff

- `/files`  
  where to look at files, source code, media assets, project materials,
  or a direct download link for single-file works

  **aliased and reachable by:** `/repo`, `/source`, `/src`, `/assets`, `/browse`, and `/stuff`

### downloads and artefacts

- `/downloads`  
  the human-facing or pretty downloads/releases page for the work

  may be functionally the same as `/files` depending on the project

  **aliased and reachable by:** `/releases`

- `/download[/<RELEASE>][/<TARGET>]`  
  download a digital download artefact of or from the work

  for software projects this is an artefact from a chosen release (git tag),
  or else the latest release

  see [when via cannot take you there](#when-via-cannot-take-you-there)
  for when a selective release and/or target fails to or cannot be resolved

  see [behaviour for selective artefact downloads](#when-there-are-many-things)
  for an explanation of `[/<RELEASE>][/<TARGET>]`

#### when there is only one thing

some projects, such as pure-python wheels, or non-software projects
with a single artefact, may not have a selective target (`[/<TARGET>]`)
parameter, as there is only one artefact to download

in such case, the selective target parameter is optional, and will be ignored
if present, redirecting to the direct download link of the artefact

#### when there are many things

where you go depends on what you tell via through the selective target
(`[/<TARGET>]`) subpath parameter thing

and in the order of which via checks against, the selective target can be a:

1. **artefact file**  
   example being, `sidestepper-windows-x86_64.exe`

2. **platform**  
   just the platform, very human-friendly.  
   example being, `windows`, `macos`, `linux` (case-insensitive)

   since this is general, and project-specific choices will apply,
   but:

   | platform | arch      | type        | note                                                       |
   | -------- | --------- | ----------- | ---------------------------------------------------------- |
   | windows  | x86_64    | msvc        | until WoA mass adoption or microsoft gives us a fat binary |
   | macos    | universal | -           | until intel macs are dead                                  |
   | linux    | x86_64    | static musl | for wide compatibility                                     |

3. **triple-like extended platform**  
   in which the format would be `<os>-<arch>[-<abi>]`,
   example being `windows-x86_64-msvc`, `macos-x86_64`, `linux-aarch64-gnu`

   synonyms can be used, in case someone is typing out a via link by hand:

   | arch    | synonyms   |
   | ------- | ---------- |
   | x86_64  | amd64, x64 |
   | x86     | -          |
   | aarch64 | arm64      |

4. **a fourth secret thing:** fuzzy fallback  
   in the case of when you pass in the wrong thing, it will fuzzy find the
   closest match, and show you an error page with a redirect to the correct link

### when via cannot take you there

- **static routes**

  e.g. `/files`, `/docs`

  if these main pages are not available, an error page with a hyperlink to
  go to `/` will be presented to the user

- **dynamic routes**

  e.g. `/download[/<RELEASE>][/<TARGET>]`, `/latest`

  if the selective target (`[/<TARGET>]`) does not match anything,
  an error page will be shown with a list of available artefacts,
  presented as hyperlinks to the correct via link

  if the selective release (`[/<RELEASE>]`) is incorrect,
  an error page will be shown with a list of available releases,
  presented as hyperlinks to the correct via link

  if a dynamic route hits an unexpected handling error, via returns a
  **500 Internal Server Error** page with a suggested safe static fallback hyperlink:

  - the dynamic `/download/...` routes fall back to the static `/downloads` route
  - the dynamic `/latest` route fall back to the static `/` route

- **on response codes**

  - **308 Permanent Redirect**  
    for every redirect
  
  - **400 Bad Request**  
    for malformed requests
  
  - **404 Not Found**  
    for error pages
  
  - **405 Method Not Allowed**  
    for unsupported methods
  
  - **500 Internal Server Error**  
    for unexpected parsing, handling, or external service errors

## how does via know?

toml config file for easy reading and writing,
plus workers making api requests

```toml
# via.joshwel.co/photos
[photos]
"/" = "https://joshwel.co/photos"
"/feed" = "https://joshwel.co/photos/rss"

# via.joshwel.co/surplus
[surplus]
"/"        = "https://surplus.joshwel.co"
repo       = "https://github.com/markjoshwel/surplus"
forges     = ["https://forge.joshwel.co/mark/surplus"]
"/funding" = "https://links.joshwel.co/donate"

# via.joshwel.co/colourmeok
[colourmeok]
repo      = "https://forge.joshwel.co/mark/colourmeok"
artifacts = ["https://forge.joshwel.co/mark/colourmeok/releases/download/vrelease/ColourMeOK.zip"]
```

either `"/"` or the helper key that defines it, `repo`, is required

see [`via.example.toml`](/via.example.toml) for a rundown on the configuration file

### helper keys

route keys start with `/`, whereas helper keys do not.

```toml
"/files" = "..."   # public route
repo = "..."       # helper key
forges = [...]     # helper key
artifacts = [...]  # helper key
```

currently, the main helper keys are:

- `repo`  
  source repository for a software-ish work

  will autofill `/` and `/files`

  may autofill `/issues`, `/downloads`, `/releases`, `/feed`,
  and other forge-specific destinations

- `forges`  
  alternative repository links on other git forges

- `artifacts`  
  direct download links used by the dynamic `/download` route

  these live alongside any artefacts that via can discover through a known git forge

user-defined routes will take precedence from any auto-defined keys coming from a helper key

### route groups and aliases

some routes have a group of aliases for mnemonics and convenience,
and you may define exactly one name in the group:

```toml
[poster]
"/assets" = "https://example.com/poster-assets"  # usually `/files`
```

which now means, `via.joshwel.co/{files,repo,source,src,assets,browse,stuff}`
will now all redirect to `https://example.com/poster-assets`

currently, these are the following route groups:

- `/files` route group

 ```text
  /files
  /repo
  /source
  /src
  /assets
  /browse
  /stuff
  ```

- `/funding` route group

  ```text
  /funding
  /sponsor
  /donate
  ```

- `/downloads` route group

  ```text
  /downloads
  /releases
  ```

- `/latest` route group

  ```text
  /latest
  /newest
  /recent
  ```

### dynamic routes

the current dynamic links are:

- for feeds, lists, catalogues, blogs, or adjacent works

  - `/latest`  
    determined by the latest rss entry

    ...unless manually defined to a link (in which then it will be a static route)

- and else for works with digital downloads,

  - `/download[/<RELEASE>][/<TARGET>]`

    where a selective target (`[/<TARGET>]`) may be passed in,
    and where a selective release (`[/<RELEASE>]`) may be passed in,
    via will do the following, in order:

    1. if the work has only a single artefact, redirect to that

       ```toml
       artifacts = ["https://example.com/cool_photo.jxl"]
       ```

    2. if the selective target is a file in `artifacts`,
       redirect to that

    3. else, if that fails,
       and the `/files` url is not from a known git forge,
       return an error page

       (we couldn't find the file you requested in the list of artefacts)

    4. else, if the `/files` url is from a known git forge,
       we can now assert that this is an OSS project

       - if a selective release was provided,
         attempt to grab the list of artefacts from that tagged release

       - else, if no selective release was provided,
         grab the list of artefacts from the latest release

       the resolved release artefacts will be added to the config-provided list of artefacts

       see [when via cannot take you there](#when-via-cannot-take-you-there)
       for when this process fails

    5. if the selective target is a file in the newly-extended list of artefacts,
       redirect to that

    6. else, selective target may be either a
       [platform (windows/macos/linux), or an triple-like extended platform (`<os>-<arch>[-<abi>]`)](#when-there-are-many-things)

       via gathers any keywords found in target/platform descriptor schemes
       i use (e.g. `windows`, `x86_64`, `darwin`, `manylinux`, `musl`) and
       build a list of platforms, then use the matching artefact if any

       _why? so i don't have to hardcode links every release_

    7. else, fuzzy find against the files + triples,
       and show an error page with the closest matched artefact
       as a suggested hyperlink

## developing

this is a **python** cloudflare worker. you will need `node`, `npm`, and `uv`.

the via package is also a command runner for common tasks:

| to do        | you should run         | which in turn runs               | 
| ------------ | ---------------------- | -------------------------------- |
| setup        | `uv sync`              |                                  |
| self-check   | `uv run via selfcheck` | (basedpyright, ruff, mypy)       |
| config check | `uv run via check`     | (config validation)              |
| config sync  | `uv run via sync`      | (sync `via.toml` into entrypoint) |
| deployment   | `uv run via deploy`    | `uv run pywrangler deploy`       |
| development  | `uv run via dev`       | `uv run pywrangler dev`          |

## licensing

via is dually licensed under the [Unlicense](https://unlicense.org/)
and the [0BSD License](https://opensource.org/licenses/0BSD).

for more information, please refer to [LICENCING](/LICENCING).
