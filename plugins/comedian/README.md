# comedian: Claw'd for Claude Code and Codex

The Terminal Comedy Studio comedian as an agent plugin. The full-screen terminal app lives in
the repository root; this folder is only the plugin.

| Skill | Claude Code | Codex | Touches files? |
| --- | --- | --- | --- |
| `joke` | `/comedian:joke [topic]` | `$joke` | no, read-only |
| `roast` | `/comedian:roast [file\|commits]` | `$roast` | no, read-only |
| `standup` | `/comedian:standup [topic]` | `$standup` | no, read-only |
| `review` | `/comedian:review [file\|ref]` | `$review` | no, read-only: real findings, told as stand-up |
| `pair` | `/comedian:pair <task>` | `$pair` | only through the agent's normal permissions |
| Comedian output style | `/output-style` → Comedian | (not available) | only through Claude Code's normal permissions |

## Install

Claude Code:

```text
/plugin install comedian --marketplace masihft/terminal-comedy-studio
```

Codex:

```bash
codex plugin marketplace add masihft/terminal-comedy-studio
```

then install `comedian` from the plugin list. More in the repository README.
