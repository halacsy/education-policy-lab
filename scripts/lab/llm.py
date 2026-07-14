"""Single LLM harness. Every model call in the lab goes through call_model()
(free text) or call_structured() (JSON-schema-constrained output, D-34).

Provider backends (Anthropic / Google / OpenAI), selected by role:
  generator -> GENERATOR_PROVIDER (default: google)
  judge     -> JUDGE_PROVIDER     (default: anthropic)
The two must differ (verified by verify.py, check 13).

Failure policy (D-34): there is NO silent mock fallback. If a provider's key
is missing or its API fails past the retry/breaker budget, StepFailed is
raised — the round stops, the failure is journaled, and a relaunch resumes
from the same step. The deterministic mock backend serves calls only under
LAB_FORCE_MOCK=1 (explicit dry run, e.g. run_mock_sprint.py).
"""
import json
import os
import re
import threading
import time

from . import mock_backend
from .util import ROOT, load_config

KEY_VARS = {"anthropic": "ANTHROPIC_API_KEY", "google": "GOOGLE_API_KEY",
           "openai": "OPENAI_API_KEY"}

CALL_LOG = []           # {task, agent, role, provider, backend, model, ms}
_clients = {}
_failures = {}          # (provider, model) -> consecutive hard-failure count;
                        # daily quotas are PER MODEL, so the breaker is too:
                        # a dead rung is skipped and the ladder climbs on
_MAX_FAILURES = 6

# Per-provider request spacing: burst-parallel calls trip per-minute quotas
# (observed with Gemini free-tier keys), so calls to the same provider are
# serialized with a minimum interval.
_MIN_INTERVAL = {"google": 6.5, "anthropic": 0.3, "openai": 0.5}
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
    # unset (None) by default: no config ladder exists for openai yet (D-33),
    # so resolve_model() falls through to codex's own configured default
    # model — set OPENAI_MODEL to pin one explicitly.
    "openai": os.environ.get("OPENAI_MODEL"),
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
        # openai (D-33) has no configured ladder: "" (falsy, but NOT None —
        # call_model()'s `model is not None` guard means to distinguish "no
        # live model available" from "no override needed") means omit -m
        # and let codex use its account's own default model.
        return {"anthropic": "claude-opus-4-8",
                "google": "gemini-2.5-flash-lite"}.get(provider, "")
    tier = m.get("task_tiers", {}).get(task, len(ladder) - 1)
    if dimension:
        tier = max(tier, m.get("dimension_tier_overrides", {}).get(dimension, 0))
    return ladder[min(tier + max(0, escalation), len(ladder) - 1)]


class StepFailed(RuntimeError):
    """A pipeline step could not be served by any live backend (or its
    output failed validation past the retry budget). Replaces the old
    silent mock fallback (D-34): callers let it propagate, the iteration
    loop stops, and a relaunch resumes from the failed step."""


def _gemini_schema(schema):
    """Gemini's OpenAPI-subset schema language rejects additionalProperties
    (it is implicitly false there) — strip it recursively, keep the rest."""
    if isinstance(schema, dict):
        return {k: _gemini_schema(v) for k, v in schema.items()
                if k != "additionalProperties"}
    if isinstance(schema, list):
        return [_gemini_schema(v) for v in schema]
    return schema


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
    elif provider == "openai":
        import openai
        _clients[provider] = openai.OpenAI()
    return _clients[provider]


