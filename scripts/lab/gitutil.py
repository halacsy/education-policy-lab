"""Git via subprocess (audit trail of self-improvement)."""
import subprocess

from .util import ROOT


def _run(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True, check=False)


def topic_paths():
    """Everything a round is allowed to commit (D-35): the current topic's
    committed state + outputs, and the shared config (a catalog change may
    touch it). Scoped so concurrent topics never cross-commit each other's
    work — and stray uncommitted files in the tree stay out of round
    commits (the old `git add -A` gotcha)."""
    from . import topic
    T = topic.current()
    return [str(T.dir.relative_to(ROOT)),
            str(T.out_root.relative_to(ROOT)),
            "config/system_config.json"]


def commit(message, paths=None):
    """Commit `paths` (pathspecs relative to ROOT); None means the current
    topic's scope (topic_paths). Ignores pathspecs that match nothing."""
    if paths is None:
        paths = topic_paths()
    _run("add", "--", *paths)
    r = _run("commit", "-m", message, "--", *paths)
    if r.returncode != 0 and "nothing to commit" not in r.stdout + r.stderr:
        raise RuntimeError(f"git commit failed: {r.stdout}\n{r.stderr}")
    return r.returncode == 0


def log_oneline():
    return _run("log", "--oneline").stdout
