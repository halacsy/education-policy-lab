"""Shared helpers: paths, config, IO, hashing."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = ROOT / "config" / "system_config.json"
AGENTS_DIR = ROOT / "agents"
DOCS_DIR = ROOT / "docs"
TEMPLATES_DIR = ROOT / "templates"
OUTPUTS_DIR = ROOT / "outputs"
ITER_DIR = OUTPUTS_DIR / "iterations"
ARCHIVE_DIR = OUTPUTS_DIR / "archive"
FINAL_DIR = OUTPUTS_DIR / "final"


def load_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def save_config(cfg):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")


def round_dir(n, create=False):
    d = ITER_DIR / f"round_{n:02d}"
    if create:
        (d / "expert_outputs").mkdir(parents=True, exist_ok=True)
        (d / "critic_outputs").mkdir(parents=True, exist_ok=True)
        (d / "system_state").mkdir(parents=True, exist_ok=True)
    return d


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def read(path):
    return Path(path).read_text(encoding="utf-8")


def write_json(path, obj):
    return write(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_jitter(key, spread=0.4):
    """Deterministic pseudo-noise in [-spread/2, +spread/2] derived from a key.

    Used to give mock judge trials honest, reproducible trial-to-trial
    variation (the key includes the randomized presentation order).
    """
    h = int(hashlib.sha256(key.encode("utf-8")).hexdigest(), 16)
    return ((h % 1000) / 1000.0 - 0.5) * spread
