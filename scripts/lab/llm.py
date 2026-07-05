"""Single LLM harness. Every model call in the lab goes through call_model().

Two provider backends (Anthropic / Google), selected by role:
  generator -> GENERATOR_PROVIDER (default: google)
  judge     -> JUDGE_PROVIDER     (default: anthropic)
The two must differ (verified by verify.py, check 13).

If a provider's key is missing, or its SDK/API fails repeatedly, calls fall
back to the deterministic mock backend built on the curated briefing pack
(lab/knowledge.py). Every call records which backend actually served it, so
the final report can state precisely what was mocked.
"""
import os
import re
import threading
import time

from . import mock_backend
from .util import ROOT, load_config

KEY_VARS = {"anthropic": "ANTHROPIC_API_KEY", "google": "GOOGLE_API_KEY"}

CALL_LOG = []           # {task, agent, role, provider, backend, ms}
_clients = {}
_failures = {"anthropic": 0, "google": 0}
_MAX_FAILURES = 6       # circuit breaker: after this many consecutive HARD
                        # failures a provider degrades to mock for the run
                        # (rate limits do not count — they wait instead)

# Per-provider request spacing: burst-parallel calls trip per-minute quotas
# (observed with Gemini free-tier keys), so calls to the same provider are
# serialized with a minimum interval.
_MIN_INTERVAL = {"google": 6.5, "anthropic": 0.3}
_throttle_lock = {p: threading.Lock() for p in _MIN_INTERVAL}
_last_call = {p: 0.0 for p in _MIN_INTERVAL}
_RATE_RE = re.compile(r"(429|RESOURCE_EXHAUSTED|rate.?limit|quota|overloaded|"
                      r"503|UNAVAILABLE|high demand)", re.I)


def _throttled(provider, fn):
    """Reserve a start slot (spacing requests) without serializing latency."""
    with _throttle_lock[provider]:
        now = time.time()
        start = max(now, _last_call[provider] + _MIN_INTERVAL[provider])
        _last_call[provider] = start
    if start > now:
        time.sleep(start - now)
    return fn()


def load_env():
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


load_env()

# Env overrides pin a provider to ONE model (bypasses the ladder). Resolved
# after .env is loaded. See D-18 (free-tier daily caps) and D-26 (per-task
# cheapest-adequate ladder with escalation).
MODEL_OVERRIDES = {
    "anthropic": os.environ.get("ANTHROPIC_MODEL"),
    "google": os.environ.get("GOOGLE_MODEL"),
}


def resolve_model(provider, task=None, dimension=None, escalation=0):
    """Cheapest-adequate model for a task (D-26).

    Tier comes from config (task_tiers; dimension_tier_overrides may raise it
    for judge_score); each escalation step (validation-failure retry) climbs
    one rung. An env override (ANTHROPIC_MODEL / GOOGLE_MODEL) wins outright.
    """
    if MODEL_OVERRIDES.get(provider):
        return MODEL_OVERRIDES[provider]
    m = load_config().get("models", {})
    ladder = m.get("ladder", {}).get(provider)
    if not ladder:
        return {"anthropic": "claude-opus-4-8",
                "google": "gemini-2.5-flash-lite"}[provider]
    tier = m.get("task_tiers", {}).get(task, len(ladder) - 1)
    if dimension:
        tier = max(tier, m.get("dimension_tier_overrides", {}).get(dimension, 0))
    return ladder[min(tier + max(0, escalation), len(ladder) - 1)]


def provider_for_role(role):
    cfg = load_config()["providers"]
    if role == "generator":
        return os.environ.get("GENERATOR_PROVIDER", cfg["generator_default"])
    if role == "judge":
        return os.environ.get("JUDGE_PROVIDER", cfg["judge_default"])
    raise ValueError(f"unknown role {role!r}")


