#!/usr/bin/env python3
"""Deploy the Trackingo web site to Vercel with the stored API token.

Uses the dynamic-credential surrogate exchange (see the custom.vercel
connector). The real token is never read, printed, or stored here.

Prerequisite: the custom.vercel credential must be stored first. The
user creates a token at vercel.com/account/tokens and enters it on the
secure connector page. The token needs permission to create projects
and deployments on the team below.

Usage:
  vercel_deploy.py verify          # GET /v2/user, proves the token works
  vercel_deploy.py create-project  # POST /v9/projects (no-op if it exists)
  vercel_deploy.py deploy          # upload web/ files, create a production
                                   # deployment, wait until it is READY
  vercel_deploy.py status <id>     # GET /v13/deployments/<id>
"""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
from dynamic_credentials import add_surrogate_to_request

BASE = "https://api.vercel.com"
ALLOWED = ["api.vercel.com"]
TEAM_ID = "team_4VbExRyZJxULA2MArFkcp2ZV"
PROJECT = "trackingo-bus-tracker"
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise RuntimeError("redirect refused, verify the endpoint")


def call(method, path, payload=None, raw=None, extra_headers=None):
    url = BASE + path
    data = None
    headers = {
        "Accept": "application/json",
        "User-Agent": "muse-vercel-deploy",
    }
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    if raw is not None:
        data = raw
    if extra_headers:
        headers.update(extra_headers)
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    add_surrogate_to_request(request, "custom.vercel", allowed_hosts=ALLOWED)
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=180) as resp:
            body = resp.read()
            return resp.status, json.loads(body.decode()) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, {"_error_body": body[:2000]}


def upload_file(local_path):
    with open(local_path, "rb") as handle:
        data = handle.read()
    sha = hashlib.sha1(data).hexdigest()
    status, out = call(
        "POST",
        f"/v2/files?teamId={TEAM_ID}",
        raw=data,
        extra_headers={
            "Content-Type": "application/octet-stream",
            "x-now-digest": sha,
            "x-now-size": str(len(data)),
            "Content-Length": str(len(data)),
        },
    )
    if status not in (200, 201):
        raise RuntimeError(f"upload {local_path} failed: HTTP {status} {json.dumps(out)[:500]}")
    if isinstance(out, list):
        out = out[0] if out else {}
    return out.get("sha", sha), len(data)


def ensure_project():
    status, proj = call("GET", f"/v9/projects/{PROJECT}?teamId={TEAM_ID}")
    if status == 200:
        print(f"project exists: {proj.get('id')} ({proj.get('name')})")
        return proj
    if status != 404:
        raise RuntimeError(f"project check failed: HTTP {status} {json.dumps(proj)[:500]}")
    status, proj = call(
        "POST",
        f"/v9/projects?teamId={TEAM_ID}",
        {"name": PROJECT, "framework": None},
    )
    print(f"create project: HTTP {status}")
    if status not in (200, 201):
        raise RuntimeError(f"create project failed: {json.dumps(proj)[:1000]}")
    print(f"created project: {proj.get('id')} ({proj.get('name')})")
    return proj


def deploy():
    ensure_project()
    files = []
    for root, dirs, names in os.walk(WEB_DIR):
        dirs[:] = [d for d in dirs if d not in ("__pycache__",)]
        for name in sorted(names):
            full = os.path.join(root, name)
            rel = os.path.relpath(full, WEB_DIR).replace(os.sep, "/")
            sha, size = upload_file(full)
            files.append({"file": rel, "sha": sha, "size": size})
            print(f"uploaded {rel} ({size} bytes, sha {sha[:7]})")
    status, dep = call(
        "POST",
        f"/v13/deployments?teamId={TEAM_ID}",
        {
            "name": PROJECT,
            "files": files,
            "projectSettings": {"framework": None},
            "target": "production",
            "version": 2,
        },
    )
    print(f"create deployment: HTTP {status}")
    if status not in (200, 201):
        raise RuntimeError(f"create deployment failed: {json.dumps(dep)[:2000]}")
    dep_id = dep.get("id")
    print(f"deployment id: {dep_id}  url: https://{dep.get('url')}")
    for _ in range(30):
        time.sleep(10)
        status, cur = call("GET", f"/v13/deployments/{dep_id}?teamId={TEAM_ID}")
        state = cur.get("readyState")
        print(f"state: {state}")
        if state == "READY":
            print(f"LIVE: https://{cur.get('url')}")
            return
        if state in ("ERROR", "CANCELED"):
            raise RuntimeError(f"deployment {state}: {json.dumps(cur)[:2000]}")
    raise RuntimeError("deployment did not become READY in 5 minutes")


def main():
    if len(sys.argv) < 2:
        print("usage: vercel_deploy.py verify|create-project|deploy|status <id>")
        return 2
    cmd = sys.argv[1]
    if cmd == "verify":
        status, out = call("GET", "/v2/user")
        print(f"HTTP {status}")
        print(json.dumps(out, indent=2)[:800])
        return 0 if status == 200 else 1
    if cmd == "create-project":
        ensure_project()
        return 0
    if cmd == "deploy":
        deploy()
        return 0
    if cmd == "status":
        if len(sys.argv) < 3:
            print("usage: vercel_deploy.py status <deployment-id>")
            return 2
        status, out = call("GET", f"/v13/deployments/{sys.argv[2]}?teamId={TEAM_ID}")
        print(f"HTTP {status} readyState={out.get('readyState')} url=https://{out.get('url')}")
        return 0
    print(f"unknown command: {cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
