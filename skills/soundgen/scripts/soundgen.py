#!/usr/bin/env python3
"""SoundGen from the command line — the SoundGen REST API, standard library only.

  export SOUNDGEN_API_KEY=...   # soundgen.ai -> Settings -> Integrations
  python3 soundgen.py credits
  python3 soundgen.py generate --prompt "lo-fi hip hop, Rhodes, vinyl" --duration 60 --instrumental
  python3 soundgen.py recover --request-id <uuid>

Every paid command makes its request id BEFORE sending and prints it to stderr
first, so a dropped connection is recovered with `recover` (same id) instead of
being sent again — a second id is a second charge.

Output is the API's `data` object as JSON on stdout. On an error it prints
{"error": {...}, "status": N} and exits 1.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

API = os.environ.get("SOUNDGEN_API_URL", "https://soundgen.ai/api/api-v1").rstrip("/")
# A generation runs to completion before the reply (one to three minutes; a
# long song or stems can take longer). Generous, so a slow job isn't abandoned.
LONG = 900
SHORT = 60


def key():
    k = os.environ.get("SOUNDGEN_API_KEY", "").strip()
    if not k:
        fail(0, {"code": "NO_API_KEY", "message": "Set SOUNDGEN_API_KEY (soundgen.ai -> Settings -> Integrations -> API keys)."})
    return k


def fail(status, error):
    print(json.dumps({"status": status, "error": error}, indent=2))
    sys.exit(1)


def request(method, path, body=None, timeout=SHORT, idempotency_key=None):
    headers = {"Authorization": "Bearer " + key(), "Accept": "application/json", "User-Agent": "soundgen-claude-skill/1"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    req = urllib.request.Request(API + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            payload = json.loads(res.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode() or "{}")
        except ValueError:
            payload = {}
        err = payload.get("error") if isinstance(payload, dict) else None
        if not isinstance(err, dict):
            err = {"code": "HTTP_%d" % e.code, "message": str(err or e.reason)}
        fail(e.code, err)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        # No answer: the job may still be running. Say how to find it.
        hint = {"code": "NO_RESPONSE", "message": "No answer from SoundGen (%s)." % getattr(e, "reason", e)}
        if idempotency_key:
            hint["request_id"] = idempotency_key
            hint["next"] = "Do not send a new request. Run: recover --request-id %s" % idempotency_key
        fail(0, hint)
    if isinstance(payload, dict) and payload.get("success") is False:
        fail(200, payload.get("error") or payload)
    return payload.get("data", payload) if isinstance(payload, dict) else payload


def out(value):
    print(json.dumps(value, indent=2))


def announce(rid):
    print("request_id: %s  (if this is interrupted: recover --request-id %s)" % (rid, rid), file=sys.stderr)


def cmd_generate(a):
    rid = a.request_id or str(uuid.uuid4())
    body = {"prompt": a.prompt, "kind": a.kind, "request_id": rid}
    for name in ("duration", "bpm", "key", "genre", "mood", "lyrics", "title"):
        v = getattr(a, name)
        if v is not None:
            body[name] = v
    if a.instrumental:
        body["instrumental"] = True
    announce(rid)
    out(request("POST", "/generate", body, timeout=LONG, idempotency_key=rid))


def cmd_recover(a):
    out(request("GET", "/generations?request_id=" + urllib.request.quote(a.request_id)))


def cmd_generations(a):
    q = "?limit=%d" % a.limit
    if a.status:
        q += "&status=" + a.status
    if a.request_id:
        q = "?request_id=" + urllib.request.quote(a.request_id)
    out(request("GET", "/generations" + q))


def cmd_stems(a):
    rid = a.request_id or str(uuid.uuid4())
    body = {"audio_url": a.audio_url, "request_id": rid, "quality": a.quality}
    if a.stems:
        body["stems"] = [s.strip() for s in a.stems.split(",") if s.strip()]
    announce(rid)
    out(request("POST", "/stems", body, timeout=LONG, idempotency_key=rid))


def cmd_transcribe(a):
    rid = a.request_id or str(uuid.uuid4())
    body = {"audio_url": a.audio_url, "request_id": rid, "diarize": a.diarize}
    if a.language:
        body["language_code"] = a.language
    announce(rid)
    out(request("POST", "/tools/transcribe_speech", body, timeout=LONG, idempotency_key=rid))


def cmd_credits(_a):
    out(request("GET", "/credits"))


def cmd_tools(a):
    out(request("GET", "/tools" + ("/" + a.name if a.name else "")))


def parse_json(text, what):
    try:
        return json.loads(text)
    except ValueError as e:
        fail(0, {"code": "BAD_JSON", "message": "%s is not valid JSON: %s" % (what, e)})


def cmd_tool(a):
    args = parse_json(a.args, "--args") if a.args else {}
    # Paid tools (edit_song, transcribe_speech, separate_stems, …) take a
    # request_id; give them one so a retry can't charge twice.
    rid = args.get("request_id") if isinstance(args, dict) else None
    if isinstance(args, dict) and a.paid and not rid:
        rid = args["request_id"] = str(uuid.uuid4())
    if rid:
        announce(rid)
    out(request("POST", "/tools/" + a.name, args, timeout=LONG, idempotency_key=rid))


def cmd_edits(a):
    body = {"steps": parse_json(a.steps, "--steps"), "dry_run": a.dry_run}
    if a.expected_version is not None:
        body["expected_version"] = a.expected_version
    out(request("POST", "/projects/%s/edits" % a.project_id, body, timeout=LONG))


def cmd_call(a):
    body = parse_json(a.json, "--json") if a.json else None
    method = a.method.upper()
    # /synthesize and /clone charge; an Idempotency-Key makes a retry return the
    # first result instead of charging again. Harmless on other POSTs.
    rid = (a.request_id or str(uuid.uuid4())) if method == "POST" else None
    if rid:
        announce(rid)
    out(request(method, a.path if a.path.startswith("/") else "/" + a.path, body, timeout=LONG, idempotency_key=rid))


def cmd_download(a):
    # Signed links need no key; sending it to a storage host would leak it.
    try:
        with urllib.request.urlopen(urllib.request.Request(a.url, headers={"User-Agent": "soundgen-claude-skill/1"}), timeout=LONG) as res, open(a.path, "wb") as f:
            size = 0
            while True:
                chunk = res.read(1 << 16)
                if not chunk:
                    break
                f.write(chunk)
                size += len(chunk)
    except (urllib.error.URLError, OSError) as e:
        fail(0, {"code": "DOWNLOAD_FAILED", "message": str(e)})
    out({"saved": a.path, "bytes": size})


def main():
    p = argparse.ArgumentParser(description="SoundGen API (soundgen.ai). Key: SOUNDGEN_API_KEY.")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="Generate music or a sound effect (paid; runs to completion)")
    g.add_argument("--prompt", required=True, help="The sound: style, genre, mood, instruments. Not the lyrics")
    g.add_argument("--kind", default="music", choices=["music", "sound-effects"])
    g.add_argument("--duration", type=float, help="Seconds: music 3-300 (default 30), sound effects 0.5-22 (default 5)")
    g.add_argument("--bpm", type=float)
    g.add_argument("--key", help='e.g. "A minor"')
    g.add_argument("--genre")
    g.add_argument("--mood")
    g.add_argument("--lyrics", help="Exact words to sing")
    g.add_argument("--instrumental", action="store_true", help="No vocals")
    g.add_argument("--title")
    g.add_argument("--request-id", help="Reuse only to recover the same job")
    g.set_defaults(fn=cmd_generate)

    r = sub.add_parser("recover", help="Find a job by its request id (after a dropped connection)")
    r.add_argument("--request-id", required=True)
    r.set_defaults(fn=cmd_recover)

    h = sub.add_parser("generations", help="Generation history, newest first")
    h.add_argument("--limit", type=int, default=20)
    h.add_argument("--status", choices=["pending", "completed", "failed"])
    h.add_argument("--request-id")
    h.set_defaults(fn=cmd_generations)

    s = sub.add_parser("stems", help="Separate audio into stems (paid: 6, or 9 with piano/guitar)")
    s.add_argument("--audio-url", required=True)
    s.add_argument("--stems", help="Comma list: vocals,drums,bass,other,piano,guitar")
    s.add_argument("--quality", default="standard", choices=["fast", "standard", "high"])
    s.add_argument("--request-id")
    s.set_defaults(fn=cmd_stems)

    t = sub.add_parser("transcribe", help="Speech or sung lyrics to timed text (paid, ~2 credits/min)")
    t.add_argument("--audio-url", required=True)
    t.add_argument("--language", help="ISO code; omit to auto-detect")
    t.add_argument("--diarize", action="store_true")
    t.add_argument("--request-id")
    t.set_defaults(fn=cmd_transcribe)

    sub.add_parser("credits", help="Credit balance").set_defaults(fn=cmd_credits)

    ts = sub.add_parser("tools", help="List studio/MCP tools with input schemas, or one by name")
    ts.add_argument("name", nargs="?")
    ts.set_defaults(fn=cmd_tools)

    tl = sub.add_parser("tool", help="Run one studio tool: tool <name> --args '<json>'")
    tl.add_argument("name")
    tl.add_argument("--args", help="JSON object of the tool's arguments")
    tl.add_argument("--paid", action="store_true", help="Add a request_id so a retry cannot charge twice")
    tl.set_defaults(fn=cmd_tool)

    e = sub.add_parser("edits", help="Several project edits as one atomic save")
    e.add_argument("project_id")
    e.add_argument("--steps", required=True, help='JSON: [{"tool": "...", "args": {...}}, ...]')
    e.add_argument("--expected-version", type=int)
    e.add_argument("--dry-run", action="store_true")
    e.set_defaults(fn=cmd_edits)

    c = sub.add_parser("call", help="Any endpoint: call GET /voices, call POST /synthesize --json '{...}'")
    c.add_argument("method")
    c.add_argument("path")
    c.add_argument("--json")
    c.add_argument("--request-id", help="Reuse only to retry the same POST")
    c.set_defaults(fn=cmd_call)

    d = sub.add_parser("download", help="Save an audio_url to a file")
    d.add_argument("url")
    d.add_argument("path")
    d.set_defaults(fn=cmd_download)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
