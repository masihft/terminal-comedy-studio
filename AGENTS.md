# AGENTS.md

# Terminal Comedy Studio — Coding Agent Instructions

## 1. PROJECT IDENTITY

You are the coding agent responsible for building and maintaining:

# Terminal Comedy Studio

Terminal Comedy Studio is an interactive AI stand-up comedian that lives inside the terminal.

The product should feel like a tiny comedy studio / virtual comedy stage running directly inside a terminal.

The primary experience is:

- character
- comedy
- personality
- animation
- stage presence
- audience interaction
- AI-generated jokes and conversations

It is NOT primarily:

- a coding assistant
- a CLI chatbot
- a Claude Code replacement
- a developer automation tool

Coding-related integrations may exist later, but comedy is the core product.

The application should feel entertaining even when the user does absolutely no programming.


# 2. CORE PRODUCT VISION

The user launches:

    comedian

and enters a small virtual comedy stage.

The terminal becomes the stage.

The comedian appears as a pixel/terminal character.

The character can:

- stand idle
- blink
- move
- talk
- react
- tell jokes
- perform stand-up
- roast
- tell stories
- react to the audience
- react to events
- improvise
- remember callbacks
- change emotions
- respond naturally

The experience should feel closer to:

"A tiny AI comedian living inside my terminal."

than:

"An AI CLI tool."


# 3. DEVELOPMENT PRIORITY

Always prioritize in this order:

1. Character
2. Comedy
3. User experience
4. Terminal presentation
5. AI interaction
6. Architecture
7. Integrations
8. Advanced features

Do not sacrifice the character experience for unnecessary engineering complexity.

Do not over-engineer the first version.


# 4. PRODUCT PRINCIPLES

The project must follow these principles.

## Character First

The character is the identity of the application.

The user should recognize the comedian immediately.

## Comedy First

Every feature should ultimately improve the comedy experience.

## Terminal Native

The application should genuinely feel designed for a terminal.

Do not simply build a web application and put it inside a terminal wrapper.

## Cross Platform

Prefer implementations that work across:

- macOS
- Linux
- Windows

Avoid unnecessary platform-specific assumptions.

## Open Source

The repository must be suitable for a public GitHub repository.

Never commit:

- API keys
- tokens
- private credentials
- personal paths
- secrets
- private configuration


# 5. CLAUDE CODE VISUAL REFERENCE

Before implementing the final comedian character, the coding agent MUST inspect the locally installed Claude Code application.

Run:

    claude

The purpose is NOT to use Claude Code as the application.

Claude Code is being used strictly as a visual reference for the comedian character.

The coding agent should inspect how the Claude Code mascot appears and use that as the primary visual reference for the character.

Do not invent an unrelated mascot.

Do not create a generic ASCII person.

Do not replace the mascot with a completely different animal or character.

The comedian should preserve the recognizable pixel/block construction and overall silhouette of the Claude Code mascot while adapting it into the Terminal Comedy Studio visual identity.


# 5.1 CHARACTER GEOMETRY

The character must be constructed from a discrete pixel/grid system.

The character should have:

- a square main head/body
- exactly two rectangular ears
- exactly two eyes
- exactly three centered rectangular legs

The ears belong on the sides of the main square character around the middle vertical area.

They are NOT horns.

They are NOT placed on the top corners.

They are NOT floating above the head.

The three legs should be centered underneath the main body.

The character should remain recognizable when rendered using only simple terminal cells.

The character should be constructed using a shared pixel/grid representation.

Do NOT construct the suit and mascot as unrelated visual layers.


# 5.2 CHARACTER STYLE

The comedian version should have the project's pink/neon-pink visual identity.

The mascot should appear as a comedian performing on stage.

The character may include:

- pink suit/jacket
- microphone
- expressive eyes
- stage lighting
- comedy-performance poses

However, the underlying mascot silhouette must remain recognizable.

The character should feel like:

