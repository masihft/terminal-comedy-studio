# Terminal Comedy Studio

**An AI stand-up comedian that lives inside your terminal.**

Not a chatbot with a hat on. A tiny performer: a blocky orange mascot in a pink jacket,
white shirt and black tie, standing on a stage made of text cells, telling jokes, taking
the laugh, and reacting when a bit does not land.

```text
$ comedian

TERMINAL COMEDY STUDIO
Claw'd is on stage. Type anything, or /help.
AI: none configured. The comedian performs offline material. (/connect)

╭────────────────────────────────────────────────────────────────────────╮
│                            TERMINAL COMEDY                             │
│                      ~ LIVE FROM YOUR TERMINAL ~                       │
│                                                                        │
│                   ████████████████████████████████                     │
│           ████████████████████████████████████████████████             │
│                   ████████████████████████████████                     │
│                   ████          ████          ████                     │
│                               🎤  Claw'd                               │
│ کد من کار می‌کنه. نمی‌دونم چرا. این ترسناک‌ترین قسمته.                  │
│                   ai: offline · local material only                    │
╰─────────────────────────────────────────────────────────────────────────╯
> _
```

<!-- TODO: replace this block with a real recording (assets/demo.gif) once the
     stage is captured from an actual terminal. Do not fake it. -->

## Why

Because `git commit` deserves an audience. The goal is not another AI CLI — it is the most
convincing comedian living inside a terminal: character first, comedy second, engineering
after that.

## Features

- **Pixel character on a grid** — 27×18 cells, square head/body, exactly two rectangular
  side ears, two eyes, three centred legs. Pink jacket, white shirt, black tie, all flat
  rectangles. Rendered with terminal cells, Unicode blocks and ANSI truecolor.
- **Frame-based animation** — 37 frames in 15 animations: `idle`, `blink`, `talk`, `think`,
  `surprise`, `laugh`, `punchline`, `reaction`, `proud`, `sorry`, `bounce`, `wave`, `look`,
  `walk`, `run`.
- **Works with no provider at all** — offline material in Persian and English, so the stage
  is never empty.
- **Bring your own model** — OmniRoute, OpenRouter, OpenAI, Anthropic, any local
  OpenAI-compatible server, or none. Configuration by environment variable only.
- **Modes** — stage, stand-up, chat, roast, story, random. Natural language picks the mode;
  slash commands are optional.
- **Callbacks** — the comedian remembers what you said this session and calls back to it.
- **An audience** — laughs, applause, awkward silence, the occasional boo. Mostly silence,
  because silence is funny.
- **Persian first** — `fa` is the default language, with bidi guards so RTL lines do not
  break the stage box. English works too.
- **Zero runtime dependencies** — standard library only.

## Installation

```bash
git clone https://github.com/masihft/terminal-comedy-studio
cd terminal-comedy-studio
pip install -e .
```

Then:

```bash
comedian
```

> **macOS + iCloud Drive:** if `comedian` suddenly says `No module named 'terminal_comedian'`,
> iCloud has marked the venv's `.pth` file hidden and newer Pythons skip hidden `.pth` files.
> Keep the checkout outside iCloud Drive, or run `chflags -R nohidden .venv`.

Requires Python 3.10+. macOS, Linux and Windows (Windows Terminal recommended; the renderer
falls back to plain text when the terminal cannot do colour or Unicode blocks).

## Configuration

Copy `.env.example` to `.env`, or export variables in your shell. Real environment variables
always win over the file. Nothing is required — with no configuration at all the comedian
performs offline material.

```bash
AI_PROVIDER=omniroute
OMNIROUTE_BASE_URL=http://localhost:20128/v1
OMNIROUTE_API_KEY=
OMNIROUTE_MODEL=
LANGUAGE=fa
```

| Variable | Meaning |
| --- | --- |
| `AI_PROVIDER` | `offline` (default), `omniroute`, `openrouter`, `openai`, `anthropic`, `local` |
| `AI_MODEL` | fallback model name when the provider-specific one is empty |
| `LANGUAGE` | `fa` (default) or `en` |
| `COMEDIAN_CHARACTER` | `default`, `sarkash`, `mr-blonde` |
| `COMEDIAN_TIMEOUT` / `COMEDIAN_TEMPERATURE` / `COMEDIAN_MAX_TOKENS` | request tuning |
| `NO_COLOR` | any value disables ANSI colour |

Never commit `.env`. Keys are read by the **name** of the environment variable and are never
printed. The only place this project writes a key is your own config file, and only when
`/connect` asks and you say yes (see below).

## Connecting a model from the stage

No file editing needed. On stage, type:

```text
/connect
```

and pick a provider from the menu:

- **OpenRouter** — sign in with your browser. The comedian opens openrouter.ai, you approve,
  and the browser comes back to a one-shot listener on `127.0.0.1`. This is OpenRouter's
  documented OAuth PKCE flow: no password or client secret passes through the comedian, and
  usage is billed to your own OpenRouter account. Over SSH, choose "paste a code" instead:
  open the link on any device and paste the code it shows. You can also paste a key.
- **OpenAI / Anthropic** — paste an API key. It is read without echo. Press Enter on an
  empty prompt and the comedian opens the provider's key page for you.
- **OmniRoute / Local server** — type the base URL (and a key, if your server wants one).

