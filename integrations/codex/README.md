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
git remote set-url origin git@github.com:liuhaoxh/agency-agents.git
git remote add upstream https://github.com/msitarzewski/agency-agents.git
```

Use SSH for `origin` if your machine has GitHub SSH configured. This avoids HTTPS
TLS issues such as `LibreSSL SSL_connect: SSL_ERROR_SYSCALL`.

## Sync From Upstream

From your Codex environment, use:

```bash
rtk proxy git -C ~/.codex/vendor_imports/agency-agents fetch upstream
rtk proxy git -C ~/.codex/vendor_imports/agency-agents merge upstream/main
rtk proxy sh -lc 'cd ~/.codex/vendor_imports/agency-agents && ./scripts/install.sh --tool codex --no-interactive'
```

If you are already inside the repo, the shorter form also works:

```bash
git fetch upstream
git merge upstream/main
```

After pulling updates, rerun the Codex installer so the generated `agency-*`
skills are refreshed:

```bash
./scripts/install.sh --tool codex
```

## Result

Imported skills are prefixed with `agency-` to avoid collisions with project-local
Codex skills.
