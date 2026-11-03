# Contributing

Thanks for being here. Terminal Comedy Studio is small on purpose: no runtime
dependencies, one character, one stage. The most valuable contributions are the
ones that make the comedian funnier without making the codebase bigger.

## Development setup

You need Python 3.10 or newer. Nothing else.

```bash
git clone https://github.com/masihft/terminal-comedy-studio.git
cd terminal-comedy-studio
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Then run it:

```bash
comedian
```

With no API key configured it still works — that is the offline show, and it is
a supported way to run the product, not an error state.

To talk to a model, copy `.env.example` to `.env` and fill in one provider.

## Running the tests

```bash
pytest
```

Or:

```bash
./scripts/test.sh
```

The suite must pass with no credentials and no network. If a test needs a
provider, it uses a fake one (`tests/test_providers.py`) or a throwaway local
HTTP server (`tests/test_http_transport.py`). Never add a test that calls a real
API.

## Project structure

```
src/terminal_comedian/
├── character/   grid frames, animation player, personalities
├── comedy/      engine, joke banks, callbacks, audience reactions
├── ai/          provider abstraction + one file per provider
├── prompts/     system persona and one role file per mode
├── memory/      session context
├── ui/          terminal capabilities, renderer, stage, animation, commands
└── cli.py       the REPL
```

`AGENTS.md` at the root is the product spec. When a change touches the
character, the comedy or the privacy model, read the relevant section there
first — §5.3 (rendering rules), §23–24 (security and privacy), §41 (comedy
safety), §45 (character consistency).

## Coding standards

- Python 3.10+, standard library only. Adding a dependency needs a paragraph of
  justification in the pull request, and `docs/framework-comparison.md`
  explains why the bar is high.
- Type hints on public functions; no comments unless the *why* is invisible.
- Match the formatting of the file you are editing. There is no linter config
  to argue about yet.
- Keep provider differences inside `ai/`. The renderer and the comedy engine
  must not know which vendor is answering.

## Character and comedy contributions

New frames: every animation frame must keep the same mascot geometry — square
body, exactly two rectangular ears on the sides, two eyes, three centred legs.
`tests/test_character.py` enforces this. If a frame changes the silhouette, it
is a different creature, not an animation.

New jokes: `comedy/jokes.py` holds the offline banks for Persian and English.
Add to both, keep them short, and keep roasts aimed at situations (a merge
conflict, a 2am commit) rather than at people. See §41.

New modes: a mode is a markdown role file in `prompts/` plus a route keyword in
`comedy/engine.py` plus a command in `ui/input.py`. The help text generates
itself from the command table, so there is nothing to keep in sync there.

## Pull requests

- One idea per pull request.
- Describe what the user now sees, not only what you changed. Screenshots or a
  `scripts/demo.sh` transcript help more than prose.
- If you touched rendering or Persian text, say which terminal you checked it
  in. Visual defects are the change, not a footnote.
- Tests for new behaviour. If you removed a test, say why in the description.
- Run `pytest` before asking for review; CI does too.

Keep commit messages imperative and short: `Add the roast mode`, not
`feat: implement roast (JIRA-123)`.

## Reporting issues

A bug report should include the terminal and OS, the width of the window, the
provider in use (`/settings` prints it), and the exact text you typed. For
rendering problems, a copy-paste of the broken box is worth more than a
description of it.

Do not put API keys in issues, logs or attachments. See [SECURITY.md](SECURITY.md)
for anything sensitive.

## Releasing

The repository is published as `masihft/terminal-comedy-studio`, and that URL
appears in `pyproject.toml`, `README.md`, `SECURITY.md` and `CHANGELOG.md`. If
the project moves to another account or an organisation, change it in those four
places before tagging a release.

A release is:

```bash
pytest                                   # must be green
python -m venv /tmp/check && /tmp/check/bin/pip install .
/tmp/check/bin/comedian --version        # the installed package, not the tree
```

Then bump `version` in `pyproject.toml` and `src/terminal_comedian/__init__.py`
together, move the `[Unreleased]` notes in `CHANGELOG.md` under the new version,
and tag `vX.Y.Z`. `CHANGELOG.md` only lists what actually exists in the tree —
if a feature is not in the code, it goes in the roadmap, not the changelog.

## Ground rules

- Never commit `.env`, keys, tokens or personal absolute paths.
- Never auto-run anything the model generated. Text from a provider is data.
- Do not claim a visual check you did not perform. If your environment cannot
  show the UI, say so in the pull request.

This project has a code of conduct in one sentence: be kind, and remember the
comedian is the product, not the framework around it.
