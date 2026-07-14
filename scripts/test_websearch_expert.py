#!/usr/bin/env python3
"""
Compare an expert agent WITHOUT web search (memory only) vs WITH web search.
Real Anthropic API, no mocks. Shows whether live retrieval changes the answer.
"""
import os
import sys

import anthropic

MODEL = "claude-sonnet-5"  # supports web_search_20260209 (dynamic filtering)

QUESTION = ("Should Hungary delay or eliminate early academic selection "
            "(6-year and 8-year gimnázium entry at ages 10-12)?")

# The demography expert's role, distilled from agents/experts/demography.md
SYSTEM = (
    "You are the demography expert in a Hungarian education-policy lab. "
    "Your role: cohort decline and its forcing effect on school-network "
    "decisions through 2040.\n"
    "Rules:\n"
    "- Tag every factual claim with [evidence: strong|moderate|weak|contested — source].\n"
    "- Never invent statistics or citations; if you do not know, say so as an "
    "explicit uncertainty.\n"
    "- Keep it under ~250 words. Structure: ## Findings, ## Position, ## Uncertainties."
)

PROMPT = (f"Policy question: {QUESTION}\n\n"
          "Give your demographic analysis. Focus on Hungarian birth-rate trends "
          "and cohort sizes, with specific numbers and years where possible.")


def run(with_search: bool):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    tools = None
    if with_search:
        tools = [{
            "type": "web_search_20260209",
            "name": "web_search",
            "max_uses": 5,
        }]

    messages = [{"role": "user", "content": PROMPT}]
    text_parts = []
    searches = []
    last_usage = None

    # Server-side tool loop can pause (stop_reason == "pause_turn"); resume it.
    for _ in range(6):
        kwargs = dict(model=MODEL, max_tokens=2000, system=SYSTEM,
                      messages=messages)
        if tools:
            kwargs["tools"] = tools
        resp = client.messages.create(**kwargs)
        last_usage = resp.usage

        for block in resp.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "server_tool_use" and block.name == "web_search":
                searches.append(block.input.get("query", "?"))

        if resp.stop_reason == "pause_turn":
            messages = [{"role": "user", "content": PROMPT},
                        {"role": "assistant", "content": resp.content}]
            continue
        break

    return "\n".join(text_parts), searches, last_usage


def main():
    print("=" * 78)
    print(f"EXPERT COMPARISON — model: {MODEL}")
    print("=" * 78)

    print("\n\n########## RUN A: NO WEB SEARCH (memory only) ##########\n")
    text_a, _, usage_a = run(with_search=False)
    print(text_a)
    print(f"\n[tokens: in={usage_a.input_tokens} out={usage_a.output_tokens}]")

    print("\n\n########## RUN B: WITH WEB SEARCH (live retrieval) ##########\n")
    text_b, searches_b, usage_b = run(with_search=True)
    print(f">> Web searches performed ({len(searches_b)}):")
    for q in searches_b:
        print(f"   - {q}")
    print()
    print(text_b)
    print(f"\n[tokens: in={usage_b.input_tokens} out={usage_b.output_tokens}]")

    print("\n\n" + "=" * 78)
    print("COMPARISON SUMMARY")
    print("=" * 78)
    print(f"Run A (memory):     {len(text_a)} chars, no searches")
    print(f"Run B (websearch):  {len(text_b)} chars, {len(searches_b)} live searches")


if __name__ == "__main__":
    main()
