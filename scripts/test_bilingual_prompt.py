#!/usr/bin/env python3
"""Quick test: single bilingual expert call against real LLM (if keys available)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lab import agents, llm, util

GLOSSARY = (Path(__file__).parent.parent / "docs" / "glossary.md").read_text()

def test_bilingual_expert():
    """Test: run demography expert with bilingual instruction."""
    question = "Should Hungary delay or eliminate early academic selection (age 6/8/10 year gimnazium entry)?"

    prompt = agents.build_prompt(
        task="expert_analysis",
        provider="anthropic",
        round_n=0,
        agent="demography",
        payload_json='{"expert": "demography"}',
        instructions=(
            f"Policy question: {question}\n"
            "Output BOTH English and Hungarian analysis.\n\n"
            "English sections: ## Findings (evidence), ## Interpretation, "
            "## Assumptions, ## Position, ## Uncertainties\n"
            "Hungarian sections (same content, Hungarian labels): ## Megállapítások, "
            "## Értelmezés, ## Feltevések, ## Álláspontom, ## Bizonytalanságok\n\n"
            "Use this glossary for consistency:\n" + GLOSSARY + "\n\n"
            "Write your analysis following your Output template. "
            "Each finding must have an inline [evidence: ...] tag and source."
        ),
        inputs="(No prior expert inputs for this test; generate independently based on your knowledge of Hungarian demography and education policy.)"
    )

    print("=" * 70)
    print("BILINGUAL EXPERT TEST: demography")
    print("=" * 70)
    print("\nPrompt length:", len(prompt.split()), "words")

    try:
        text = llm.call_model(prompt, role="generator", max_tokens=4000, retries=2)
        print("\n✓ LLM call succeeded\n")
        print("OUTPUT (first 1500 chars):\n")
        print(text[:1500])
        print("\n...")
        print("\nFull output saved to: /tmp/test_bilingual_output.txt")
        Path("/tmp/test_bilingual_output.txt").write_text(text)

        # Check: has Hungarian?
        has_hu_headers = any(h in text for h in ["## Megállapítások", "## Értelmezés", "## Feltevések", "## Álláspontom"])
        has_en_headers = any(h in text for h in ["## Findings", "## Interpretation", "## Assumptions", "## Position"])

        print(f"\n✓ English sections found: {has_en_headers}")
        print(f"✓ Hungarian sections found: {has_hu_headers}")

        if has_hu_headers and has_en_headers:
            print("\n✅ BILINGUAL PROMPT WORKS!")
            return True
        else:
            print("\n❌ Bilingual prompt produced only partial output")
            return False

    except Exception as e:
        print(f"\n❌ LLM call failed: {e}")
        print("(This is expected if API keys are not available or provider is mock-only)")
        return None

if __name__ == "__main__":
    result = test_bilingual_expert()
    sys.exit(0 if result else 1)
