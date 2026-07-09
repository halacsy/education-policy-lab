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

CALL_LOG = []           # {task, agent, role, provider, backend, model, ms}
_clients = {}
_failures = {}          # (provider, model) -> consecutive hard-failure count;
                        # daily quotas are PER MODEL, so the breaker is too:
                        # a dead rung is skipped and the ladder climbs on
_MAX_FAILURES = 6

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
    if _cli_backend(provider):
        return True  # CLI backends authenticate via their own login
    return bool(os.environ.get(KEY_VARS[provider]))


def _model_dead(provider, model):
    return _failures.get((provider, model), 0) >= _MAX_FAILURES


def _pick_live_model(provider, task, dimension, escalation):
    """Resolve the cheapest adequate rung, skipping breaker-tripped models
    by climbing the ladder; None if every candidate rung is dead."""
    seen = []
    for bump in range(8):
        m = resolve_model(provider, task=task, dimension=dimension,
                          escalation=escalation + bump)
        if m in seen:
            break
        seen.append(m)
        if not _model_dead(provider, m):
            return m
    return None


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


def _cli_backend(provider):
    """CLI backends (issue #7): subscription/free-tier compute instead of API
    keys. ANTHROPIC_BACKEND=claude-code -> `claude -p` (subscription quota);
    GOOGLE_BACKEND=gemini-cli -> `gemini` (API-key auth);
    GOOGLE_BACKEND=agy -> Antigravity CLI (Google-account quota)."""
    return os.environ.get({"anthropic": "ANTHROPIC_BACKEND",
                           "google": "GOOGLE_BACKEND"}[provider], "")


# D-26 ladder ids -> Antigravity model names (Gemini only: the agy backend
# serves the GOOGLE provider side, and cross-family (check 13) must hold even
# though Antigravity could also serve Claude models.
AGY_MODEL_MAP = {
    "gemini-2.5-flash-lite": "Gemini 3.5 Flash (Low)",
    "gemini-2.5-flash": "Gemini 3.5 Flash (High)",
    "gemini-2.5-pro": "Gemini 3.1 Pro (High)",
}


def _call_cli(provider, model, prompt, max_tokens):
    import subprocess
    env = dict(os.environ)
    if provider == "anthropic":
        # strip the API key so the CLI bills the subscription, not the key
        env.pop("ANTHROPIC_API_KEY", None)
        cmd = ["claude", "-p", "--model", model]
    elif _cli_backend(provider) == "agy":
        # Antigravity CLI: prompt must be an argv argument (no stdin mode).
        # agy is an agent — without the directive below it writes its answer
        # to a workspace file instead of printing it.
        agy_model = AGY_MODEL_MAP.get(model, "Gemini 3.5 Flash (Low)")
        directive = ("IMPORTANT: You are used as a text-generation backend. "
                     "Print your COMPLETE answer directly as your response "
                     "text. Do NOT create, write or edit any files. Do NOT "
                     "use any tools. Do NOT summarize what you did — output "
                     "only the requested document itself.\n\n")
        cmd = ["agy", "-p", directive + prompt, "--model", agy_model,
               "--print-timeout", "9m"]
    else:
        # strip API keys so the CLI uses its own configured auth
        env.pop("GOOGLE_API_KEY", None)
        env.pop("GEMINI_API_KEY", None)
        env["GEMINI_CLI_TRUST_WORKSPACE"] = "true"
        # headless mode reads the prompt from stdin when it is not a TTY;
        # passing it as the -p argument would hit argv size limits
        cmd = ["gemini", "-m", model]
    env["PATH"] = (os.path.expanduser("~/.local/bin") + os.pathsep
                   + os.path.expanduser("~/.antigravity/antigravity/bin")
                   + os.pathsep + env.get("PATH", ""))
    stdin_text = None if cmd[0] == "agy" else prompt
    # isolated empty cwd: an agentic CLI must not read or write the repo
    import tempfile
    with tempfile.TemporaryDirectory(prefix="lab-cli-") as tmpdir:
        r = subprocess.run(cmd, input=stdin_text, capture_output=True,
                           text=True, timeout=600, env=env, cwd=tmpdir)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd[0]} CLI failed: {r.stderr.strip()[:300]}")
    return r.stdout.strip()