def provider_available(provider):
    if os.environ.get("LAB_FORCE_MOCK"):
        return False
    if _failures[provider] >= _MAX_FAILURES:
        return False
    return bool(os.environ.get(KEY_VARS[provider]))


def _client(provider):
    if provider in _clients:
        return _clients[provider]
    if provider == "anthropic":
        import anthropic  # lazy: mock path needs no SDKs
        _clients[provider] = anthropic.Anthropic()
    elif provider == "google":
        from google import genai
        _clients[provider] = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    return _clients[provider]


def _call_real(provider, model, prompt, max_tokens):
    if provider == "anthropic":
        resp = _client(provider).messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in resp.content if b.type == "text")
    if provider == "google":
        from google.genai import types
        try:
            cfg = types.GenerateContentConfig(
                temperature=0.2, max_output_tokens=max_tokens,
                thinking_config=types.ThinkingConfig(thinking_budget=0))
        except Exception:  # older SDK without thinking_config
            cfg = types.GenerateContentConfig(
                temperature=0.2, max_output_tokens=max_tokens)
        resp = _client(provider).models.generate_content(
            model=model, contents=prompt, config=cfg)
        return resp.text or ""
    raise ValueError(provider)


def call_model(prompt, role, max_tokens=8000, retries=4, escalation=0,
               dimension=None):
    """The single entry point for every model call in the lab.

    Returns the model's text. The prompt carries a structured header
    (TASK/AGENT/LANG/PROVIDER lines) which real models may ignore but the
    mock backend uses for deterministic composition. `escalation` climbs the
    model ladder (D-26): validation-failure retries pass attempt numbers so
    a cheap model that produced unusable output is replaced by a stronger one.
    """
    provider = provider_for_role(role)
    t0 = time.time()
    entry = {"role": role, "provider": provider, "backend": "mock"}
    for line in prompt.splitlines()[:6]:
        if line.startswith("TASK:"):
            entry["task"] = line[5:].strip()
        if line.startswith("AGENT:"):
            entry["agent"] = line[6:].strip()
    model = resolve_model(provider, task=entry.get("task"),
                          dimension=dimension, escalation=escalation)
    entry["model"] = model

    if provider_available(provider):
        for attempt in range(retries + 1):
            try:
                text = _throttled(provider,
                                  lambda: _call_real(provider, model, prompt,
                                                     max_tokens))
                if not text.strip():
                    raise RuntimeError("empty response")
                _failures[provider] = 0
                entry["backend"] = provider
                entry["ms"] = int((time.time() - t0) * 1000)
                CALL_LOG.append(entry)
                return text
            except Exception as e:  # noqa: BLE001 — any API error degrades
                msg = f"{type(e).__name__}: {e}"
                entry.setdefault("errors", []).append(msg[:200])
                if "PerDay" in msg or "check your plan and billing" in msg:
                    # daily quota exhausted: no point retrying today — degrade
                    # this provider to the deterministic mock for the run
                    _failures[provider] = _MAX_FAILURES
                    break
                if _RATE_RE.search(msg):
                    # per-minute rate limit: wait it out, no breaker penalty
                    time.sleep(min(60, 15 * (attempt + 1)))
                    continue
                _failures[provider] += 1
                if _failures[provider] >= _MAX_FAILURES:
                    break
                time.sleep(2.0 * (attempt + 1))

    text = mock_backend.compose(prompt, role)
    entry["backend"] = "mock"
    entry["ms"] = int((time.time() - t0) * 1000)
    CALL_LOG.append(entry)
    return text


def backend_stats():
    """Summary of which backend/model served which task — final report input."""
    stats = {}
    for e in CALL_LOG:
        label = e["backend"] if e["backend"] == "mock" else \
            f"{e['backend']}:{e.get('model', '?')}"
        key = (e.get("task", "?"), label)
        stats[key] = stats.get(key, 0) + 1
    return {f"{task} [{label}]": n for (task, label), n in sorted(stats.items())}
