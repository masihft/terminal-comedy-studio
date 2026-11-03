# Changelog

All notable changes to Terminal Comedy Studio follow
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing pending. The entries below are what actually exists in this tree.

## [0.1.0]

### Added

- `comedian` console script — a terminal REPL with a pixel comedian on a small
  stage, installable with `pip install -e .`. No runtime dependencies.
- Grid-based mascot built from a shared pixel map: square body, two rectangular
  side ears, two eyes, three centred legs, pink jacket over a white shirt with a
  black tie. ASCII and no-colour fallbacks for terminals that cannot do either.
- Fifteen frame-based animations (`idle`, `blink`, `talk`, `think`, `surprise`,
  `laugh`, `punchline`, `reaction`, `proud`, `sorry`, `bounce`, `wave`, `look`,
  `walk`, `run`) driven by a time-based `Player` and an in-place repaint capped
  at 20 fps.
- AI provider abstraction with a registry keyed by provider id: OpenAI,
  Anthropic, OpenRouter, OmniRoute and any OpenAI-compatible local server. Each
  provider declares the *name* of the environment variable holding its key, so
  no key is ever stored, printed or committed.
- Offline mode — a complete provider-less show, so the product works with no
  account, no key and no network.
- Streaming replies over SSE with delta coalescing at 50 ms, plus defensive
  parsing of the structured `{text, emotion, animation, duration}` contract;
  malformed JSON falls back to the raw text instead of losing the joke.
- Six modes as prompt roles — stage, stand-up, chat, roast, story, random —
  with keyword routing from natural language, so `tell me a joke` works without
  learning a command.
- Comedy engine with Persian and English joke banks, one-liners, roast openers,
  story seeds, thinking lines and apologies, rotated rather than repeated.
- Callback engine (session topics, offered oldest-first) and an audience model
  that is mostly quiet because silence is a joke too.
- Three comedian presets with distinct personalities and languages.
- Terminal capability detection: truecolour, `NO_COLOR`, `TERM`, `isatty`,
  measured width; display-width measurement for East Asian and combining
  characters; a bidi guard so Persian lines cannot drag the stage walls to the
  wrong side.
- Command set: `/help`, `/joke`, `/standup`, `/story`, `/roast`, `/random`,
  `/mode`, `/character`, `/provider`, `/settings`, `/reset`, `/exit` — help
  text generated from the command table.
- Flags: `--version`, `--provider`, `--model`, `--character`, `--language`,
  `--mode`, `--no-color`, `--plain`, and one-shot positionals for
  `comedian tell me a joke`.
- `.env` loading from the project directory, `$XDG_CONFIG_HOME` and
  `~/.terminal-comedy-studio`, with real environment variables always winning;
  `.env.example` ships placeholders only.
- Test suite of 131 tests covering frames and geometry, animation validity,
  provider abstraction and configuration, structured-output parsing, comedy
  routing, callbacks, audience, stage rendering across four terminal profiles,
  command dispatch and the HTTP transport against a throwaway local gateway. No
  test needs a credential or the network.
- Contact sheets: `comedian-preview` renders frames to ANSI, a plain-text grid
  or an SVG sheet for checking the drawing with real eyes.
- Documentation: `README.md`, `AGENTS.md`, `CONTRIBUTING.md`, `SECURITY.md`,
  `docs/framework-comparison.md`, MIT `LICENSE`.

### Security

- Generated text is treated as data. The application never executes
  model output — no `eval`, no shell invocation, no dynamic imports, no plugin
  loader — and animation and emotion names are validated against fixed
  registries.
- Control characters and escape sequences in a reply or pasted line are stripped
  before the stage paints it.
- Only the persona, the current role, the last eight turns of the live session
  and what you just typed are sent to a configured provider. Files, environment
  variables and history are never sent, and the CLI says so on screen.

[Unreleased]: https://github.com/terminal-comedy-studio/terminal-comedy-studio/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/terminal-comedy-studio/terminal-comedy-studio/releases/tag/v0.1.0
