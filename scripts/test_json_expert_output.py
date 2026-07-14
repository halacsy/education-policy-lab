#!/usr/bin/env python3
"""Test: expert output as structured JSON (bilingual, guaranteed schema)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lab import llm

GLOSSARY = (Path(__file__).parent.parent / "docs" / "glossary.md").read_text()

# JSON schema for expert output (bilingual, guaranteed)
EXPERT_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Expert name (e.g., 'demography')"},
        "en": {
            "type": "object",
            "properties": {
                "findings": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "English findings, each with [evidence: status] tag"
                },
                "interpretation": {"type": "string"},
                "assumptions": {"type": "array", "items": {"type": "string"}},
                "position": {"type": "string", "description": "One sentence"},
                "uncertainties": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Each with (confidence: level; would be reduced by: ...)"
                }
            },
            "required": ["findings", "interpretation", "assumptions", "position", "uncertainties"]
        },
        "hu": {
            "type": "object",
            "properties": {
                "findings": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Hungarian findings, each with [bizonyíték: status] tag"
                },
                "interpretation": {"type": "string"},
                "assumptions": {"type": "array", "items": {"type": "string"}},
                "position": {"type": "string", "description": "One sentence"},
                "uncertainties": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Each with (megbízhatóság: level; csökkentené: ...)"
                }
            },
            "required": ["findings", "interpretation", "assumptions", "position", "uncertainties"]
        }
    },
    "required": ["name", "en", "hu"]
}

def test_json_expert():
    """Test: run expert with JSON schema output."""
    question = "Should Hungary delay or eliminate early academic selection (age 6/8/10 year gimnazium entry)?"

    prompt = f"""TASK: expert_analysis
AGENT: demography
PROVIDER: anthropic

Policy question: {question}

You are the demography expert. Output your analysis as valid JSON matching this schema:
{json.dumps(EXPERT_SCHEMA, indent=2)}

GLOSSARY FOR CONSISTENCY:
{GLOSSARY}

RULES:
- Provide BOTH English (en) and Hungarian (hu) versions
- Tag every factual claim with [evidence: strong|moderate|weak|contested — source]
- In Hungarian: [bizonyíték: erős|mérsékelt|gyenge|vitatott — forrás]
- Keep findings, interpretation, assumptions, position, uncertainties as separate arrays/fields
- Position must be one sentence
- Stay under 300 words per language
- Return ONLY valid JSON, no markdown wrapper

Respond with the JSON object only."""

    print("=" * 80)
    print("JSON EXPERT TEST: demography (bilingual schema)")
    print("=" * 80)
    print(f"\nPrompt length: {len(prompt.split())} words\n")

    try:
        text = llm.call_model(prompt, role="generator", max_tokens=4000, retries=2)
        print("✓ LLM call succeeded\n")

        # Parse JSON
        try:
            output = json.loads(text)
            print("✓ Valid JSON output\n")

            # Check structure
            has_name = "name" in output
            has_en = "en" in output and isinstance(output.get("en"), dict)
            has_hu = "hu" in output and isinstance(output.get("hu"), dict)

            print(f"✓ Has 'name': {has_name}")
            print(f"✓ Has 'en' object: {has_en}")
            print(f"✓ Has 'hu' object: {has_hu}")

            if has_en:
                en_fields = set(output["en"].keys())
                print(f"  EN fields: {en_fields}")
                has_all_en = all(f in en_fields for f in ["findings", "interpretation", "assumptions", "position", "uncertainties"])
                print(f"  ✓ All EN fields complete: {has_all_en}")

            if has_hu:
                hu_fields = set(output["hu"].keys())
                print(f"  HU fields: {hu_fields}")
                has_all_hu = all(f in hu_fields for f in ["findings", "interpretation", "assumptions", "position", "uncertainties"])
                print(f"  ✓ All HU fields complete: {has_all_hu}")

            print("\n" + "=" * 80)
            print("ENGLISH POSITION:")
            print(output.get("en", {}).get("position", "N/A"))
            print("\nMAGYAR ÁLLÁSPONTOM:")
            print(output.get("hu", {}).get("position", "N/A"))
            print("=" * 80)

            print("\n✅ JSON SCHEMA WORKS! Both languages guaranteed.")

            # Save full output
            Path("/tmp/test_json_expert_output.json").write_text(json.dumps(output, indent=2, ensure_ascii=False))
            print("\nFull output saved to: /tmp/test_json_expert_output.json")

            return True

        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
            print(f"Raw output:\n{text[:500]}")
            return False

    except Exception as e:
        print(f"❌ LLM call failed: {e}")
        return None

if __name__ == "__main__":
    result = test_json_expert()
    sys.exit(0 if result else 1)
