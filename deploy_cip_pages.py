#!/usr/bin/env python3
"""Publish compoundintelligencepartners.com to Cloudflare Pages, and move its DNS from GoDaddy to Cloudflare.

Modeled on PLA Claude/website/deploy_pla_pages.py and MML Corpus/anthology_website/publish.py.
Differences from the PLA script, on purpose:
  - publishes an ALLOWLIST only (the PLA script publishes every .html in its folder, which leaked drafts)
  - 404.html is a real not-found page, not a copy of the home page
  - GoDaddy's own DNS records are never edited; only the nameservers move, so rollback is one call

Usage:
  python3 deploy_cip_pages.py --build            # assemble the publish folder only
  python3 deploy_cip_pages.py --serve 8020       # build, then serve it locally for a check
  python3 deploy_cip_pages.py --deploy           # build + upload to Pages project 'compoundintelligencepartners'
  python3 deploy_cip_pages.py --migrate-dns      # create the Cloudflare zone, copy TXT records, CNAME apex+www
                                                 # to Pages, attach domains, switch GoDaddy nameservers
  python3 deploy_cip_pages.py --restore-godaddy  # put the GoDaddy nameservers back (GitHub Pages serves again)
  python3 deploy_cip_pages.py --status
  add --dry-run to any mutating step to preview it.

Tokens: ~/.config/cloudflare/api_token.txt (DNS), pages_token.txt (Pages), ~/.config/godaddy/godaddy.env.
Values are passed only to child processes and scrubbed from printed output.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse

SITE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLISH_DIR = "/Users/mark/A/data/sites/compoundintelligencepartners-com/publish"
BACKUP_DIR = "/Users/mark/A/state/sites/compoundintelligencepartners-com"
API = "https://api.cloudflare.com/client/v4"
GD_API = "https://api.godaddy.com"
ZONE_NAME = "compoundintelligencepartners.com"
PROJECT_NAME = "compoundintelligencepartners"
PAGES_TARGET = f"{PROJECT_NAME}.pages.dev"
GODADDY_NS = ["ns65.domaincontrol.com", "ns66.domaincontrol.com"]
DRY = "--dry-run" in sys.argv

# Published path -> source path (relative to SITE_DIR). Nothing else is published.
ALLOW = {
    "index.html": "index.html",
    "404.html": "404.html",
    "robots.txt": "robots.txt",
    "favicon.png": "favicon.png",
    "favicon64.png": "favicon64.png",
    "mark-michael-lewis.jpg": "mark-michael-lewis.jpg",
    "compound-intelligence-framework-white-paper.pdf": "The Compound Intelligence Framework — White Paper 1.pdf",
    "turn-ai-tools-into-profitable-workflows.pdf": "Turn AI Tools Into Profitable Workflows.pdf",
}
# Directory published as-is (another lane's work; published unchanged, minus dotfiles).
ALLOW_DIRS = ["rise-of-ai"]
REFUSE_EXT = {".py", ".md", ".toml", ".json", ".js", ".docx_lock"}
MAX_FILE = 25 * 1024 * 1024  # Pages per-file cap

HEADERS = """/
  Content-Security-Policy: default-src 'self'; script-src 'self' https://static.cloudflareinsights.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self' https://cloudflareinsights.com; frame-ancestors 'none'; base-uri 'self'; form-action 'none'
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
/index.html
  Content-Security-Policy: default-src 'self'; script-src 'self' https://static.cloudflareinsights.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self' https://cloudflareinsights.com; frame-ancestors 'none'; base-uri 'self'; form-action 'none'
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
/rise-of-ai/*
  X-Robots-Tag: noindex
  X-Content-Type-Options: nosniff
"""

# Old URLs (GitHub Pages era) -> new ones.
REDIRECTS = [
    ("/The%20Compound%20Intelligence%20Framework%20%E2%80%94%20White%20Paper%201.pdf", "/compound-intelligence-framework-white-paper.pdf"),
    ("/Turn%20AI%20Tools%20Into%20Profitable%20Workflows.pdf", "/turn-ai-tools-into-profitable-workflows.pdf"),
    ("/rise-of-ai", "/rise-of-ai/"),
]


def step(msg):
    print(("[dry-run] would " if DRY else "[cip] ") + msg, flush=True)


def secret(path):
    p = os.path.expanduser(path)
    if not os.path.exists(p):
        raise SystemExit(f"Missing token file: {p}")
    return open(p).read().strip()


def godaddy_creds():
    env = {}
    for line in open(os.path.expanduser("~/.config/godaddy/godaddy.env")):
        line = line.strip()
        if line.startswith("export "):
            line = line[len("export "):]
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env["GODADDY_KEY"], env["GODADDY_SECRET"]


def curl_json(method, url, headers, body=None):
    cfg = "".join(f'header = "{h}"\n' for h in headers) + f'request = "{method}"\n'
    tmp = None
    if body is not None:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(body, tmp)
        tmp.close()
        cfg += f'data = "@{tmp.name}"\n'
    try:
        r = subprocess.run(["curl", "-s", "-w", "\n%{http_code}", "--config", "-", url],
                           input=cfg, capture_output=True, text=True, timeout=60)
    finally:
        if tmp:
            os.unlink(tmp.name)
    body_txt, _, code = r.stdout.rpartition("\n")
    try:
        data = json.loads(body_txt) if body_txt.strip() else None
    except json.JSONDecodeError:
        data = body_txt
    return int(code or 0), data


def cf(method, path, token, body=None):
    code, out = curl_json(method, API + path,
                          [f"Authorization: Bearer {token}", "Content-Type: application/json"], body)
    if not isinstance(out, dict) or not out.get("success"):
        raise SystemExit(f"Cloudflare API error [{method} {path}] HTTP {code}: "
                         f"{out.get('errors') if isinstance(out, dict) else out}")
    return out["result"]


def gd(method, path, body=None):
    k, s = godaddy_creds()
    code, out = curl_json(method, GD_API + path,
                          [f"Authorization: sso-key {k}:{s}", "Content-Type: application/json", "Accept: application/json"], body)
    if code >= 300:
        raise SystemExit(f"GoDaddy API error [{method} {path}] HTTP {code}: {out}")
    return out


# ---------------------------------------------------------------- build

def build():
    if os.path.isdir(PUBLISH_DIR):
        shutil.rmtree(PUBLISH_DIR)
    os.makedirs(PUBLISH_DIR)
    for dst, src in ALLOW.items():
        s = os.path.join(SITE_DIR, src)
        if not os.path.isfile(s):
            raise SystemExit(f"Allowlisted file missing: {s}")
        shutil.copy2(s, os.path.join(PUBLISH_DIR, dst))
    for d in ALLOW_DIRS:
        shutil.copytree(os.path.join(SITE_DIR, d), os.path.join(PUBLISH_DIR, d),
                        ignore=shutil.ignore_patterns(".*"))
    with open(os.path.join(PUBLISH_DIR, "_headers"), "w") as f:
        f.write(HEADERS)
    with open(os.path.join(PUBLISH_DIR, "_redirects"), "w") as f:
        f.write("".join(f"{a} {b} 301\n" for a, b in REDIRECTS))
    # Refusals: nothing private, nothing oversized.
    n = 0
    for root, _, files in os.walk(PUBLISH_DIR):
        for fn in files:
            p = os.path.join(root, fn)
            n += 1
            ext = os.path.splitext(fn)[1].lower()
            if fn.startswith(".") or ext in REFUSE_EXT:
                raise SystemExit(f"Refusing to publish {p}")
            if os.path.getsize(p) > MAX_FILE:
                raise SystemExit(f"Over the Pages per-file cap: {p}")
    print(f"[build] {n} files -> {PUBLISH_DIR}")


def serve(port):
    build()
    print(f"[serve] http://127.0.0.1:{port}/  (Ctrl-C to stop; _headers and _redirects are not applied locally)")
    subprocess.run([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"], cwd=PUBLISH_DIR)


# ---------------------------------------------------------------- deploy

def account_id(dns_token):
    # The DNS token is zone-scoped; any zone it can see names the account. Use PLA's, which is known to exist.
    zones = cf("GET", "/zones?name=profitabilityleadership.com", dns_token)
    if not zones:
        raise SystemExit("Could not resolve the Cloudflare account id.")
    return zones[0]["account"]["id"]


def ensure_project(acct, pages_token):
    try:
        cf("GET", f"/accounts/{acct}/pages/projects/{PROJECT_NAME}", pages_token)
        print(f"[pages] project '{PROJECT_NAME}' exists")
    except SystemExit:
        step(f"create Pages project '{PROJECT_NAME}' (production branch main)")
        if not DRY:
            cf("POST", f"/accounts/{acct}/pages/projects", pages_token,
               {"name": PROJECT_NAME, "production_branch": "main"})


def deploy():
    dns_token, pages_token = secret("~/.config/cloudflare/api_token.txt"), secret("~/.config/cloudflare/pages_token.txt")
    build()
    acct = account_id(dns_token)
    ensure_project(acct, pages_token)
    step(f"upload {PUBLISH_DIR} -> Pages '{PROJECT_NAME}' (branch main)")
    if DRY:
        return
    env = {**os.environ, "CLOUDFLARE_API_TOKEN": pages_token, "CLOUDFLARE_ACCOUNT_ID": acct,
           "WRANGLER_SEND_METRICS": "false"}
    r = subprocess.run(["npx", "--yes", "wrangler", "pages", "deploy", PUBLISH_DIR,
                        "--project-name", PROJECT_NAME, "--branch", "main", "--commit-dirty=true"],
                       cwd=os.path.dirname(PUBLISH_DIR), env=env, capture_output=True, text=True, timeout=900)
    out = (r.stdout + r.stderr).replace(pages_token, "[redacted]").replace(dns_token, "[redacted]")
    print("\n".join(out.strip().splitlines()[-8:]))
    urls = re.findall(r"https://[\w.-]+\.pages\.dev", out)
    if r.returncode != 0 or not urls:
        raise SystemExit(f"Deploy failed (exit {r.returncode})")
    print(f"[deploy] DEPLOYED: {urls[-1]}  (production: https://{PAGES_TARGET})")


# ---------------------------------------------------------------- DNS migration

def migrate_dns():
    dns_token, pages_token = secret("~/.config/cloudflare/api_token.txt"), secret("~/.config/cloudflare/pages_token.txt")
    acct = account_id(dns_token)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")

    # 1. Back up GoDaddy state (records + nameservers). This is the rollback record.
    records = gd("GET", f"/v1/domains/{ZONE_NAME}/records")
    domain = gd("GET", f"/v1/domains/{ZONE_NAME}")
    bk = os.path.join(BACKUP_DIR, f"godaddy-backup-{'dryrun' if DRY else 'live'}-{ts}.json")
    with open(bk, "w") as f:
        json.dump({"records": records, "nameServers": domain.get("nameServers")}, f, indent=2)
    print(f"[backup] {len(records)} GoDaddy records + nameservers -> {bk}")

    # 2. Cloudflare zone (create if absent).
    zones = cf("GET", f"/zones?name={ZONE_NAME}", dns_token)
    if zones:
        zone = zones[0]
        print(f"[zone] exists: {zone['id']} status={zone['status']}")
    else:
        step(f"create Cloudflare zone {ZONE_NAME} (full setup, free plan)")
        if DRY:
            zone = {"id": "<new>", "name_servers": ["<assigned>", "<assigned>"]}
        else:
            zone = cf("POST", "/zones", dns_token, {"name": ZONE_NAME, "account": {"id": acct}, "type": "full"})
    zid = zone["id"]

    # 3. Records in the new zone: carry over every TXT (SPF, Zoho verification, DMARC); point apex + www at Pages.
    existing = [] if DRY and zid == "<new>" else cf("GET", f"/zones/{zid}/dns_records?per_page=100", dns_token)
    have = {(r["type"], r["name"], r["content"]) for r in existing}
    wanted = []
    for r in records:
        if r["type"] == "TXT":
            name = ZONE_NAME if r["name"] == "@" else f"{r['name']}.{ZONE_NAME}"
            wanted.append({"type": "TXT", "name": name, "content": r["data"], "ttl": 1})
        elif r["type"] == "MX":
            name = ZONE_NAME if r["name"] == "@" else f"{r['name']}.{ZONE_NAME}"
            wanted.append({"type": "MX", "name": name, "content": r["data"], "priority": r.get("priority", 10), "ttl": 1})
    for host in (ZONE_NAME, f"www.{ZONE_NAME}"):
        wanted.append({"type": "CNAME", "name": host, "content": PAGES_TARGET, "proxied": True, "ttl": 1})
    for rec in wanted:
        key = (rec["type"], rec["name"], rec["content"])
        if key in have:
            print(f"[dns] present: {rec['type']} {rec['name']}")
            continue
        step(f"add {rec['type']} {rec['name']} -> {rec['content'][:60]}")
        if not DRY:
            cf("POST", f"/zones/{zid}/dns_records", dns_token, rec)

    # 4. Attach both hostnames to the Pages project.
    try:
        attached = {d["name"] for d in cf("GET", f"/accounts/{acct}/pages/projects/{PROJECT_NAME}/domains", pages_token)}
    except SystemExit:
        attached = set()
    for host in (ZONE_NAME, f"www.{ZONE_NAME}"):
        if host in attached:
            print(f"[domains] attached: {host}")
        else:
            step(f"attach {host} to Pages project")
            if not DRY:
                cf("POST", f"/accounts/{acct}/pages/projects/{PROJECT_NAME}/domains", pages_token, {"name": host})

    # 5. Switch the registrar nameservers at GoDaddy.
    ns = zone.get("name_servers") or []
    step(f"set GoDaddy nameservers -> {ns}")
    if not DRY:
        if not ns or len(ns) < 2:
            raise SystemExit(f"Zone has no assigned nameservers yet: {ns}")
        gd("PATCH", f"/v1/domains/{ZONE_NAME}", {"nameServers": ns})
    print("[migrate] done. Propagation: check `dig +short NS compoundintelligencepartners.com @8.8.8.8`.")


def restore_godaddy():
    step(f"set GoDaddy nameservers back -> {GODADDY_NS} (GoDaddy records were never changed; GitHub Pages serves again)")
    if not DRY:
        gd("PATCH", f"/v1/domains/{ZONE_NAME}", {"nameServers": GODADDY_NS})


def status():
    print(subprocess.run(["dig", "+short", "NS", ZONE_NAME, "@8.8.8.8"], capture_output=True, text=True).stdout.strip())
    for u in (f"https://{PAGES_TARGET}/", f"https://www.{ZONE_NAME}/", f"https://{ZONE_NAME}/"):
        r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code} %{remote_ip}", "-L", u],
                           capture_output=True, text=True)
        print(f"{u}  {r.stdout}")


if __name__ == "__main__":
    a = sys.argv
    if "--serve" in a:
        serve(int(a[a.index("--serve") + 1]) if len(a) > a.index("--serve") + 1 else 8020)
    elif "--build" in a:
        build()
    elif "--deploy" in a:
        deploy()
    elif "--migrate-dns" in a:
        migrate_dns()
    elif "--restore-godaddy" in a:
        restore_godaddy()
    elif "--status" in a:
        status()
    else:
        print(__doc__)