Next the comedian lists the provider's models. Pick one by number, type part of a name to
search, or press Enter for the default. Last, it asks whether to remember the connection in
`~/.config/terminal-comedy-studio/.env` (or `$XDG_CONFIG_HOME/terminal-comedy-studio/.env`),
which it creates readable by you only. Say no and the connection lasts for this show only.

| Command | What it does |
| --- | --- |
| `/connect [id]`, `/login` | the menu above; `/connect openrouter` jumps straight to one |
| `/model [name]` | list and pick a model for the provider on stage, or set one directly |
| `/logout` | remove the saved key for this provider and go offline |

Variables set in your shell still win over the saved file. `/connect` tells you when one does.

## Providers

| Provider | Key variable | Base URL variable | Notes |
| --- | --- | --- | --- |
| OmniRoute | `OMNIROUTE_API_KEY` | `OMNIROUTE_BASE_URL` | OpenAI-compatible gateway. Never assumed to exist; no hard-coded host or port. |
| OpenRouter | `OPENROUTER_API_KEY` | `OPENROUTER_BASE_URL` | defaults to `https://openrouter.ai/api/v1` |
| OpenAI | `OPENAI_API_KEY` | `OPENAI_BASE_URL` | defaults to `https://api.openai.com/v1`; point it at any proxy |
| Anthropic | `ANTHROPIC_API_KEY` | `ANTHROPIC_BASE_URL` | native messages API |
| Local server | `LOCAL_API_KEY` (optional) | `LOCAL_BASE_URL` | llama.cpp, vLLM, LM Studio, anything with `/v1/chat/completions` |
| offline | — | — | no network calls at all |

Switch at any time with `/connect` or `/provider <id>`, or per run with `comedian --provider openrouter`.

## Commands

Natural language is the main interface — type anything. Commands are the side door:

| Command | What it does |
| --- | --- |
| `/help` | the commands and the modes |
| `/joke` | one joke, now |
| `/standup` | a short set with structure |
| `/story` | a short comedic story |
| `/roast <thing>` | roasts a behaviour or situation, never a person |
| `/random` | the comedian chooses what to perform |
| `/mode [name]` | show or set the default mode |
| `/character [name]` | who is holding the mic |
| `/connect [id]`, `/login` | connect a model: browser sign-in or API key |
| `/model [name]` | pick the model |
| `/logout` | forget the saved key and go offline |
| `/provider [id]` | show or switch the AI provider |
| `/settings` | provider, model, language, and exactly what gets sent where |
| `/save [file]` | write this set to a markdown file (never overwrites) |
| `/reset` | forget the session |
| `/exit`, `/quit` | leave the stage |

One-shot form for scripts and pipes:

```bash
comedian joke
comedian story "my kubernetes cluster"
comedian --provider local --language en standup
comedian --plain joke
```

For looking at the character alone:

```bash
comedian-preview --list
comedian-preview idle
comedian-preview walk --strip
comedian-preview --sheet assets/character_sheet.svg --all
```

## Privacy and safety

- The comedian tells you at start-up which provider is in use. Only what you type, the last
  few turns of the session and the persona prompt are sent. Never files, never environment
  variables, never your shell history.
- Generated text is data. The comedian never runs a command the model produced, and it never
  asks you to.
- Roasting targets situations, not people: no identity, no appearance, no slurs, no
  harassment. See [SECURITY.md](SECURITY.md).

## Architecture

```text
src/terminal_comedian/
├── character/    grid geometry, 37 frames, 15 animations, emotions, personalities
├── comedy/       engine (modes + routing), offline banks, callbacks, audience
├── ai/           provider abstraction: one interface, five engines, defensive JSON parsing
├── prompts/      the persona and the six modes, as markdown with front-matter
├── memory/       session context for one show
├── ui/           renderer (ANSI/ASCII/SVG), stage layout, terminal capabilities, commands
├── cli.py        the `comedian` REPL
└── preview.py    the `comedian-preview` character inspector
```

The model returns structured intent — `{"text", "emotion", "animation", "duration"}` — and
the presentation layer decides how to perform it. A provider never knows what a joke is; the
comedy engine never knows what an HTTP request is. The renderer never knows either provider.

See [docs/framework-comparison.md](docs/framework-comparison.md) for why this is a
line-based CLI with a stdlib renderer instead of a full-screen TUI framework.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
./scripts/test.sh
./scripts/demo.sh
```

133 tests, none of which need an API key or a network. The transport tests start their own
throwaway OpenAI-compatible gateway on localhost.

## Roadmap

- **v0.1 (this)** — character, animations, stage CLI, offline comedy, five providers,
  callbacks, audience, Persian and English.
- **v0.2** — more frames and poses, better timing, more characters. (`/save` a set has landed.)
- **v0.3** — persistent memory between shows, richer callback selection.
- **v0.4** — optional Claude Code / coding-event reactions, OmniRoute improvements.
- **v0.5** — voice and lip-sync, Kitty / iTerm2 / Sixel renderers.
- **v1.0** — polished cross-platform experience, plugins, character marketplace.

## Contributing

Start with [CONTRIBUTING.md](CONTRIBUTING.md). Character-consistency rules for new frames
are in that file too — every frame must keep the same silhouette.

## Security

See [SECURITY.md](SECURITY.md) for responsible disclosure and for the rules this project
will not accept exceptions to.

## License

MIT — see [LICENSE](LICENSE).
