# via

place your hand in theirs, [and be led into the mist](#where-will-you-take-me)

```text
via.joshwel.co/surplus                            # to read
via.joshwel.co/surplus/files                      # to browse
git clone https://via.joshwel.co/surplus@future   # to take, and to give
```

## table of contents

- [why are you, via?](#why-are-you-via)
- [where will you take me?](#where-will-you-take-me)
- [behaviour for selective artifact downloads](#behaviour-for-selective-artifact-downloads)
  - [sometimes it may be not needed](#sometimes-it-may-be-not-needed)
  - [when there are multiple artifacts, where will i go?](#when-there-are-multiple-artifacts-where-will-i-go)
- [how does via know?](#how-does-via-know)
  - [example!](#example)
  - [on dynamic routes](#on-dynamic-routes)
  - [on dynamic route fallback](#on-dynamic-route-fallback)
  - [response codes](#response-codes)
- [development](#development)
- [licencing](#licencing)

## why are you, via?

because a project may be on one git forge, or another

because i'd quite like pretty links for my resume hyperlinks

because short vanity links, especially ones for download, are pretty swell

## where will you take me?

via can take you many places, but usually:

- `/`  
  dedicated webpage if available,
  else the repo for software projects

- `/files`  
  a repository of source code,
  a file sharing link with work/document/project files,
  or adjacent destinations

- `/issues`  
  the issue or bug tracker page for the [usually software] project

- `/docs`  
  the documentation or help page for the [usually software] project,
  if different from the project homepage (`/`)

- `/funding`  
  the funding or sponsorship page for the project if any,
  is also aliased by `/sponsor` and `/sponsors`

- `/downloads`  
  the downloads or releases page for the project,
  or a redirect to a direct download link.

  may be functionally the same as `/files` depending on the project,
  is also aliased by `/releases`

- `/feed`  
  the RSS or Atom feed for the work (project, blog, catalogue) if available

- `/latest`  
  the latest release for a non-software work, such as a blog post

if these main pages are not available, an error page with a hyperlink to
go to `/` will be presented to the user

- `/download/[<TARGET>]`  
  download a digital download artifact of or from the work,
  which depending on the project may be functionally the same as `/files` and `/download`

  for software projects this is an artifact from the latest release

  sometimes, if the selective target (`[<TARGET>]`) does not match anything,
  an error page will be shown with a list of available artifacts,
  presented as hyperlinks to the correct via.joshwel.co link

  see [behaviour for selective artifact downloads](#behaviour-for-selective-artifact-downloads)
  for an explanation of `[<TARGET>]`

- `/download/<TAG>/[<TARGET>]`  
  download a specific release for the software project,
  which depending on the project may be functionally the same
  as `/files` and `/download`

  if the tag is incorrect, an error page will be shown with a list of available tags,
  presented as hyperlinks to the correct via.joshwel.co link

  if the tag is correct, but the selective target does not match anything,
  an error page will be shown with a list of available artifacts,
  presented as hyperlinks to the correct via.joshwel.co link

  see [behaviour for selective artifact downloads](#behaviour-for-selective-artifact-downloads)
  for an explanation of `[<TARGET>]`

## behaviour for selective artifact downloads

### sometimes it may be not needed

some projects, such as pure-python wheels, or non-software projects
with a single artifact, may not have a selective target (`[<TARGET>]`)
parameter, as there is only one artifact to download

in such case, the selective target parameter is optional, and will be ignored
if present, redirecting to the direct download link of the artifact

### when there are multiple artifacts, where will i go?

where you go depends on what you tell via through the selective target
(`[<TARGET>]`) subpath parameter thing

and in the order of which via checks against, the selective target can be a:

1. **release file**  
   example being, `sidestepper-windows-x86_64.exe`

2. **platform**  
   just the platform, very human-friendly.  
   example being, `windows`, `macos`, `linux` (case-insensitive)

   since this is general, and project-specific choices will apply,
   but:

   | platform | arch      | type        | note                     |
   | -------- | --------- | ----------- | ------------------------ |
   | windows  | x86_64    | msvc        | until WoA mass adoption  |
   | macos    | universal | -           | when intel macs are dead |
   | linux    | x86_64    | static musl | for wide compat          |

3. **triple-like extended platform**  
   in which the format would be `<os>-<arch>[-<abi>]`,
   example being `windows-x86_64-msvc`, `macos-x86_64`, `linux-aarch64-gnu`

   synonyms can be used, in case someone is typing out a via link by hand:

   | arch    | synonyms   |
   | ------- | ---------- |
   | x86_64  | amd64, x64 |
   | x86     | -          |
   | aarch64 | arm64      |

4. **a fourth secret thing**  
   in the case of when you pass in the wrong thing, it will fuzzy find the
   closest match, and show you an error page with a redirect to the correct link

## how does via know?

big ass dict + workers making api requests

shown as toml to go easy on the eyes

```toml
[example]
"/"          = "..."
"/issues"    = "..."
"/docs"      = "..."
"/funding"   = "..."
"/downloads" = "..."
"/download"  = ["..."]  # list of file urls
"/feed"      = "..."
# "/latest" is not defined, uses /feed

# or for software projects:

repo   = "..."    # will autofill "/", "/issues", "/downloads"
forges = ["..."]  # in case i host the project on different git forges
```

either `"/"` or a key that autofills it, such as repo, is required.

### example!

```toml
# via.joshwel.co/photos
[photos]
"/" = "https://joshwel.co/photos"
"/feed" = "https://joshwel.co/photos/rss"

# via.joshwel.co/surplus
[surplus]
repo     = "https://surplus.joshwel.co"
funding  = "https://links.joshwel.co/donate"
forges   = ["https://forge.joshwel.co/mark", "https://github.com/markjoshwel"]

# via.joshwel.co/colourmeok
[colourmeok]
repo     = "https://forge.joshwel.co/mark/colourmeok"   
download = ["https://forge.joshwel.co/mark/colourmeok/releases/download/vrelease/ColourMeOK.zip"]
```

### on dynamic routes

the current dynamic links are:

- for strictly non-software works, feeds, lists, or catalogues,

  - `/latest`  
    determined by the latest rss entry

- and else for works with digital downloads,

  - `/download/[<TARGET>]`

    1. if the work has only a single artifact, redirect to that

       ```toml
       downloads = ["https://example.com/cool_photo.jxl"]
       ```

    2. if the selective target is a file name,
       serve it directly if exists

    3. else, if that fails,
       and the `downloads` url is not from a known git forge,
       return an error page

    4. else, we now assert that this is an OSS project,
       and the worker will request from the forge's api for a list of
       artifacts

    5. do a by-name exact match, return if found

    6. else, gather any keywords found in target/platform descriptor schemes
       i use (e.g. `windows`, `x86_64`, `darwin`, `manylinux`, `musl`) and
       build a list of platforms, then return any triples that match

       _why? so i don't have to hardcode links every release_

    7. else, fuzzy find against the files + triples,
       and show an error page with the closest matched artifact
       as a suggested hyperlink

  - `/download/<TAG>/[<TARGET>]`  
    same as non-tagged download, but gets a list of tags first before doing 5-6,
    else returning an error page with the closest matched tag
    as a suggested hyperlink

### on dynamic route fallback

if a dynamic route hits an unexpected handling error, via returns a
**500 Internal Server Error** page with a suggested safe static fallback hyperlink:

- dynamic `/download/...` routes fall back to the static `/downloads` route
- dynamic `/latest` routes fall back to the static `/` route

this fails loud while still giving the user a usable way forward.

### response codes

- **302 Found**  
  for every redirect
- **400 Bad Request**  
  for malformed requests
- **404 Not Found**  
  for error pages
- **405 Method Not Allowed**  
  for unsupported methods
- **500 Internal Server Error**  
  for unexpected parsing, handling, or external service errors

## development

this is a **python** cloudflare worker. you will need `node`, `npm`, and `uv`.

| to do       | you should run             | or               |
| ----------- | -------------------------- | ---------------- |
| setup       | `uv sync`                  |                  |
| deployment  | `uv run pywrangler deploy` | `npm run deploy` |
| development | `uv run pywrangler dev`    | `npm run dev`    |

## licencing

via is dually licensed under the [Unlicense](https://unlicense.org/)
and the [0BSD License](https://opensource.org/licenses/0BSD).

for more information, please refer to [LICENCING](/LICENCING).
