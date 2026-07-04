"""Git via subprocess (audit trail of self-improvement)."""
import subprocess

from .util import ROOT


def _run(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True, check=False)


def commit(message):
    _run("add", "-A")
    r = _run("commit", "-m", message)
    if r.returncode != 0 and "nothing to commit" not in r.stdout + r.stderr:
        raise RuntimeError(f"git commit failed: {r.stdout}\n{r.stderr}")
    return r.returncode == 0


def log_oneline():
    return _run("log", "--oneline").stdout