Claude Code mascot → transformed into a terminal stand-up comedian

not:

random pixel comedian


# 5.3 CHARACTER IMPLEMENTATION RULES

The character renderer must be grid/pixel based.

Prefer:

- terminal cells
- Unicode blocks
- ANSI colors
- frame arrays
- deterministic pixel maps

Avoid:

- HTML/CSS shapes
- browser DOM-based characters
- SVG circles
- arbitrary vector geometry
- gradients as the character itself
- rounded UI components pretending to be pixels

The visual character should work inside a real terminal.


# 5.4 CHARACTER ANIMATION

Animation should be frame based.

At minimum support:

- idle
- blink
- talking
- thinking
- surprised
- laughing
- punchline
- reaction

Animation may modify:

- eyes
- ears
- body
- legs
- microphone
- pose

The initial implementation does not need sophisticated physics.

Simple multi-frame pixel animation is preferred.

For example:

    idle_01
    idle_02
    idle_03
    idle_02

rather than complicated animation systems.


# 6. PRODUCT MODES

The application should eventually support:

    Stage
    Stand-up
    Chat
    Roast
    Story
    Random

## Stage

The default experience.

The comedian appears on stage and interacts with the user.

## Stand-up

The comedian performs a sequence of jokes.

## Chat

Natural conversation with the comedian.

## Roast

Playful comedy roasting.

Roasts must remain within safe comedic boundaries.

## Story

The comedian generates and performs a short comedic story.

## Random

The comedian chooses something entertaining to perform.


# 7. OPTIONAL CLAUDE CODE INTEGRATION

Claude Code integration is optional.

It is NOT the core product.

The comedian may eventually react to coding activity.

Examples:

    user writes code
            ↓
    event detected
            ↓
    comedian reacts

Possible reactions:

    "Interesting approach."

    "That function has seen things."

    "Three nested loops? Bold."

    "Your terminal is becoming a cry for help."

The integration must remain modular.

The core application must work perfectly without Claude Code.

Never make Claude Code a hard dependency.


# 8. AI PROVIDER ARCHITECTURE

AI access must use an abstraction.

Create an interface similar to:

    class AIProvider:
        def generate(self, prompt: str, context: dict) -> dict:
            ...

The application should not hard-code one AI provider into the comedy engine.

Potential providers:

- OmniRoute
- OpenAI
- Anthropic
- local models
- custom HTTP providers


# 9. AI RESPONSE FORMAT

Internally, AI responses should support structured information.

For example:

    {
      "text": "The joke text goes here.",
      "emotion": "laughing",
      "animation": "talking",
      "duration": 3.5
    }

The renderer should not need to understand the AI provider.

The AI layer produces semantic output.

The presentation layer decides how to display it.


# 10. OMNIROUTE

OmniRoute may be supported as an AI provider.

However:

OMNIROUTE MUST NEVER be assumed to exist.

The application must work without OmniRoute.

Configuration should happen through environment variables or configuration files.

Example:

    AI_PROVIDER=omniroute
    OMNIROUTE_BASE_URL=http://localhost:20128
    OMNIROUTE_MODEL=

Do not hard-code:

    localhost:20128

into application logic.


# 11. CHARACTER SYSTEM

Create a reusable character system.

A character should be able to define:

    name
    personality
    comedic_style
    language
    tone
    boundaries
    catchphrases
    moods
    topics
    performance_style

Example:

    Character(
        name="Comedian",
        personality="confident, playful, sarcastic",
        comedic_style="observational",
        language="fa",
        tone="friendly",
    )

The architecture should eventually support multiple comedians.

Do not hard-code the entire personality directly into the renderer.


# 12. COMEDY ENGINE

Create modular comedy components.

Suggested architecture:

    ComedyEngine
    ├── JokeGenerator
    ├── StoryGenerator
    ├── RoastGenerator
    ├── ReactionGenerator
    ├── ImprovisationEngine
    ├── CallbackEngine
    └── RandomBitGenerator

