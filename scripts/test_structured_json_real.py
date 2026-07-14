#!/usr/bin/env python3
"""
Real Anthropic API test with structured JSON output (bilingual expert).
No mocks, no pipeline harness — direct API call with response_format.
"""
import json
import os
from pathlib import Path

import anthropic

GLOSSARY = (Path(__file__).parent.parent / "topics" / "korai-szelekcio" / "glossary.md").read_text()

# Structured output schema
EXPERT_SCHEMA = {
    "name": "ExpertAnalysis",
    "description": "Bilingual expert analysis (English and Hungarian)",
    "schema": {
        "type": "object",
        "properties": {
            "expert_name": {
                "type": "string",
                "description": "Expert role (e.g., 'demography')"
            },
            "en": {
                "type": "object",
                "properties": {
                    "findings": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Factual findings with [evidence: status — source]"
                    },
                    "interpretation": {
                        "type": "string",
                        "description": "Interpretation of findings"
                    },
                    "assumptions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Unstated assumptions"
                    },
                    "position": {
                        "type": "string",
                        "description": "One-sentence position statement"
                    },
                    "uncertainties": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Known unknowns with (confidence: level; would be reduced by: ...)"
                    }
                },
                "required": ["findings", "interpretation", "assumptions", "position", "uncertainties"],
                "additionalProperties": False
            },
            "hu": {
                "type": "object",
                "properties": {
                    "findings": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Hungarian findings with [bizonyíték: status — forrás]"
                    },
                    "interpretation": {
                        "type": "string",
                        "description": "Értelmezés"
                    },
                    "assumptions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Feltevések"
                    },
                    "position": {
                        "type": "string",
                        "description": "Egy mondatos álláspontom"
                    },
                    "uncertainties": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Bizonytalanságok (megbízhatóság: level; csökkentené: ...)"
                    }
                },
                "required": ["findings", "interpretation", "assumptions", "position", "uncertainties"],
                "additionalProperties": False
            }
        },
        "required": ["expert_name", "en", "hu"],
        "additionalProperties": False
    }
}

def test_structured_expert():
    """Call Anthropic API with structured JSON output (bilingual)."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    question = "Should Hungary delay or eliminate early academic selection (age 6/8/10 year gimnazium entry)?"

    prompt = f"""You are the demography expert for Hungarian education policy analysis.

Policy question: {question}

Provide your expert analysis in BOTH English and Hungarian. Structure your response
as the JSON schema requires — each language must have all five fields.

GLOSSARY (for consistent terminology):
{GLOSSARY}

REQUIREMENTS:
- Findings: Factual claims with [evidence: strong|moderate|weak|contested — source] tags
- Hungarian findings: [bizonyíték: erős|mérsékelt|gyenge|vitatott — forrás]
- Position: Exactly one sentence
- Uncertainties: List unknowns with (confidence: low|medium|high; would be reduced by: ...)
- Hungarian uncertainties: (megbízhatóság: alacsony|közepes|magas; csökkentené: ...)

Return valid JSON matching the schema."""

    print("=" * 80)
    print("STRUCTURED JSON EXPERT TEST (Real Anthropic API, No Mock)")
    print("=" * 80)
    print(f"\nPolicy question: {question}\n")
    print(f"Using model: claude-haiku-4-5")
    print(f"Response format: JSON Schema (structured output enforced)\n")

    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=8000,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": EXPERT_SCHEMA["schema"],
                }
            }
        )

        # output_config.format guarantees the first text block is valid JSON
        text = next(b.text for b in response.content if b.type == "text")
        output = json.loads(text)

        print("✅ STRUCTURED JSON RECEIVED!\n")

        # Validate structure
        expert_name = output.get("expert_name", "unknown")
        print(f"Expert: {expert_name}\n")

        en = output.get("en", {})
        hu = output.get("hu", {})

        print("=" * 80)
        print("ENGLISH ANALYSIS")
        print("=" * 80)
        print(f"\nFindings ({len(en.get('findings', []))} items):")
        for f in en.get("findings", [])[:2]:
            print(f"  - {f[:80]}...")

        print(f"\nInterpretation:")
        print(f"  {en.get('interpretation', 'N/A')[:150]}...")

        print(f"\nPosition:")
        print(f"  {en.get('position', 'N/A')}")

        print("\n" + "=" * 80)
        print("HUNGARIAN ANALYSIS (MAGYAR ELEMZÉS)")
        print("=" * 80)
        print(f"\nMegállapítások ({len(hu.get('findings', []))} item):")
        for f in hu.get("findings", [])[:2]:
            print(f"  - {f[:80]}...")

        print(f"\nÉrtelmezés:")
        print(f"  {hu.get('interpretation', 'N/A')[:150]}...")

        print(f"\nÁlláspontom:")
        print(f"  {hu.get('position', 'N/A')}")

        print("\n" + "=" * 80)
        print("VALIDATION")
        print("=" * 80)

        # Check completeness
        en_complete = all(k in en for k in ["findings", "interpretation", "assumptions", "position", "uncertainties"])
        hu_complete = all(k in hu for k in ["findings", "interpretation", "assumptions", "position", "uncertainties"])

        print(f"✓ English fields complete: {en_complete}")
        print(f"✓ Hungarian fields complete: {hu_complete}")
        print(f"✓ English findings count: {len(en.get('findings', []))}")
        print(f"✓ Hungarian findings count: {len(hu.get('findings', []))}")

        if en_complete and hu_complete:
            print("\n✅ BILINGUAL JSON STRUCTURE WORKS!")
            print("   Both languages guaranteed by schema validation.")

            # Save output
            output_file = Path("/tmp/structured_expert_bilingual.json")
            output_file.write_text(json.dumps(output, indent=2, ensure_ascii=False))
            print(f"\nFull output saved: {output_file}")

            return True
        else:
            print("\n❌ Structure incomplete")
            return False

    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON response: {e}")
        return False
    except anthropic.APIError as e:
        print(f"❌ API Error: {e}")
        return False

if __name__ == "__main__":
    import sys
    result = test_structured_expert()
    sys.exit(0 if result else 1)
