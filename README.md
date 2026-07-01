# tiny-wiki

A tiny markdown-based wiki. Renders markdown documents provided by `items.json`, with a list of all documents at the left, and a list of the headings (levels 2+) at the right

No frameworks, just a bit of Javascript, HTML 5 and CSS.

## Setup

Just run it via any web server, e.g. [http-server](https://www.npmjs.com/package/http-server).

## Development

- CSS via https://picocss.com/docs/
- Markdown via https://marked.js.org

## Scripts

`scripts/convert_raw_links.py` finds raw URLs in markdown files (e.g. `https://example.com`) that aren't wrapped in markdown link syntax, since marked.js won't autolink them.

```sh
# report raw links found under a file or directory (exit code 1 if any found)
python3 scripts/convert_raw_links.py md/data

# rewrite files in place, wrapping raw URLs as [url](url)
python3 scripts/convert_raw_links.py md/data --fix

# suppress output, e.g. when only the exit code matters (scripting/CI)
python3 scripts/convert_raw_links.py md/data --quiet
```

`scripts/convert_google_redirects.py` finds old Google redirect links (`http://www.google.com/url?q=...`) and replaces them with their decoded `https://` target, whether the link is bare or already wrapped in markdown link syntax. Same `--fix` / `--quiet` flags and exit code convention as `convert_raw_links.py`.

```sh
python3 scripts/convert_google_redirects.py md/data
python3 scripts/convert_google_redirects.py md/data --fix
```

## Testing

Run tests with `python3 -m unittest discover scripts/tests`.