The first MVP does not need every component fully implemented.

Build the smallest useful version first.


# 13. CALLBACK SYSTEM

The comedian should eventually remember jokes or topics from the current session.

Example:

User:

    I hate debugging.

Comedian later:

    Remember when you said you hated debugging?

    Your code apparently took that personally.

Callbacks should be intentional.

Do not make the comedian randomly repeat every previous message.


# 14. AUDIENCE SYSTEM

The user should feel like an audience member.

Future audience concepts may include:

    audience_reaction
    laugh
    silence
    awkward
    applause
    boo
    surprise

Example:

    😂 HAHAHA
    👏 APPLAUSE
    ...
    ...
    awkward silence

Do not overuse fake reactions.

Silence can be funny.


# 15. STAGE UI

The default terminal screen should resemble a tiny comedy stage.

Conceptually:

    ┌───────────────────────────────────────────────┐
    │             TERMINAL COMEDY                  │
    │                                               │
    │                  🎤                           │
    │                [CHARACTER]                    │
    │                                               │
    │              LIVE FROM YOUR                  │
    │                 TERMINAL                     │
    │                                               │
    ├───────────────────────────────────────────────┤
    │ You: type something...                        │
    └───────────────────────────────────────────────┘

The actual visual design should be more polished than this example.

Primary visual identity:

- dark terminal
- neon pink
- white
- subtle purple
- pixel aesthetic
- stage lighting
- terminal typography

Avoid turning the UI into a generic dashboard.


# 16. TERMINAL RENDERING

Character rendering should support:

    ASCII
    Unicode
    ANSI
    Unicode block characters

Potential future renderers:

    BasicRenderer
    ANSIArtRenderer
    ImageRenderer
    KittyRenderer
    SixelRenderer

Do not implement all of these in the MVP.

Start with a robust basic renderer.


# 17. FUTURE TERMINAL GRAPHICS

Potential future support:

- Kitty graphics protocol
- iTerm2 inline images
- Sixel
- Unicode block rendering
- ANSI art

Architecture should make these possible later without rewriting the entire application.


# 18. SPEECH / VOICE

Voice is a future feature.

Do NOT make voice a dependency for the MVP.

Future architecture may include:

    Text
      ↓
    TTS
      ↓
    Audio
      ↓
    Speech synchronization
      ↓
    Character animation

Do not build a complicated speech synchronization system before the basic text experience works.


# 19. SPEECH SYNCHRONIZATION

Future versions may synchronize:

- mouth
- eyes
- body
- microphone
- timing

with generated speech.

Do not build a complicated speech synchronization system before the basic text experience works.


# 20. INPUT SYSTEM

Natural language is the primary interface.

Users should be able to type:

    tell me a joke

or:

    امروز خیلی خسته‌ام

without learning commands.

Optional commands:

    /help
    /exit
    /quit
    /roast
    /joke
    /story
    /standup
    /random
    /mode
    /settings
    /character
    /reset

Commands should be secondary to natural interaction.


# 21. SESSION MEMORY

The MVP should support lightweight session context.

The comedian should know what was recently said during the current session.

Persistent memory is optional for later versions.

Do not build a large database just to remember a few messages.


# 22. CONFIGURATION

Configuration must be externalized.

Use:

    .env

and/or a user configuration file.

Never commit real credentials.

Provide:

    .env.example

with placeholders.

Example:

    AI_PROVIDER=
    AI_MODEL=
    OPENAI_API_KEY=
    ANTHROPIC_API_KEY=
    OMNIROUTE_BASE_URL=
    OMNIROUTE_MODEL=
    LANGUAGE=fa


# 23. SECURITY

The comedian must NEVER automatically execute arbitrary AI-generated shell commands.

AI-generated text is data.

It is not trusted code.

Never:

- execute generated shell commands automatically
- expose environment variables to the model unnecessarily
- print API keys
- send local files silently
- upload files without explicit user intent
- execute arbitrary code generated by the model

