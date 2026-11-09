# AGENTS.md — Trackingo Bus Tracker

Read this before changing anything in this repo. It tells you what the
project is, where things live, how to run and test it, and the privacy
rules that are not negotiable.

## What this is

A live bus tracker for Indian bus operators that use Trackingo (Bitla
Software's fleet tracker, reached via RedBus or directly). The operator
sends a tracking link; the link opens a Trackingo page that polls its
own internal API about every 20 seconds for the bus's GPS position.

This repo calls that same API directly, two ways:

- a command-line tool (Python, zero dependencies) that prints the live
  position, speed, and ETA for every stop
- a website (static site + a small serverless proxy) that shows the
  same thing in a browser

The Trackingo endpoints are the tracker page's **internal endpoints,
not a published developer API**. They worked without a login, they may
change without notice, and there is no public documentation for them.
Use them for your own tracking link, at your own risk, and respect the
site's terms.

The key lesson the tool is built around: trust the GPS fix, not the
status line. RedBus's public status text (for example "Next: K R
Puram") is easy to read as "the bus already passed ITI Gate". The GPS
fields — latitude/longitude, speed, GPS timestamp, location — say
where the bus actually is. If `arrival_time` for a stop is empty, the
bus has not reached that stop yet, whatever the status text says.

## Layout

```
README.md                  # user-facing docs: what it is, how to use it
AGENTS.md                  # this file: contributor/agent docs
LICENSE                    # MIT
pyproject.toml             # packaging; console script `trackingo-tracker`
src/trackingo_tracker/
  client.py                # fetch + parse + format + watch loop
  __main__.py              # CLI entry point
  __init__.py
tests/test_parse.py        # parser test, plain Python, no pytest needed
examples/sample_eta_map.json  # fictional example response, clearly labelled
docs/
  images/                  # the three diagrams used in the README
  make_images.py           # regenerates the diagrams (matplotlib)
web/                       # the website (see "Website" below)
  index.html               # single-page tracker UI
  app.js                   # UI logic: demo mode, live mode, polling
  style.css
  api/live.py              # Vercel serverless proxy to the Trackingo API
  api/sample_eta_map.json  # fictional example data for demo mode
  images/                  # diagrams reused from docs/
deploy/vercel_deploy.py    # deploys web/ to Vercel with a stored API token
```

## CLI — how to run it

Python 3.10+, no dependencies beyond the standard library.

```bash
# Demo with bundled example data: no key, no network
PYTHONPATH=src python3 -m trackingo_tracker --demo

# One live check for your own bus
PYTHONPATH=src python3 -m trackingo_tracker --key YOUR_KEY --once

# Keep watching, like the tracker page does (every 20 seconds)
PYTHONPATH=src python3 -m trackingo_tracker --key YOUR_KEY

# Raw JSON instead of the table
PYTHONPATH=src python3 -m trackingo_tracker --key YOUR_KEY --once --json

# Journey details instead of the live map (may include booking/contact fields)
PYTHONPATH=src python3 -m trackingo_tracker --key YOUR_KEY --journey --once
```

After `pip install .`, the same commands work as `trackingo-tracker`.

Your tracking key is the key in your own tracking link — the short
link the operator sends you redirects to
`bus.trackingo.in/customer/track_vehicle?<KEY>`.

## Website — how it works

Live at https://trackingo-bus-tracker.vercel.app/

- `web/index.html` + `app.js` + `style.css` are a static single-page
  site. Open it and it runs in demo mode on the bundled fictional trip
  (bus idle at B. Narayanapura, 28 minutes late, stops Tin Factory to
  Hoskote).
- Pasting a key switches to live mode. The browser never talks to
  Trackingo directly: `app.js` POSTs the key to `/api/live`, and
  `web/api/live.py` (a Vercel Python serverless function) proxies the
  request to the Trackingo endpoints. That avoids CORS problems and
  keeps the key out of URLs.
- The proxy sends the key in a POST body, never stores or logs it, and
  strips anything that looks like a phone number, contact, email, or
  ticket field from journey-details responses before returning them.
- API of the proxy:
  - `GET /api/live?demo=1` returns the bundled fictional example data
  - `POST /api/live {"key": "..."}` returns live `eta_map` data
  - `POST /api/live {"key": "...", "mode": "journey"}` returns live
    journey details, scrubbed

### Deploying the website

`deploy/vercel_deploy.py` deploys `web/` to Vercel using a stored
Vercel API token (it never reads or prints the token itself). It
creates the project if missing, uploads the files, creates a
production deployment, and waits until it is READY.

```bash
python3 deploy/vercel_deploy.py verify   # proves the token works
python3 deploy/vercel_deploy.py deploy   # deploys web/ to production
```

Two things to know about Vercel defaults, both learned the hard way:

- New projects are created with Vercel Authentication (SSO login wall)
  on by default, which makes the site return 302 to a login page for
  public visitors. Disable it after creating the project:
  `PATCH /v9/projects/{project_id} {"ssoProtection": null}`.
- After deploying, verify the live URL yourself: homepage, `style.css`,
  `app.js`, and `/api/live?demo=1` must all return 200 without signing
  in.

## API endpoints used

```
GET https://bus.trackingo.in/api/live/eta_map?current_status=true&key=<KEY>
GET https://bus.trackingo.in/api/live/journey_details?key=<KEY>&zoom_position=12&platform=mobile
```

`eta_map` fields this repo uses: `current_status_details.lat_long`
(`[latitude, longitude]`), `current_status_details.details.speed`
(km/h), `current_status_details.details.timestamp` (GPS update time),
`current_status_details.details.location`, `current_status_details.details.hstate`
(`idle`, `moving`, ...), `eta_map_data` (one row per stop: scheduled,
expected, `arrival_time`, `departure_time`, status), `distance_details`.

`journey_details` returns the operator, vehicle, service, route stops,
and boarding / drop-off details. It can include booking and contact
fields, so treat its output as private.

## Tests — how to verify a change

```bash
PYTHONPATH=src python3 -c "import sys; sys.path.insert(0, 'tests'); import test_parse; test_parse.test_parse_sample(); print('ok')"
```

That is the whole test suite: the parser against the bundled example
response. No pytest, no network. Run it after touching `client.py`,
and run the CLI in `--demo` mode after touching the output formatting.

For a website change, check the live demo after deploying, or serve
`web/` locally and open it: the demo mode needs no backend except
`/api/live?demo=1`, which the static sample file covers.

## Privacy — hard rules

This repo contains **no personal data**: no tracking key, no ticket
number, no vehicle number, no phone number, no booking details, and
no real trip. The sample data in `examples/` and `web/api/` is
fictional and labelled as such.

- Never commit a real key, ticket, vehicle number, or phone number.
  Use the placeholder `YOUR_KEY` in docs and examples.
- Keep real keys out of screenshots and shared terminal output,
  especially `journey_details` output.
- Never log or store a key in the proxy (`web/api/live.py`): request
  logging is disabled there on purpose.
- Do not replace the fictional sample data with a real trip.

## Changing things

- Keep the CLI dependency-free (Python standard library only). If a
  change needs a new dependency, say so in the PR instead of adding it
  silently.
- Keep the website static plus the one proxy function. Do not add a
  backend, a database, or stored keys.
- If Trackingo changes its endpoints or response shape, update the
  field table in the README, the parser in `client.py`, the proxy in
  `web/api/live.py`, and the example data together, and say in the
  commit message what changed upstream.
- The sample trip in demo mode is fictional. If you change it, keep it
  clearly fictional and keep the stop list consistent across
  `examples/sample_eta_map.json`, `web/api/sample_eta_map.json`, and
  the README example output.