def _cli_backend(provider):
    """CLI backends (issue #7): subscription/free-tier compute instead of API
    keys. ANTHROPIC_BACKEND=claude-code -> `claude -p` (subscription quota);
    GOOGLE_BACKEND=gemini-cli -> `gemini` (API-key auth);
    GOOGLE_BACKEND=agy -> Antigravity CLI (Google-account quota);
    OPENAI_BACKEND=codex -> `codex exec` (ChatGPT subscription quota, D-33)."""
    return os.environ.get({"anthropic": "ANTHROPIC_BACKEND",
                           "google": "GOOGLE_BACKEND",
                           "openai": "OPENAI_BACKEND"}[provider], "")


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
    import tempfile
    env = dict(os.environ)
    output_file = None
    # isolated empty cwd: an agentic CLI must not read or write the repo
    with tempfile.TemporaryDirectory(prefix="lab-cli-") as tmpdir:
        if provider == "anthropic":
            # strip the API key so the CLI bills the subscription, not the key
            env.pop("ANTHROPIC_API_KEY", None)
            cmd = ["claude", "-p", "--model", model]
        elif provider == "openai":
            # Codex CLI (D-33): ChatGPT-subscription quota. `codex exec` has
            # no -a/--ask-for-approval of its own (that's an interactive-CLI
            # flag); -s read-only keeps it a pure text-generation call (no
            # filesystem writes from model-invoked commands, so nothing ever
            # needs an approval prompt). -o writes ONLY the agent's final
            # message, avoiding TUI/log noise in stdout. --skip-git-repo-check:
            # the isolated tmpdir is deliberately not a git repo.
            env.pop("OPENAI_API_KEY", None)
            output_file = os.path.join(tmpdir, "codex_output.txt")
            directive = ("IMPORTANT: You are used as a text-generation "
                        "backend. Print your COMPLETE answer directly as "
                        "your response text. Do NOT explore the filesystem, "
                        "do NOT run shell commands, do NOT create or edit "
                        "any files. Do NOT summarize what you did — output "
                        "only the requested document itself.\n\n")
            cmd = ["codex", "exec"] + (["-m", model] if model else []) + [
                "-s", "read-only", "--skip-git-repo-check", "-o", output_file]
            prompt = directive + prompt
        elif _cli_backend(provider) == "agy":
            # Antigravity CLI: prompt must be an argv argument (no stdin mode).
            # agy is an agent — without the directive below it writes its
            # answer to a workspace file instead of printing it.
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
        r = subprocess.run(cmd, input=stdin_text, capture_output=True,
                           text=True, timeout=600, env=env, cwd=tmpdir)
        if r.returncode != 0:
            raise RuntimeError(f"{cmd[0]} CLI failed: {r.stderr.strip()[:300]}")
        if output_file is not None:
            with open(output_file, encoding="utf-8") as f:
                return f.read().strip()
        return r.stdout.strip()


def web_search_supported(role="generator"):
    """The server-side web-search tool (P4/D-34) is implemented for the
    Anthropic API backend only; the mock path serves it deterministically."""
    if os.environ.get("LAB_FORCE_MOCK"):
        return True
    return provider_for_role(role) == "anthropic" and \
        not _cli_backend("anthropic")


def _call_search(provider, model, prompt, max_tokens, max_uses):
    """Free-text call with the server-side web-search tool. The server-side
    tool loop can pause (stop_reason == "pause_turn"); resume it. Adaptive
    thinking stays ON for this call — with thinking disabled the model is
    much less likely to actually search."""
    tools = [{"type": "web_search_20260209", "name": "web_search",
              "max_uses": max_uses}]
    messages = [{"role": "user", "content": prompt}]
    parts = []
    usage = {"input_tokens": 0, "output_tokens": 0}
    for _ in range(6):
        resp = _client(provider).messages.create(
            model=model, max_tokens=max_tokens, tools=tools,
            messages=messages)
        usage["input_tokens"] += resp.usage.input_tokens
        usage["output_tokens"] += resp.usage.output_tokens
        parts += [b.text for b in resp.content if b.type == "text"]
        if resp.stop_reason == "pause_turn":
            messages = [{"role": "user", "content": prompt},
                        {"role": "assistant", "content": resp.content}]
            continue
        break
    return "\n".join(parts), usage