Integrations must be explicit and permission-aware.


# 24. PRIVACY

The application should clearly communicate when external AI services are used.

Do not silently send:

- local files
- terminal history
- environment variables
- private project contents

to an external provider.

Only send the minimum context required.


# 25. TECHNOLOGY SELECTION

Before committing to the production UI architecture, investigate current terminal UI options.

At minimum compare two viable approaches.

Potential candidates:

### Python

- Textual
- Rich
- prompt_toolkit

### Node.js

- Ink
- blessed
- @clack/prompts

### Rust

- Ratatui
- Crossterm

The coding agent should compare:

- animation support
- Unicode support
- ANSI support
- terminal resizing
- input handling
- cross-platform support
- installation experience
- developer ergonomics
- performance
- ecosystem maturity

Build a tiny renderer prototype before committing to the final architecture.


# 26. MVP

The first version must remain small.

MVP should include:

- installable command

    comedian

- terminal stage
- pixel character
- Claude Code-inspired mascot geometry
- idle animation
- typing/input
- AI response
- talking animation
- return to idle
- at least 3 emotions
- /exit
- configurable AI provider
- Persian support
- English support where practical
- README
- clean GitHub repository
- tests
- no secrets

The MVP does NOT require:

- voice
- advanced graphics
- persistent memory
- Claude Code integration
- OpenClaw integration
- complex databases


# 27. PROJECT STRUCTURE

The target repository should be approximately:

    terminal-comedy-studio/
    │
    ├── AGENTS.md
    ├── README.md
    ├── LICENSE
    ├── CONTRIBUTING.md
    ├── SECURITY.md
    ├── CHANGELOG.md
    ├── .gitignore
    ├── .env.example
    ├── pyproject.toml
    │
    ├── src/
    │   └── terminal_comedian/
    │       ├── __init__.py
    │       ├── main.py
    │       ├── cli.py
    │       │
    │       ├── character/
    │       │   ├── __init__.py
    │       │   ├── character.py
    │       │   ├── personality.py
    │       │   ├── states.py
    │       │   └── frames.py
    │       │
    │       ├── comedy/
    │       │   ├── __init__.py
    │       │   ├── engine.py
    │       │   ├── jokes.py
    │       │   ├── stories.py
    │       │   ├── roast.py
    │       │   ├── callbacks.py
    │       │   └── reactions.py
    │       │
    │       ├── ai/
    │       │   ├── __init__.py
    │       │   ├── provider.py
    │       │   ├── omniroute.py
    │       │   ├── openai.py
    │       │   ├── anthropic.py
    │       │   └── local.py
    │       │
    │       ├── ui/
    │       │   ├── __init__.py
    │       │   ├── stage.py
    │       │   ├── renderer.py
    │       │   ├── animation.py
    │       │   ├── terminal.py
    │       │   └── input.py
    │       │
    │       ├── memory/
    │       │   ├── __init__.py
    │       │   ├── session.py
    │       │   └── persistent.py
    │       │
    │       ├── integrations/
    │       │   ├── __init__.py
    │       │   ├── claude_code.py
    │       │   ├── openclaw.py
    │       │   └── omniroute.py
    │       │
    │       └── config/
    │           ├── __init__.py
    │           └── settings.py
    │
    ├── assets/
    │   ├── characters/
    │   ├── animations/
    │   ├── themes/
    │   └── sounds/
    │
    ├── tests/
    │   ├── test_character.py
    │   ├── test_renderer.py
    │   ├── test_comedy.py
    │   ├── test_ai.py
    │   └── test_config.py
    │
    └── scripts/
        ├── dev.sh
        ├── test.sh
        └── demo.sh

The exact structure may be adjusted based on the selected framework.

Do not create empty abstractions simply to match this tree.

Only create modules that have a meaningful purpose.


# 28. GITHUB READINESS

