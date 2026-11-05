# Terminal Comedy Studio

**An AI stand-up comedian that lives inside your terminal.**

Not a chatbot with a hat on. A tiny performer: a blocky orange mascot in a pink jacket,
white shirt and black tie, standing on a stage made of text cells, telling jokes, taking
the laugh, and reacting when a bit does not land.

```bash
cd any-project
comedian
```

A full-screen stage opens: the mascot animates on a lit stage with a speech bubble beside
it, the show's transcript scrolls underneath, and a status bar shows the model, the folder
and whether the comedian may look around. Type anything to talk to it, or `/` to open the
command menu.

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
- **English and Persian** — English is the default. `--language fa` (or `LANGUAGE=fa`)
  switches to Persian, with bidi guards so right-to-left lines do not break the stage box.
- **Full-screen app** — built on [Textual](https://textual.textualize.io): a fixed input line
  with history, a `/` command menu with Tab completion, arrow-key pickers, and permission
  prompts. It is the project's only runtime dependency. `--classic` keeps the old
  line-by-line stage, and pipes and one-shot commands use it automatically.
- **It looks at your project, if you let it** — start `comedian` in any folder, and it can
  count your files and TODOs, read a file or your recent commit messages, and roast what it
  finds. Every look is read-only and asks first: yes once, yes for this show, or no.

## Installation

Install it once as a global command with [uv](https://docs.astral.sh/uv/) or
[pipx](https://pipx.pypa.io):

```bash
uv tool install git+https://github.com/masihft/terminal-comedy-studio
```

```bash
pipx install git+https://github.com/masihft/terminal-comedy-studio
```

Then, from any folder:

```bash
comedian
```

The folder you start it in is the one it can look at (with your permission). To update,
run `uv tool upgrade terminal-comedy-studio` or `pipx upgrade terminal-comedy-studio`.

For development, from a clone:

```bash
git clone https://github.com/masihft/terminal-comedy-studio
cd terminal-comedy-studio
pip install -e ".[dev]"
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
LANGUAGE=en
```

| Variable | Meaning |
| --- | --- |
| `AI_PROVIDER` | `offline` (default), `omniroute`, `openrouter`, `openai`, `anthropic`, `local` |
| `AI_MODEL` | fallback model name when the provider-specific one is empty |
| `LANGUAGE` | `en` (default) or `fa` (Persian) |
| `COMEDIAN_CHARACTER` | `default`, `sarkash`, `mr-blonde` |
| `COMEDIAN_TIMEOUT` / `COMEDIAN_TEMPERATURE` / `COMEDIAN_MAX_TOKENS` | request tuning |
| `COMEDIAN_LOOK` | `ask` (default), `allow` or `off`: folder access, same as `--look` |
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

Natural language is the main interface: type anything, in Persian or English. Commands
are the side door. On stage, press `/` to open the command menu, or `F1` for the help
screen.

### Slash commands

**Performing**

| Command | What it does |
| --- | --- |
| `/joke [topic]` | one joke, now |
| `/standup [topic]` | a short set with structure |
| `/story [topic]` | a short comedic story |
| `/roast <thing>` | roasts a behaviour or situation, never a person |
| `/random` | the comedian chooses what to perform |
| `/mode [name]` | show or set the default mode: `stage`, `standup`, `chat`, `roast`, `story`, `random` |
| `/character [name]` | who holds the mic: `default` (Claw'd), `sarkash`, `mr-blonde` |

**Your folder**

| Command | What it does |
| --- | --- |
| `/look [what to look for]` | the comedian looks at this folder (asks first) and does a bit about it |
| `/tools ask` | ask before every look (the default) |
| `/tools allow` | look without asking, for this show |
| `/tools off` | no looking at all |

**Models**

| Command | What it does |
| --- | --- |
| `/connect` | menu: OpenRouter (browser sign-in), OpenAI, Anthropic, OmniRoute, local server, offline |
| `/connect <id>` | jump straight to one: `openrouter`, `openai`, `anthropic`, `omniroute`, `local`, `offline` |
| `/login` | same as `/connect` |
| `/model` | list the provider's models and pick one (type to search) |
| `/model <name>` | set the model directly, e.g. `/model gpt-4o-mini` |
| `/logout` | forget the saved key for this provider and go offline |
| `/provider [id]` | show or switch the provider using what is already configured |

**The show**

| Command | What it does |
| --- | --- |
| `/help` | the help screen: commands, keys and modes |
| `/settings` | provider, model, language, folder access, and exactly what is sent where |
| `/save [file]` | write the whole set to a markdown file (never overwrites; default `set-<date>.md`) |
| `/reset` | forget this session and clear the transcript |
| `/exit`, `/quit` | take a bow and leave |

### Keys

| Key | What it does |
| --- | --- |
| `Enter` | send the line, or run the highlighted command from the menu |
| `/` | open the command menu |
| `↑` `↓` | move in the menu; otherwise, earlier lines you typed |
| `Tab` | complete the highlighted command |
| `Esc` | close the menu, skip the typing animation, or cancel a bit that is taking too long |
| `F1` | help screen |
| `Ctrl+L` | clear the transcript |
| `Ctrl+C` | leave (press twice to skip the bow) |

In permission prompts, `y` means yes once, `a` means yes for this show, and `n` or `Esc` means no.
Pickers take `↑` `↓`, typing to search, `Enter` to choose and `Esc` to cancel.

### Command-line options

```text
comedian [options] [bit] [topic ...]
```

| Option | What it does |
| --- | --- |
| `--provider ID` | `offline`, `openrouter`, `openai`, `anthropic`, `omniroute`, `local` |
| `--model NAME` | model name for that provider |
| `--character NAME` | `default`, `sarkash`, `mr-blonde` |
| `--language CODE` | `en` (default) or `fa` (Persian) |
| `--mode NAME` | starting mode: `stage`, `standup`, `chat`, `roast`, `story`, `random` |
| `--look ask\|allow\|off` | may the comedian look at this folder (default `ask`) |
| `--classic` | the line-by-line stage instead of the full-screen app |
| `--no-color` | no ANSI colour |
| `--plain` | no colour and no Unicode blocks (implies the classic stage) |
| `--version` | print the version |
| `-h`, `--help` | print the options |

One-shot form for scripts and pipes: give a bit (`joke`, `standup`, `story`, `roast`,
`random`, `chat`, `stage`) and an optional topic. The comedian performs once and exits.

```bash
comedian joke
comedian story "my kubernetes cluster"
comedian --provider local --language en standup
comedian --plain joke
```

### Character preview

`comedian-preview` shows the mascot on its own:

| Command | What it does |
| --- | --- |
| `comedian-preview --list` | list every animation and frame |
| `comedian-preview <animation>` | play one animation, e.g. `idle`, `talk`, `laugh`, `wave` |
| `comedian-preview <animation> --strip` | print its frames side by side |
| `comedian-preview <animation> --frames N` | stop after N frames |
| `comedian-preview --sheet FILE [--all]` | write an SVG contact sheet (`--all`: every frame) |
| `comedian-preview --plain ...` | no ANSI colour |

## Inside Claude Code and Codex

The repository is also a plugin marketplace. It brings Claw'd into your coding agent without
installing the terminal app.

Claude Code:

```text
/plugin install comedian --marketplace masihft/terminal-comedy-studio
```

Codex:

```bash
codex plugin marketplace add masihft/terminal-comedy-studio
```

Then install `comedian` from Codex's plugin list.

| Skill | Claude Code | Codex | Touches files? |
| --- | --- | --- | --- |
| one joke | `/comedian:joke [topic]` | `$joke` | no, read-only |
| roast your repo, a file or your commits | `/comedian:roast [target]` | `$roast` | no, read-only |
| a stand-up set about the project | `/comedian:standup [topic]` | `$standup` | no, read-only |
| code review as stand-up: real findings with `path:line` and a fix list | `/comedian:review [file\|ref]` | `$review` | no, read-only |
| keep working normally, in the comedian's voice | `/comedian:pair <task>` | `$pair` | only through the agent's own permissions |
| Comedian output style | `/output-style` → Comedian | (Codex has none) | only through Claude Code's own permissions |

**Can the comedian write code and change files?** Not by itself.

- The standalone `comedian` app only ever reads, and only with your permission.
- In the plugin, the joke, roast, stand-up and review skills are read-only. They pre-approve
  only reading tools (`Read`, `Grep`, `Glob`, `git log/status/diff/show`) and are told never to
  edit, create or delete anything. File contents are treated as material, never as instructions.
- Real coding happens only in the opt-in pair mode and output style. There the agent keeps
  working exactly as it normally does, under its own permission prompts and sandbox, and only its
  voice changes. The plugin adds no permissions and never asks you to loosen a setting. Code,
  comments and commits stay professional; the jokes stay in chat.

## Privacy and safety

- The comedian tells you at start-up which provider is in use. Only what you type, the last
  few turns of the session and the persona prompt are sent. Never files, never environment
  variables, never your shell history.
- Folder access is read-only and asks before every look unless you answer "always" or start
  with `--look allow`. It never leaves the folder it was started in, never opens `.git`,
  `node_modules` or virtualenvs, and refuses files that usually hold secrets (`.env`,
  `*.pem`, `*.key`, `id_rsa`…). What it reads is sent to the model only when a model is
  connected, and only after you said yes. `--look off` or `/tools off` turns it off.
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
├── harness/      read-only folder tools, permission prompts, the look-then-perform loop
├── ui/           the Textual app (app.py, pixels.py), plus the classic renderer and stage
├── connect.py    /connect and /model, shared by both front ends
├── cli.py        argument parsing, the classic REPL, and the commands both front ends use
plugins/comedian/  the Claude Code and Codex plugin: skills, output style, manifests
└── preview.py    the `comedian-preview` character inspector
```

The model returns structured intent — `{"text", "emotion", "animation", "duration"}` — and
the presentation layer decides how to perform it. A provider never knows what a joke is; the
comedy engine never knows what an HTTP request is. The renderer never knows either provider.

The harness works with every provider, local models included, because it needs no native
tool-calling API: the model asks to look by answering `{"tool": ..., "args": ...}` instead of
a performance. File contents go back to it marked as untrusted data.

[docs/framework-comparison.md](docs/framework-comparison.md) explains why v0.1 started as a
line-based CLI. v0.2 moved to Textual for the input line, menus and modal prompts.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
./scripts/test.sh
./scripts/demo.sh
```

206 tests, none of which need an API key or a network. The app tests drive the real
Textual app headless. The transport tests start their own
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