def _call_real(provider, model, prompt, max_tokens, schema=None,
               web_search=False):
    """Returns (text, usage). usage is {"input_tokens", "output_tokens"} when
    the backend reports it (API backends do; CLI/subscription backends
    don't meter per-call, so usage is None for those). With `schema`, the
    response is constrained to that JSON schema (API backends only).
    `web_search` and `schema` are never combined (two-phase expert call)."""
    if _cli_backend(provider):
        if schema is not None or web_search:
            raise StepFailed(
                f"structured output / web search needs the {provider} API "
                f"backend; the {_cli_backend(provider)!r} CLI cannot serve "
                "it — unset the *_BACKEND env var for this role and set "
                f"{KEY_VARS[provider]}")
        return _call_cli(provider, model, prompt, max_tokens), None
    if web_search:
        if provider != "anthropic":
            raise StepFailed(
                "web search (P4) is implemented for the anthropic provider "
                "only — set GENERATOR_PROVIDER=anthropic or disable "
                "research.web_search")
        return _call_search(provider, model, prompt, max_tokens,
                            max_uses=5)
    if provider == "anthropic":
        # Extended thinking (when the model/account defaults it on) counts
        # against max_tokens — on a long input (e.g. the 10-voice digest)
        # the model can burn the ENTIRE budget on thinking and hit
        # stop_reason=max_tokens with zero actual text, silently failing
        # every call for this task. Every call here wants a clean,
        # deterministic, directly-parseable answer (prose or JSON), never
        # visible chain-of-thought, so thinking is explicitly off.
        kwargs = {}
        if schema is not None:
            kwargs["output_config"] = {
                "format": {"type": "json_schema", "schema": schema}}
        req = dict(
            model=model,
            max_tokens=max_tokens,
            thinking={"type": "disabled"},
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        if max_tokens > 8192:
            # large outputs (bilingual scenarios/brief) must stream — the
            # SDK refuses long non-streaming requests to avoid HTTP timeouts
            with _client(provider).messages.stream(**req) as st:
                resp = st.get_final_message()
        else:
            resp = _client(provider).messages.create(**req)
        if schema is not None and resp.stop_reason == "max_tokens":
            # truncated JSON can never validate — retrying at the same
            # budget reproduces it, so fail loudly instead
            raise StepFailed(
                f"structured output truncated at max_tokens={max_tokens} — "
                "raise this step's token budget")
        text = "".join(b.text for b in resp.content if b.type == "text")
        usage = dict(input_tokens=resp.usage.input_tokens,
                     output_tokens=resp.usage.output_tokens)
        return text, usage
    if provider == "google":
        from google.genai import types
        extra = {}
        if schema is not None:
            extra = dict(response_mime_type="application/json",
                         response_schema=_gemini_schema(schema))
        try:
            cfg = types.GenerateContentConfig(
                temperature=0.2, max_output_tokens=max_tokens,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
                **extra)
        except Exception:  # older SDK without thinking_config
            cfg = types.GenerateContentConfig(
                temperature=0.2, max_output_tokens=max_tokens, **extra)
        resp = _client(provider).models.generate_content(
            model=model, contents=prompt, config=cfg)
        usage = None
        um = getattr(resp, "usage_metadata", None)
        if um is not None:
            usage = dict(
                input_tokens=getattr(um, "prompt_token_count", None),
                output_tokens=getattr(um, "candidates_token_count", None))
        return resp.text or "", usage
    if provider == "openai":
        # OpenAI API judge path (owner decision 2026-07-14: the OpenAI key
        # has more headroom than the Gemini free tier). Structured output
        # via chat.completions response_format json_schema strict — the
        # lab's schemas already satisfy strict mode (additionalProperties
        # false + all-required everywhere; $defs supported).
        kwargs = {}
        if schema is not None:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "artifact", "strict": True,
                                "schema": schema}}
        resp = _client(provider).chat.completions.create(
            model=model or "gpt-5-mini",
            max_completion_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            **kwargs)
        choice = resp.choices[0]
        if schema is not None and choice.finish_reason == "length":
            raise StepFailed(
                f"structured output truncated at max_tokens={max_tokens} — "
                "raise this step's token budget")
        usage = None
        if resp.usage is not None:
            usage = dict(input_tokens=resp.usage.prompt_tokens,
                         output_tokens=resp.usage.completion_tokens)
        return choice.message.content or "", usage
    raise ValueError(provider)


def call_model(prompt, role, max_tokens=8000, retries=4, escalation=0,
               dimension=None, schema=None, web_search=False):
    """The single entry point for every model call in the lab.

    Returns the model's text. The prompt carries a structured header
    (TASK/AGENT/LANG/PROVIDER lines) which real models may ignore but the
    mock backend uses for deterministic composition. `escalation` climbs the
    model ladder (D-26): validation-failure retries pass attempt numbers so
    a cheap model that produced unusable output is replaced by a stronger one.
    With `schema`, the response is constrained to that JSON schema (D-34;
    API backends only — prefer call_structured(), which also parses).

    Failure policy (D-34): NO silent mock fallback. Missing credentials,
    a fully breaker-tripped ladder, or retry exhaustion raise StepFailed.
    The mock backend serves only under LAB_FORCE_MOCK=1 (explicit dry run).
    """
    provider = provider_for_role(role)
    t0 = time.time()
    entry = {"role": role, "provider": provider, "backend": "mock"}
    for line in prompt.splitlines()[:6]:
        if line.startswith("TASK:"):
            entry["task"] = line[5:].strip()
        if line.startswith("AGENT:"):
            entry["agent"] = line[6:].strip()

    if os.environ.get("LAB_FORCE_MOCK"):
        text = mock_backend.compose(prompt, role)
        entry["model"] = None
        entry["ms"] = int((time.time() - t0) * 1000)
        CALL_LOG.append(entry)
        return text

    if not provider_available(provider):
        raise StepFailed(
            f"provider {provider!r} (role {role}) has no credentials or CLI "
            f"backend configured — set {KEY_VARS[provider]} or the "
            "*_BACKEND env var")

    model = _pick_live_model(provider, entry.get("task"), dimension, escalation)
    entry["model"] = model
    if model is None:
        raise StepFailed(
            f"every {provider} ladder rung is breaker-tripped (daily quotas "
            "exhausted?) — relaunch after the quota resets; the run resumes")

    for attempt in range(retries + 1):
        try:
            text, usage = _throttled(provider,
                                     lambda: _call_real(provider, model, prompt,
                                                        max_tokens, schema,
                                                        web_search))
            if not text.strip():
                raise RuntimeError("empty response")
            _failures[(provider, model)] = 0
            entry["backend"] = provider + (
                f"({_cli_backend(provider)})" if _cli_backend(provider) else "")
            entry["ms"] = int((time.time() - t0) * 1000)
            if usage:
                entry["input_tokens"] = usage.get("input_tokens")
                entry["output_tokens"] = usage.get("output_tokens")
            CALL_LOG.append(entry)
            return text
        except StepFailed:
            raise  # terminal by design (config error, truncation, ...)
        except Exception as e:  # noqa: BLE001 — any API error is retryable
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

    CALL_LOG.append({**entry, "backend": "failed",
                     "ms": int((time.time() - t0) * 1000)})
    raise StepFailed(
        f"{provider} call failed past the retry budget for task "
        f"{entry.get('task', '?')!r}; last errors: "
        f"{entry.get('errors', ['?'])[-2:]}")