The repository must be ready to publish publicly on GitHub.

At minimum include:

    README.md
    LICENSE
    CONTRIBUTING.md
    SECURITY.md
    CHANGELOG.md
    .gitignore
    .env.example
    pyproject.toml

The repository must not contain:

- API keys
- personal absolute paths
- private usernames
- local machine configuration
- private tokens
- temporary files
- IDE-specific junk
- generated secrets


# 29. README REQUIREMENTS

README.md must feel like a real open-source project.

It should include:

## Project name

Terminal Comedy Studio

## Hero description

Explain the product in one or two strong sentences.

Example:

    An AI stand-up comedian that lives inside your terminal.

## Visual demo

Reserve space for:

- screenshot
- GIF
- terminal recording

Example:

    ![Terminal Comedy Studio](assets/demo.gif)

If a real demo asset does not exist yet, do not fabricate one.

Use a TODO marker instead.

## Features

Explain:

- terminal comedian
- pixel character
- AI jokes
- stand-up mode
- chat
- roast
- story
- animations
- provider support

## Installation

Show exact commands.

For example:

    git clone ...
    cd terminal-comedy-studio
    pip install -e .

Then:

    comedian

## Configuration

Explain .env.

## Commands

Document:

    /help
    /joke
    /roast
    /story
    /standup
    /random
    /exit

## Providers

Explain supported AI providers.

## Architecture

Briefly explain the main components.

## Development

Show:

    pytest

and any required development commands.

## Roadmap

Show planned releases.

## Contributing

Link to CONTRIBUTING.md.

## Security

Link to SECURITY.md.

## License

State the license.


# 30. LICENSE

Use a standard open-source license.

Unless the project owner explicitly specifies another license, use MIT.

Do not invent a custom license.


# 31. CONTRIBUTING.md

Include:

- development setup
- project structure
- running tests
- coding standards
- pull request expectations
- issue reporting
- feature proposals
- character/comedy contribution guidelines

Keep it friendly and beginner accessible.


# 32. SECURITY.md

Explain:

- responsible disclosure
- no secrets in issues
- no API keys in commits
- AI-generated commands must not be automatically executed
- external integrations must be explicit
- privacy considerations

Do not include private contact information unless explicitly provided by the project owner.


# 33. CHANGELOG.md

Start with:

    # Changelog

and create an initial unreleased section.

Example:

    ## [Unreleased]

    ### Added
    - Initial terminal comedian architecture
    - Pixel character renderer
    - AI provider abstraction

Do not claim features exist unless they actually exist.


# 34. .GITIGNORE

The repository should ignore at least:

    .env
    .venv/
    venv/
    __pycache__/
    *.py[cod]
    .pytest_cache/
    .mypy_cache/
    .ruff_cache/
    .DS_Store
    .idea/
    .vscode/
    dist/
    build/
    *.egg-info/
    node_modules/

Adjust based on the actual technology stack.


# 35. PYPROJECT / PACKAGE CONFIGURATION

If Python is selected, create a proper pyproject.toml.

It should define:

- project name
- version
- description
- Python version
- dependencies
- optional development dependencies
- CLI entry point

The CLI should expose:

    comedian

Example conceptual configuration:

    [project.scripts]
    comedian = "terminal_comedian.main:main"

Use the actual package structure implemented by the agent.


# 36. TESTING

Tests should cover at least:

- character construction
- frame validity
- renderer output
- animation transitions
- comedy engine
- provider abstraction
- configuration
- command parsing

The tests must not require real API credentials.

Use mocks/fakes for external providers.


# 37. DEVELOPMENT WORKFLOW

Build in small verified stages.

Do not immediately create the entire architecture.

Follow this sequence:

## Stage 1 — Environment Inspection

Inspect:

- operating system
- shell
- Python
- Node
- Rust if available
- Git
- terminal capabilities
- installed package managers
- repository status
- existing files

Also check whether:

    claude

exists.


