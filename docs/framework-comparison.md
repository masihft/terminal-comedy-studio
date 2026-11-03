# Terminal UI: what we compared and why the harness has no dependencies

AGENTS.md §25 and §37 Stage 3 require the choice to be investigated, not
assumed. This document records what was measured.

Every number below was read from a fresh `git clone` of the project named, at
the commit shown. Nothing here is second-hand.

| Project | Commit read | UI stack measured | Size of the loop we were cloning |
| --- | --- | --- | --- |
| `Textualize/textual` | `5e5b7ef` | Python, own reactor + compositor | `src/textual/app.py` = 5,040 lines; whole package = 82,461 lines |
| `openai/crush` (Charm) | `3b1f860` | Go, `charm.land/bubbletea/v2 v2.1.0` + `lipgloss/v2 v2.0.6` | `require (...)` block = 203 module lines |
| `sigoden/aichat` | `82976d3` | Rust, `crossterm = "0.28.1"` + `reedline = "0.40.0"` | full `[dependencies]` block, plus `hyper`, `reqwest-eventsource` |
| `Aider-AI/aider` | `5dc9490` | Python, `prompt-toolkit==3.0.52` | `aider/main.py` = 1,274 lines; `aider/aider/` = 20,285 lines |
| `simonwillison/llm` | `2cd2661` | Python, `click` | `llm/cli.py` = 4,556 lines, 15 declared runtime deps |
| `block/goose` | `cfb67d7` | Rust, `tokio` + `axum`, non-terminal-first | — |

## What each one actually gave us

**Textual.** The most capable option and the reason we did not choose it. Its
core is a full-screen application: a reactor, a message pump, a compositor, a
CSS-like layout engine and its own input loop. `app.py` alone is 5,040 lines,
and the package needs `rich`, `markdown-it-py`, `mdit-py-plugins`,
`platformdirs` and `typing-extensions` before it draws anything. A comedy
stage is a rectangle that repaints in place; wrapping that in an application
framework means `pip install -e .` pulls six projects onto the user's machine
before they see the mascot. It also owns the terminal in alternate-screen
mode, which is exactly what AGENTS.md §15 and the "it is a CLI" constraint
rule out — the comedian should coexist with the shell, the user's scrollback
and Ctrl-C.

**Crush / Bubble Tea.** Excellent model, wrong runtime. The update-view-command
loop and `tea.Program` are a real fit for animation, but adopting it means the
project becomes Go and loses the stdlib-only property that makes
`comedian` installable anywhere Python is. We took the *idea*: animation is a
tick function, not a widget.

**aichat.** Read this for the provider layer rather than the renderer. Its
`config.yml` lists many providers behind one trait, and the streaming code
distinguishes an event stream from a plain body — the same split our
`ai/http.py` makes. Its terminal handling is `crossterm` for raw output and
`reedline` for editing; that is the pairing we deliberately did not pay for.

**aider.** The closest shape to what this product is: a normal REPL over
`input()`, a command table where the help text is generated from the table
instead of maintained beside it, and repaints coalesced so a fast stream does
not thrash the screen. We copied that harness. `prompt_toolkit` buys history
and completion; neither is worth a dependency at v0.1.

**llm.** The template for provider registration: a declarative registry keyed
by provider id, where each entry names the *environment variable* holding the
key instead of holding the key. That is why `AIProvider.key_env` is a name and
never a secret, and why `/settings` can print what is configured without ever
printing a token.

**goose.** Read for prompt assembly and for structured output: a model reply is
parsed as data, with a defined fallback when the JSON is malformed. Our
`parse_comedy_response` follows that, and its fallback is lossless — if the
JSON is unusable we keep the raw text rather than dropping the joke.

## The decision

Python 3.10+, standard library only, no runtime dependencies.

The harness is the one aider and llm both converged on: a blocking `input()`
loop, a data-driven command table, and line-based output that stays in the
terminal's own scrollback. Everything we needed from a framework is
implemented in `src/terminal_comedian/ui/` in 438 lines:

- `terminal.py` — capabilities measured from the environment (`COLORTERM`,
  `NO_COLOR`, `TERM`, `isatty`, `shutil.get_terminal_size`), display width for
  East Asian and combining characters, ANSI stripped before measuring, and a
  bidi guard so Persian rows cannot drag the box walls to the wrong side.
- `renderer.py` — grid frames to block characters with truecolour SGR, with
  ASCII and no-colour fallbacks for terminals that cannot do either.
- `stage.py` — the box, the mascot, the speech.
- `animation.py` — in-place repaint by relative cursor movement, capped at 20
  fps because past that the frames blur into flicker.
- `input.py` — the command table; `/help` is generated from it.

Animation runs during the beats where the program already owns the screen —
while a reply streams in, while a set is performed — not on a background timer
fighting the prompt. That is the one genuine compromise of not using a
framework, and it is a cheaper compromise than six dependencies.

Adding a dependency needs to buy something the standard library cannot do.
None of the six candidates above did.
