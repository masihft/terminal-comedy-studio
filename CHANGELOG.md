# Changelog

All notable changes to Terminal Comedy Studio follow
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- English is the default language. `--language fa` or `LANGUAGE=fa` switches to Persian.
- Textual is now a runtime dependency. It is the only one.

### Added

- Pixel-letter stage: a LIVE light and TERMINAL COMEDY in a pink-to-purple 5x7 pixel
  font, and the comedian's name under the mascot in a 3x5 pixel font. The layout
  adapts to the terminal: smaller letters on narrow screens, and the border carries
  the title when there is not enough height.

### Fixed

- The full-screen mascot was stretched to twice its width. It now draws one column
  and half a row per pixel, so pixels are square, and it scales to double size on
  large terminals.

### Added

- Stage UX: the line types into the speech bubble while the comedian talks, then lands
  with the bit's animation. A spinner with elapsed seconds shows while the model
  thinks. `Esc` skips the typing or cancels a slow bit, and a line typed mid-bit is
  queued instead of lost. Audience reactions pop under the bubble. A blinking LIVE
  light, a stage floor, and a transcript with name badges. The status bar shows
  context-sensitive key hints, and `F1` or `/help` opens a help screen. The README
  lists every command, key and option.
- A full-screen app built on Textual is now the default stage. The mascot is drawn
  with half blocks, so its pixels are square. It has a speech bubble, a scrolling
  transcript, an input line with history, a `/` command menu with Tab completion,
  arrow-key pickers for `/connect` and `/model`, and a status bar. `--classic` keeps
  the line-by-line stage, and pipes use it automatically.
- A folder harness. `comedian` started in any folder can look at it through
  read-only tools: a summary, the file list, one file, the git log and git status.
  It asks permission first (once, always for this show, or no). It never leaves the
  folder and refuses files that usually hold secrets. `/look` performs a bit about
  the folder, offline too. `/tools ask|allow|off` and `--look` control access.
- Install as a global command: `uv tool install git+https://github.com/masihft/terminal-comedy-studio`
  (or pipx), then run `comedian` from any folder.
- `/connect` (alias `/login`) connects a model from the stage, with no file editing.
  OpenRouter offers browser sign-in through its OAuth PKCE flow, plus a paste-the-code
  path for SSH. OpenAI and Anthropic take a pasted API key, read without echo.
  OmniRoute and local servers take a base URL. The comedian then lists the provider's
  models to pick from, and, if you agree, saves the connection to an owner-only
  `~/.config/terminal-comedy-studio/.env`.
- `/model` lists or sets the model for the provider on stage; `/logout` removes the
  saved key and goes offline.
- `/save [file]` writes the whole set — every line, not just the prompt window —
  to a local markdown file. It refuses to overwrite an existing file.
- Each comedian wears their own jacket — pink for Claw'd, purple for Sarkash,
  light pink for Mr Blonde — on the exact same mascot silhouette.
- Offline closers end on the comedian's catchphrase when it matches the show's
  language, so the presets differ even without an AI provider.
- GitHub Actions workflow running the tests on Linux, macOS and Windows,
  Python 3.10 and 3.13.

### Fixed

- The stage stops the terminal echoing keystrokes while it owns the screen. Typing
  ahead during an animation used to paint a line of its own into the middle of the
  block, so the in-place repaint could not count it and the box walked down a row
  every turn.

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
- Test suite of 133 tests covering frames and geometry, animation validity,
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

[Unreleased]: https://github.com/masihft/terminal-comedy-studio/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/masihft/terminal-comedy-studio/releases/tag/v0.1.0
