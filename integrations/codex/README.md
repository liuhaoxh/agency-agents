# Codex

Install The Agency into Codex as global `agency-*` skills under `~/.codex/skills/`.

## Install

From this repo:

```bash
./scripts/install.sh --tool codex
```

This does three things:

1. Converts each upstream Agency agent into a Codex-compatible `SKILL.md`
2. Writes generated wrappers into `~/.codex/vendor_imports/skills/agency-agents/`
3. Exposes each wrapper through `~/.codex/skills/agency-*`

## Direct Installer

If you want to call the Codex installer directly:

```bash
python3 ./scripts/install_codex.py
```

Optional flags:

```bash
python3 ./scripts/install_codex.py --codex-home ~/.codex
python3 ./scripts/install_codex.py --repo-root /path/to/agency-agents
```

## Remotes

Recommended git remote layout for a Codex-adapted fork:

```bash
git remote set-url origin https://github.com/liuhaoxh/agency-agents.git
git remote add upstream https://github.com/msitarzewski/agency-agents.git
```

Then keep the fork up to date with:

```bash
git fetch upstream
git merge upstream/main
```

After pulling updates, rerun:

```bash
./scripts/install.sh --tool codex
```

## Result

Imported skills are prefixed with `agency-` to avoid collisions with project-local
Codex skills.