def _call_real(provider, model, prompt, max_tokens):
    """-> (text, usage) where usage = {tokens_in, tokens_out, estimated}.
    API backends report exact counts; CLI backends don't expose usage, so
    counts are chars/4 estimates and flagged as such."""
    if _cli_backend(provider):
        text = _call_cli(provider, model, prompt, max_tokens)
        return text, {"tokens_in": len(prompt) // 4,
                      "tokens_out": len(text) // 4, "estimated": True}
    if provider == "anthropic":
        resp = _client(provider).messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        return text, {"tokens_in": resp.usage.input_tokens,
                      "tokens_out": resp.usage.output_tokens,
                      "estimated": False}
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
        text = resp.text or ""
        um = getattr(resp, "usage_metadata", None)
        if um is not None:
            usage = {"tokens_in": um.prompt_token_count or 0,
                     "tokens_out": (um.candidates_token_count or 0)
                     + (getattr(um, "thoughts_token_count", 0) or 0),
                     "estimated": False}
        else:
            usage = {"tokens_in": len(prompt) // 4,
                     "tokens_out": len(text) // 4, "estimated": True}
        return text, usage
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
    model = _pick_live_model(provider, entry.get("task"), dimension, escalation)
    entry["model"] = model

    if provider_available(provider) and model is not None:
        for attempt in range(retries + 1):
            try:
                text, usage = _throttled(
                    provider, lambda: _call_real(provider, model, prompt,
                                                 max_tokens))
                if not text.strip():
                    raise RuntimeError("empty response")
                _failures[(provider, model)] = 0
                entry["backend"] = provider + (
                    f"({_cli_backend(provider)})" if _cli_backend(provider) else "")
                entry["ms"] = int((time.time() - t0) * 1000)
                entry.update(usage)
                CALL_LOG.append(entry)
                return text
            except Exception as e:  # noqa: BLE001 — any API error degrades
                msg = f"{type(e).__name__}: {e}"
                entry.setdefault("errors", []).append(msg[:200])
                if "PerDay" in msg or "check your plan and billing" in msg:
                    # daily quota exhausted for THIS model — kill the rung
                    # and climb to the next live one (D-27)
                    _failures[(provider, model)] = _MAX_FAILURES
                    model = _pick_live_model(provider, entry.get("task"),
                                             dimension, escalation)
                    entry["model"] = model
                    if model is None:
                        break
                    continue
                if _RATE_RE.search(msg):
                    # per-minute rate limit: wait it out, no breaker penalty
                    time.sleep(min(60, 15 * (attempt + 1)))
                    continue
                _failures[(provider, model)] = \
                    _failures.get((provider, model), 0) + 1
                if _model_dead(provider, model):
                    break
                time.sleep(2.0 * (attempt + 1))

    text = mock_backend.compose(prompt, role)
    entry["backend"] = "mock"
    entry["ms"] = int((time.time() - t0) * 1000)
    entry.update({"tokens_in": len(prompt) // 4,
                  "tokens_out": len(text) // 4, "estimated": True})
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


def token_stats(since=0):
    """Token/time accounting over CALL_LOG[since:] — a full-run cost report.

    Per (backend, model): calls, tokens in/out, wall-clock ms; totals per
    provider and overall. Counts from API backends are exact; CLI/mock
    entries are chars/4 estimates and reported separately ('estimated').
    Pass `since` (a CALL_LOG index captured at round start) for per-round
    deltas."""
    per = {}
    for e in CALL_LOG[since:]:
        key = f"{e['backend']}:{e.get('model') or '-'}"
        d = per.setdefault(key, {"calls": 0, "tokens_in": 0, "tokens_out": 0,
                                 "ms": 0, "estimated": 0})
        d["calls"] += 1
        d["tokens_in"] += e.get("tokens_in", 0)
        d["tokens_out"] += e.get("tokens_out", 0)
        d["ms"] += e.get("ms", 0)
        d["estimated"] += 1 if e.get("estimated") else 0
    total = {"calls": sum(d["calls"] for d in per.values()),
             "tokens_in": sum(d["tokens_in"] for d in per.values()),
             "tokens_out": sum(d["tokens_out"] for d in per.values()),
             "ms": sum(d["ms"] for d in per.values()),
             "estimated_calls": sum(d["estimated"] for d in per.values())}
    return {"per_model": dict(sorted(per.items())), "total": total}
