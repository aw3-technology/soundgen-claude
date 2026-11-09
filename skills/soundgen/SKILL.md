---
name: soundgen
description: Make and edit music and sound with SoundGen (soundgen.ai) — generate songs (with sung lyrics or instrumental, up to 5 minutes) and sound effects, extend or rewrite part of a song, split audio into stems, transcribe speech or lyrics, clone a voice and speak text, and build or edit a SoundGen Studio project (tracks, MIDI clips, effects). Use when the user asks to generate music, a beat, a jingle, a sound effect or a voiceover, to separate vocals or stems, or to work with their SoundGen account, credits or projects.
---

# SoundGen

SoundGen is an AI music studio: generation plus a real multi-track DAW. This
skill drives it for the user through their own account, so everything made
lands in their SoundGen library and every paid call spends their credits.

## Setup

The user needs a SoundGen API key: **soundgen.ai → Settings → Integrations →
API keys**. A new account has 100 free credits, no card. Prefer the key in the
environment (`SOUNDGEN_API_KEY`). Where there is no environment to set (the
claude.ai app), the user may give it in the conversation: then set it only for
the command (`SOUNDGEN_API_KEY=... python3 scripts/soundgen.py ...`), never
write it to a file or repeat it back, and tell them once that it now sits in
this chat's history and can be revoked any time in Settings → Integrations.

Two ways in — use the first that is available:

1. **SoundGen MCP tools** (`generate_audio`, `separate_stems`, `add_track`, …)
   when the SoundGen connector is connected (`https://soundgen.ai/api/mcp-server`).
   It signs in with the user's SoundGen account — no key to paste: in Claude
   Code run `/mcp` and authenticate; in claude.ai add it under Connectors. The
   connection appears in their Settings → Integrations, where they can revoke it.
   Prefer these tools when present.
2. **`scripts/soundgen.py`**, when this copy of the skill includes it (the
   claude.ai upload does; the Claude Code plugin uses the connector instead) —
   no dependencies, Python 3.8+, needs an API key in `SOUNDGEN_API_KEY`. Run
   `python3 scripts/soundgen.py --help`.

With the connector, each job below is one MCP tool: `generate_audio`,
`edit_song`, `separate_stems`, `transcribe_speech`, `synthesize_voice`,
`clone_voice`, `list_generations` / `get_generation` (recovery by request id),
`get_user_credits`, and the studio tools (`list_projects`, `get_arrangement`,
`add_track`, `add_midi_clip`, `add_clip`, `add_effect`, `apply_edits`). The
script commands below are the same calls, for when there is no connector.

If neither works (no key, or the sandbox cannot reach soundgen.ai), say so and
offer the in-app route: the user signs in at soundgen.ai and asks the AI Agent
there (**Ask AI** on their dashboard), which can do everything below and more.

## Rules that protect the user's money

1. **Say the price before spending, and get a yes** for anything over a few
   credits. Prices: `reference/pricing.md` (a 30 s song is 20 credits, 1 min 38,
   5 min 125; a sound effect 5; stems 6, or 9 for piano/guitar). Check the
   balance with `credits` when a job is large.
2. **Charged only on success.** A failure, safety rejection or 402 costs nothing.
3. **One request id per job, and reuse it to recover — never to start again.**
   `generate`, `stems`, `edit_song`, `transcribe`, `clone`, `synthesize` all take
   a `request_id` (a UUID). If the connection drops or times out, do NOT send a
   fresh request: run `recover --request-id <same id>`. Pending means it is
   still running; 404 means it never arrived, so re-sending with the *same* id
   is safe. A new id is a second, separately charged job.
4. **Don't loop on failures.** `SAFETY_REJECTION` usually means an artist, band
   or song name in the prompt — describe the sound instead (genre, instruments,
   tempo, mood, era) and try once more.

## Licensing — tell the user when it matters

Audio generated through this API uses the ElevenLabs music model. The user owns
it and may use it commercially (release, stream, monetize, YouTube) **except**
(a) in film, TV, radio or commercially released video games, and (b) to build
sample packs or sound libraries for sale. For those, they should generate in the
app with **Model → Stable Audio** on soundgen.ai/generate (instrumental only, no
media restriction; not available through the API). Terms: soundgen.ai/terms §4.
Don't give legal advice beyond this.

## Common jobs

**A song or instrumental**
```
python3 scripts/soundgen.py generate --prompt "warm lo-fi hip hop, dusty drums, Rhodes, vinyl crackle" --duration 90 --bpm 85 --key "A minor" --instrumental
python3 scripts/soundgen.py generate --prompt "anthemic pop-punk, fast drums, big chorus" --duration 120 --lyrics "$(cat lyrics.txt)"
```
`--prompt` is the sound, never the lyrics. Lyrics go in `--lyrics` (the model
sings them exactly; `[Verse]`/`[Chorus]` tags help). Music is 3–300 s. It runs
to completion (1–3 minutes) and returns `audio_url`, `generation_id`,
`credits_charged`. `download <audio_url> song.mp3` saves it.

**A sound effect** — `generate --kind sound-effects --prompt "heavy wooden door creaks open" --duration 4` (0.5–22 s, 5 credits).

**Longer, or fix one part** — `tool edit_song --paid --args '{"generation_id": "...", "mode": "extend", "extend_seconds": 30}'`, or `"mode": "replace"` with `start_seconds`/`end_seconds` to rewrite a 3–120 s section while the rest stays note-for-note. Priced on the song's length plus the result's.

**Stems** — `stems --audio-url <url> [--stems vocals,drums,bass,other]`. Adding `piano` or `guitar` runs the deep model (9 credits). The audio must be at a public or SoundGen URL.

**Lyrics or speech to text** — `transcribe --audio-url <url>` (about 2 credits a minute, timed lines).

**Voice** — `call GET /voices` lists voices; `call POST /synthesize --json '{"text": "...", "voice_id": "..."}'` speaks text (6 credits); `call POST /clone --json '{"name": "...", "audio_urls": ["..."]}'` clones a voice from audio already in SoundGen (30).

**A Studio project** — `tools` lists every studio tool with its input schema;
`tool <name> --args '<json>'` runs one (add `--paid` for a tool that charges) (e.g. `list_projects`, `get_arrangement`,
`add_track`, `add_midi_clip` in bars, `add_clip` for audio, `add_effect`).
For several changes use `edits <project_id> --steps '<json>'`: one atomic save,
`--dry-run` first. A 409 means the project changed since it was read — read it
again, never overwrite. The user opens the result at soundgen.ai/studio.

**History and balance** — `generations`, `generations --request-id <id>`, `credits`.

Full endpoint list with parameters: `reference/api.md`. Tool groups:
`reference/tools.md`.

## Errors

| Code | Meaning | Do |
|---|---|---|
| 401 UNAUTHORIZED | Missing or bad key | Ask the user to check `SOUNDGEN_API_KEY` |
| 402 INSUFFICIENT_CREDITS | Balance below price; nothing charged | Tell them; packs are one-time at soundgen.ai/pricing |
| 400 SAFETY_REJECTION | Prompt blocked; nothing charged | Remove names, describe the sound |
| 409 REQUEST_ALREADY_FAILED | That request id already failed | Start again with a new id |
| 409 (projects) | Project changed meanwhile | Re-read, re-apply |
| 410 ACTION_REMOVED | Retired `ai-process` action | Use the replacement it names |
| 502 GENERATION_FAILED | Provider failed; nothing charged | Retry once with a new id |
| 503 BALANCE_UNCONFIRMED | Balance unreadable; nothing charged | Try again shortly |

Support: will.schulz@aw3.tech. SoundGen is in public beta.
