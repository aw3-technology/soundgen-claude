# SoundGen for Claude

Make and edit music and sound with [SoundGen](https://soundgen.ai), the AI music studio, from
Claude: generate songs (sung lyrics or instrumental, up to five minutes) and sound effects, extend
a song or rewrite one section, split audio into stems, transcribe lyrics or speech, clone a voice
and speak text, and build or edit a SoundGen Studio project — tracks, MIDI clips, effects.

Everything runs through your own SoundGen account. A new account has 100 free credits, no card.
Paid actions spend your credits; Claude states the price before it runs one.

## Install

**Claude Code**

```
/plugin marketplace add aw3-technology/soundgen-claude
/plugin install soundgen@soundgen
```

Then run `/mcp`, choose **soundgen** and sign in with your SoundGen account.

**claude.ai / Claude Desktop** — Settings → Connectors → Add custom connector, URL
`https://soundgen.ai/api/mcp-server`, then Connect and sign in. For the skill, download
`soundgen-skill.zip` from https://soundgen.ai/api and upload it under Settings → Capabilities →
Skills.

Your connection appears in SoundGen under Settings → Integrations, where you can revoke it at any
time.

## What's inside

- `skills/soundgen/` — the skill: when to use SoundGen, the rules that protect your credits
  (prices, request ids, recovery), licensing, and the full API, price and tool references.
- `.mcp.json` — the SoundGen MCP server, connected by signing in. This plugin reads no API key or
  other credential from your machine.

The claude.ai download of the skill also includes `scripts/soundgen.py`, a dependency-free client
for the REST API, for places where the connector isn't available (it needs an API key from
Settings → Integrations).

## Licensing of what you make

You own audio you generate and may use it commercially, except — for audio from the default
generation model — in film, TV, radio or commercially released games, or to build sample packs for
sale. For those, generate in the app with the Stable Audio model. See https://soundgen.ai/terms §4.

## Support and policies

- Support: will.schulz@aw3.tech · https://soundgen.ai/contact
- Privacy: https://soundgen.ai/privacy · Terms: https://soundgen.ai/terms
- API and MCP docs: https://soundgen.ai/api

SoundGen is made by AW3 Technology, Inc. and is in public beta. The plugin is MIT-licensed; use of
the service is governed by SoundGen's terms.