def call_structured(prompt, schema, role, max_tokens=8000, retries=4,
                    escalation=0, dimension=None):
    """call_model() with a JSON-schema-constrained response (D-34); returns
    the parsed object. Requires an API backend — constrained decoding
    guarantees schema-valid JSON, so a parse failure here means truncation
    (already raised as StepFailed) or a mock without a structured composer."""
    text = call_model(prompt, role, max_tokens=max_tokens, retries=retries,
                      escalation=escalation, dimension=dimension,
                      schema=schema)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise StepFailed(
            f"structured call returned unparseable JSON ({e}) — under "
            "LAB_FORCE_MOCK this means the mock backend has no structured "
            "composer for this task yet") from e


def backend_stats():
    """Summary of which backend/model served which task — final report input."""
    stats = {}
    for e in CALL_LOG:
        label = e["backend"] if e["backend"] == "mock" else \
            f"{e['backend']}:{e.get('model', '?')}"
        key = (e.get("task", "?"), label)
        stats[key] = stats.get(key, 0) + 1
    return {f"{task} [{label}]": n for (task, label), n in sorted(stats.items())}


def call_log_len():
    """Marker for since= slicing (per-round token attribution, D-35)."""
    return len(CALL_LOG)


def token_stats(since=0):
    """Input/output token totals per (task, backend) and a grand total —
    API backends report usage per call; CLI/subscription backends don't
    meter per call, so their calls are counted but contribute no tokens.
    since= restricts the aggregation to calls made after that CALL_LOG
    marker (llm.call_log_len()) — per-round attribution in a multi-round
    process."""
    per_key = {}
    total_in = total_out = 0
    metered_calls = 0
    for e in CALL_LOG[since:]:
        if e.get("input_tokens") is None and e.get("output_tokens") is None:
            continue
        label = e["backend"] if e["backend"] == "mock" else \
            f"{e['backend']}:{e.get('model', '?')}"
        key = (e.get("task", "?"), label)
        i, o = e.get("input_tokens") or 0, e.get("output_tokens") or 0
        cur = per_key.setdefault(key, {"input_tokens": 0, "output_tokens": 0})
        cur["input_tokens"] += i
        cur["output_tokens"] += o
        total_in += i
        total_out += o
        metered_calls += 1
    return {
        "by_task_backend": {f"{task} [{label}]": v
                            for (task, label), v in sorted(per_key.items())},
        "total_input_tokens": total_in,
        "total_output_tokens": total_out,
        "total_tokens": total_in + total_out,
        "metered_calls": metered_calls,
        "unmetered_calls": len(CALL_LOG[since:]) - metered_calls,
    }


def error_stats():
    """Captured error messages per (task, final backend) — surfaces WHY a
    step needed to retry/escalate/fall back, not just that it did (issue
    #17). Errors accumulate on `entry` across every live attempt inside one
    call_model() invocation, so they're attributed to whatever backend that
    invocation ultimately landed on (a live model, or mock)."""
    out = {}
    for e in CALL_LOG:
        errs = e.get("errors")
        if not errs:
            continue
        label = e["backend"] if e["backend"] == "mock" else \
            f"{e['backend']}:{e.get('model', '?')}"
        key = f"{e.get('task', '?')} [{label}]"
        out.setdefault(key, []).extend(errs)
    return out