## Stage 2 — Claude Code Visual Inspection

Run:

    claude

and inspect the actual Claude Code interface and mascot.

Use it as the primary visual reference for the character.

If the environment cannot visually expose the interactive Claude Code UI to the coding agent, document this limitation honestly.

Do NOT claim to have inspected something that was not visible.

If Claude Code is unavailable, use the documented mascot geometry in this file and continue.


## Stage 3 — Framework Comparison

Compare at least two terminal UI approaches.

Document:

- pros
- cons
- animation
- input
- rendering
- cross-platform behavior
- installation

Then select the simplest technology that satisfies the MVP.


## Stage 4 — Tiny Renderer Prototype

Before implementing the complete application, build a minimal prototype containing:

    terminal stage
    comedian character
    name
    idle animation
    talking animation

Verify:

- Unicode rendering
- ANSI colors
- terminal resize
- input
- animation timing
- character geometry

Do not proceed to a large architecture until this works.


## Stage 5 — Character System

Implement:

- pixel map
- character states
- frame system
- animation system
- emotions

Ensure the mascot geometry matches the Claude Code visual reference.


## Stage 6 — Comedy Engine

Implement:

- joke
- reaction
- conversation

Then add:

- roast
- story
- stand-up
- callbacks


## Stage 7 — AI Provider

Implement provider abstraction.

Add at least one working provider.

Keep the provider replaceable.


## Stage 8 — CLI

Implement:

    comedian

and command handling.


## Stage 9 — GitHub Packaging

Create:

    README.md
    LICENSE
    CONTRIBUTING.md
    SECURITY.md
    CHANGELOG.md
    .gitignore
    .env.example
    pyproject.toml

Run tests.

Run the application.

Check the repository for secrets.


# 38. USER EXPERIENCE TARGET

The first ten seconds are extremely important.

The ideal flow is:

    $ comedian

    Terminal Comedy Studio

                 [comedian appears]

           "Welcome to my terminal."

              🎤

    > _

The user should immediately understand:

1. what this is
2. who the character is
3. that they can talk to it
4. that it is alive/animated

Do not show a wall of configuration before the character appears.


# 39. PERSONALITY

The default comedian should feel:

- witty
- playful
- slightly sarcastic
- confident
- friendly
- expressive
- unpredictable
- self-aware

Avoid:

- generic assistant language
- corporate tone
- constant enthusiasm
- repetitive jokes
- forced memes
- trying too hard to be funny

The comedian should sometimes be understated.

Silence can be funny.


# 40. LANGUAGE

Persian should be supported from the beginning.

The default language should preferably be:

    fa

The system should handle Persian Unicode correctly.

The UI should not break when Persian text is displayed.

English should remain possible.

Do not assume every joke must be translated literally.

Comedy should respect the language and cultural context.


# 41. COMEDY SAFETY

Comedy can include:

- sarcasm
- absurdity
- playful roasting
- observational humour
- fictional situations

Avoid harmful content.

Roasting should target:

- harmless situations
- fictional scenarios
- everyday behaviour

Do not turn the product into a tool for targeted harassment.


# 42. FUTURE EXTENSIONS

Potential future features:

### v0.1

- terminal stage
- pixel character
- idle animation
- talking animation
- basic AI conversation

### v0.2

- stand-up mode
- roast mode
- story mode
- more animations
- audience reactions

### v0.3

- multiple characters
- personality presets
- callback memory
- better comedy engine

### v0.4

- Claude Code integration
- coding-event reactions
- OpenClaw integration
- OmniRoute improvements

### v0.5

- voice
- speech synchronization
- advanced terminal graphics

### v1.0

- polished cross-platform experience
- multiple renderers
- character marketplace
- plugins
- advanced memory
- high-quality comedy generation

Do not implement future features prematurely.


# 43. AGENT BEHAVIOUR

The coding agent should behave like a senior engineer working with a product designer.

Before changing architecture:

