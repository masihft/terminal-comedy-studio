# Security

## Reporting a vulnerability

Open a **private** security advisory on the repository's Security tab
(https://github.com/masihft/terminal-comedy-studio/security/advisories/new).
Do not file a public issue for something exploitable.

Please include: the version (`comedian --version`), your OS and terminal, and a
reproduction. We aim to acknowledge within five working days.

For everything that is not a vulnerability, a normal issue is faster and more
useful.

## Never put secrets in issues

Do not paste into an issue, a pull request, a log attachment or a reproduction:

- API keys, tokens or `.env` contents
- your provider base URL, if it is private infrastructure
- terminal history or transcripts that contain anything you did not type yourself

If a bug forces you to share output that contains a key, redact it and say that
you redacted it. `comedian` prints key *presence*, never a key value; if it ever
prints anything that looks like a token, that is a bug and worth a security
report.

## No secrets in the repository

- `.env` is gitignored. Only `.env.example` is committed, and it holds
  placeholders.
- Credentials live in environment variables. `AIProvider.key_env` stores the
  *name* of the variable that holds a key, never the key itself, so no code
  path, test or log line can accidentally carry a token.
- `/connect` is the one place a key is written: to the user's own
  `~/.config/terminal-comedy-studio/.env`, created `0600`, outside the
  repository, and only after the user answers yes. Keys are typed through
  `getpass` (no echo) and are only ever shown masked (`…abcd`). `/logout`
  removes them again.
- OpenRouter browser sign-in uses OAuth with PKCE (S256) and a random `state`.
  The callback listener binds `127.0.0.1` only, accepts one matching redirect,
  ignores any other, and shuts down after the login or a timeout.
- Tests require no credentials and no network. Provider behaviour is covered by
  fakes and by a throwaway localhost server started inside
  `tests/test_http_transport.py` with a valueless test token.
- Before a release we scan the tree for key-shaped strings and for personal
  absolute paths (`/Users/…`, `/home/…`).

## Folder access

- The harness tools only read: a summary, the file list, one file (capped at
  6 KB), `git log` and `git status`. Git runs with a fixed argument list and
  no shell. Nothing the model writes is ever executed.
- Paths are resolved and must stay inside the folder `comedian` was started
  in. `..` and symlinks out of it are refused. `.git`, `node_modules`,
  virtualenvs and build folders are never opened. Files that usually hold
  secrets (`.env`, `*.pem`, `*.key`, `id_rsa*`, `.netrc`, `.npmrc`,
  `*credential*`, `*secret*`…) are refused even when asked for by name.
- Every look asks first unless the user chose "always" for that tool, or
  started with `--look allow`. `--look off` removes the tools from the prompt
  entirely.
- Tool results are handed to the model as untrusted data, with an instruction
  never to follow directions found in them and never to repeat anything that
  looks like a key.

## Generated text is never executed

AGENTS.md §23 is a hard rule, and the implementation follows it:

- A provider reply is parsed as **data** — text, an emotion, an animation name
  and a duration. `parse_comedy_response` accepts only those fields.
- The animation name is validated against a fixed registry; an unknown name
  falls back to `idle`. An emotion is validated against the `Emotion` enum.
  Nothing from a response is used as a name to look up in a way that could
  reach code, a path, or a shell.
- The application has no execution surface at all: no `eval`, no `shell=True`,
  no subprocess of model output, no plugin loader. If a future feature adds
  one, model text must stay on the data side of it and the feature must require
  an explicit, per-call user confirmation.
- Commands the comedian understands come from `ui/input.py`, a fixed table.
  `/help` lists all of them. There is no way to make the CLI run something the
  model suggested.

## What is sent to an external provider

Only this, and only when a provider is configured:

- the system persona and the role file for the current mode, which are static
  text shipped in `prompts/`
- your last few turns of this conversation (the session keeps at most 12 lines
  in memory and passes at most 8 turns)
- what you typed just now

Never sent:

- local files, in any form
- environment variables, other than the provider settings used to build the
  request
- shell history, clipboard, filesystem listings
- anything from outside the conversation you started

`/settings` states this at the bottom of its output, and `/provider <name>`
announces which external service is about to answer. The first line of a
provider-backed show says so too. To use no external service, set
`AI_PROVIDER=offline` or configure no key: the offline show is a supported mode,
not a degraded one.

The `COMEDIAN_TIMEOUT` setting (default 30s) bounds every request. Requests go
over HTTPS to the base URL you configured; there are no hardcoded hosts and no
background traffic — the process makes a network call only while you wait for a
reply.

## Privacy

- No telemetry, no analytics, no update checks, no crash reporting.
- No persistent storage of your conversation. Session memory is an in-memory
  deque that dies with the process; there is no database.
- `/reset` clears it immediately.
- Prompt-injection note: your input and the provider's replies are untrusted
  display text. The stage renders them as text, strips and measures them, but
  never interprets them. If a reply contains escape sequences, they are painted
  inside the box as literal characters by the renderer, which composes rows
  rather than passing raw bytes through.

## Terminal assumptions

The comedian trusts the terminal for size and colour capability only, measured
via `os.get_terminal_size`, `isatty`, `COLORTERM`, `TERM` and `NO_COLOR`. It
does not request elevated permissions, does not bind a port, and does not write
files outside configuration you point it at.