1. inspect the existing code
2. understand the current implementation
3. identify the smallest correct change
4. make the change
5. run relevant tests
6. verify the application
7. report what changed

Do not rewrite working systems without a reason.

Do not introduce dependencies without justification.

Do not create abstractions merely because they sound architectural.


# 44. VISUAL QUALITY REQUIREMENT

Visual quality is a first-class requirement.

The terminal character is not a decorative afterthought.

The agent must inspect the actual rendered output during development.

If possible:

- run the application
- capture terminal output
- inspect alignment
- resize the terminal
- inspect animation
- verify Persian rendering

Fix visual defects before adding unnecessary features.


# 45. CHARACTER CONSISTENCY

Every animation frame must preserve the same underlying character geometry.

The following should remain consistent:

- head/body dimensions
- ear positions
- eye positions
- leg positions
- overall silhouette

Animation should change expression or pose, not accidentally transform the character into a different creature.


# 46. DO NOT FAKE VISUAL INSPECTION

If a tool or environment does not allow the agent to actually see:

    claude

or the terminal UI:

DO NOT claim visual inspection was performed.

Instead:

1. state the limitation
2. use the documented geometry
3. continue implementation
4. leave a clear note for later visual verification

Honesty is more important than pretending a visual test passed.


# 47. NO SECRET DEPENDENCIES

The application must not require:

- private repositories
- undocumented services
- private APIs
- personal credentials
- local machine-specific paths

The default repository should be cloneable by another developer.


# 48. NO MACHINE-SPECIFIC PATHS

Never commit paths such as:

    /Users/<username>/...
    /home/<username>/...
    C:\Users\<username>\...

Use:

- relative paths
- environment variables
- configuration
- platform APIs


# 49. DEFINITION OF DONE

A feature is NOT done merely because the code exists.

A feature is done when:

- implementation exists
- imports work
- tests pass
- the feature runs
- terminal output is visually checked when relevant
- errors are handled
- documentation is updated when necessary
- no secrets were introduced
- cross-platform assumptions are reasonable


# 50. FINAL MVP DEFINITION

The first public version should allow someone to do:

    git clone <repo>
    cd terminal-comedy-studio
    pip install -e .
    comedian

and immediately see:

    TERMINAL COMEDY

with the pixel comedian on stage.

The comedian should:

- animate
- respond to input
- tell jokes
- talk
- change emotion
- return to idle

The character should visually follow the Claude Code mascot reference while being transformed into the project's pink comedy identity.

The user should feel:

"There is literally a comedian living in my terminal."

That feeling is the core product.


# 51. FIRST TASK

Before implementing the complete product, perform the following tasks in order:

### 1.

Inspect the repository and environment.

### 2.

Check whether Claude Code is installed:

    command -v claude
    claude --version

### 3.

Open Claude Code:

    claude

Inspect its actual visual character/interface.

Use the Claude Code mascot as the visual reference.

### 4.

Document the observed character geometry.

### 5.

Compare at least two terminal UI frameworks.

### 6.

Choose the simplest appropriate stack.

### 7.

Build the smallest terminal prototype:

    stage
    character
    name
    idle animation
    talking animation
    input

### 8.

Verify the prototype.

### 9.

Only after verification, implement the actual architecture.

### 10.

Finish the repository as a GitHub-ready open-source project including:

    README.md
    LICENSE
    CONTRIBUTING.md
    SECURITY.md
    CHANGELOG.md
    .gitignore
    .env.example
    package/project configuration
    source code
    tests
    assets
    scripts

Do not skip the prototype.

Do not build unnecessary features before the core character experience works.


# 52. FINAL PRINCIPLE

When making a technical decision, ask:

"Does this make the comedian more fun, more alive, easier to use, or easier to extend?"

If not, it probably does not belong in the first version.

The goal is not to build the most complicated AI terminal application.

The goal is to build the most convincing:

# AI COMEDIAN LIVING INSIDE A TERMINAL.