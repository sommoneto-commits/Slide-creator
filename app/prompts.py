"""
Prompt templates for LLM interactions.
Contains system prompts, user prompts, and JSON schemas for structured outputs.
"""

# ============ SYSTEM PROMPTS ============

SYSTEM_PARTNER_REVIEW = """You are a Senior Partner at a top-tier strategy consulting firm (McKinsey, BCG, Bain caliber).
You review presentation storylines with a critical, constructive eye.

Your approach:
- Top-down thinking: Start with the answer, then support it
- Pyramid Principle: Group ideas logically, MECE where possible
- Pragmatic: Focus on what matters to the audience
- Incisive: Cut through fluff, identify the core message
- Executive presence: Communicate with confidence and clarity

When reviewing a storyline:
1. Identify what works and should be preserved
2. Spot logical gaps, missing evidence, or weak arguments
3. Flag risks (audience reception, feasibility, credibility)
4. Provide actionable recommendations
5. Ask clarifying questions that would strengthen the narrative

Be direct but constructive. Your goal is to make this presentation compelling and bulletproof."""

SYSTEM_SLIDE_OUTLINE = """You are a presentation architect at a top-tier consulting firm.
Your job is to transform a storyline into a well-structured slide deck outline.

Principles:
- Each slide should have ONE clear message
- Slides should flow logically with clear transitions
- Use the "answer first" approach where appropriate
- Balance depth with accessibility
- Consider the audience's knowledge level and interests

For each slide, define:
- A clear, action-oriented title (not descriptive, but insightful)
- The specific objective (what should the audience think/feel/do)
- The key message (the one thing to remember)
- Supporting points (3-5 bullets max)
- Evidence or data needed to support the message

Create a deck structure that tells a compelling story from beginning to end."""

SYSTEM_SLIDE_SPEC = """You are a slide designer and content strategist at a top-tier consulting firm.
Your job is to specify the exact content and visual framework for each slide.

You have access to a set of PRE-APPROVED FRAMEWORKS. You MUST select one framework from this list.
Do not invent new frameworks or suggest frameworks not in the list.

When designing a slide:
1. Choose the most appropriate framework from the approved list
2. Explain briefly why this framework fits (rationale)
3. Structure the content to fit the framework's layout
4. Write clear, concise copy (headline, body, footnotes)
5. Specify any data visualizations needed
6. Include speaker notes if helpful

Quality bar:
- Headlines should state the insight, not describe the content
- Body text should be scannable (short phrases, parallel structure)
- Every element should earn its place on the slide
- Less is more: if it doesn't add value, remove it"""

SYSTEM_SLIDE_SPEC_REVISION = """You are revising a slide specification based on user feedback.
Maintain the overall structure but incorporate the requested changes.
If the feedback suggests a different framework would be better, you may change it.
Always explain your rationale for the revision."""


# ============ USER PROMPT TEMPLATES ============

def build_partner_review_prompt(storyline: str, context: dict) -> str:
    """Build the user prompt for partner review."""
    prompt = f"""Please review the following storyline for a presentation:

=== STORYLINE ===
{storyline}
=== END STORYLINE ===
"""

    if context.get("target_audience"):
        prompt += f"\nTarget Audience: {context['target_audience']}"
    if context.get("duration_minutes"):
        prompt += f"\nExpected Duration: {context['duration_minutes']} minutes"
    if context.get("tone_of_voice"):
        prompt += f"\nTone of Voice: {context['tone_of_voice']}"
    if context.get("brand_constraints"):
        prompt += f"\nBrand Constraints: {context['brand_constraints']}"
    if context.get("additional_context"):
        prompt += f"\nAdditional Context: {context['additional_context']}"

    prompt += """

Provide your structured review following the exact JSON schema provided.
Be specific and actionable in your feedback."""

    return prompt


def build_slide_outline_prompt(storyline: str, review_feedback: str = None, context: dict = None) -> str:
    """Build the user prompt for slide outline generation."""
    prompt = f"""Create a slide deck outline for the following storyline:

=== STORYLINE ===
{storyline}
=== END STORYLINE ===
"""

    if review_feedback:
        prompt += f"""
The storyline has been reviewed with the following key points to address:
{review_feedback}
"""

    if context:
        if context.get("target_audience"):
            prompt += f"\nTarget Audience: {context['target_audience']}"
        if context.get("duration_minutes"):
            prompt += f"\nExpected Duration: {context['duration_minutes']} minutes (plan slide count accordingly)"
        if context.get("tone_of_voice"):
            prompt += f"\nTone of Voice: {context['tone_of_voice']}"

    prompt += """

Generate a complete slide outline. Each slide should have:
- A unique ID (S01, S02, etc.)
- An insight-driven title
- Clear objective
- Key message (one sentence)
- 3-5 supporting bullets
- Evidence/data needed

Follow the JSON schema exactly."""

    return prompt


def build_slide_outline_revision_prompt(current_outline: str, user_feedback: str) -> str:
    """Build prompt for revising the slide outline."""
    return f"""Please revise the following slide outline based on user feedback:

=== CURRENT OUTLINE ===
{current_outline}
=== END OUTLINE ===

=== USER FEEDBACK ===
{user_feedback}
=== END FEEDBACK ===

Incorporate the feedback and return the revised outline in the same JSON format.
Maintain slide IDs for unchanged slides. Use new IDs for new slides."""


def build_slide_spec_prompt(
    slide_outline: dict,
    frameworks_list: str,
    deck_context: str = None,
    previous_slides: list = None
) -> str:
    """Build the user prompt for slide specification."""
    prompt = f"""Design the detailed specification for this slide:

=== SLIDE OUTLINE ===
Slide ID: {slide_outline['slide_id']}
Title: {slide_outline['title']}
Objective: {slide_outline['objective']}
Key Message: {slide_outline['key_message']}
Bullets: {', '.join(slide_outline['bullets'])}
Evidence Needed: {', '.join(slide_outline.get('evidence_needed', []))}
=== END OUTLINE ===

=== APPROVED FRAMEWORKS (you MUST choose one) ===
{frameworks_list}
=== END FRAMEWORKS ===
"""

    if deck_context:
        prompt += f"\nDeck Context: {deck_context}"

    if previous_slides:
        prompt += "\n\nPrevious slides in this deck (for context and consistency):"
        for ps in previous_slides[-3:]:  # Last 3 slides for context
            prompt += f"\n- {ps.get('slide_id')}: {ps.get('title')} (Framework: {ps.get('framework_name', 'N/A')})"

    prompt += """

Select the most appropriate framework and design the slide content.
Follow the JSON schema exactly. Ensure the content fits the framework's structure."""

    return prompt


def build_slide_spec_revision_prompt(current_spec: str, user_feedback: str, frameworks_list: str) -> str:
    """Build prompt for revising a slide spec."""
    return f"""Revise this slide specification based on user feedback:

=== CURRENT SPECIFICATION ===
{current_spec}
=== END SPECIFICATION ===

=== USER FEEDBACK ===
{user_feedback}
=== END FEEDBACK ===

=== APPROVED FRAMEWORKS (if changing framework, choose from this list) ===
{frameworks_list}
=== END FRAMEWORKS ===

Apply the feedback and return the revised specification in the same JSON format."""


# ============ JSON SCHEMAS ============

SCHEMA_STORYLINE_REVIEW = {
    "type": "object",
    "properties": {
        "overall_assessment": {
            "type": "string",
            "description": "High-level assessment of the storyline (2-3 sentences)"
        },
        "strengths": {
            "type": "array",
            "items": {"type": "string"},
            "description": "What works well (3-5 items)"
        },
        "gaps": {
            "type": "array",
            "items": {"type": "string"},
            "description": "What's missing or unclear (3-5 items)"
        },
        "risks": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Potential risks or issues (2-4 items)"
        },
        "recommendations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Actionable recommendations (3-5 items)"
        },
        "clarifying_questions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Questions to ask the stakeholder (2-4 items)"
        },
        "suggested_rewrite": {
            "type": "string",
            "description": "Optional improved version of the storyline"
        }
    },
    "required": ["overall_assessment", "strengths", "gaps", "risks", "recommendations", "clarifying_questions"],
    "additionalProperties": False
}

SCHEMA_SLIDE_OUTLINE = {
    "type": "object",
    "properties": {
        "deck_title": {
            "type": "string",
            "description": "Overall presentation title"
        },
        "deck_subtitle": {
            "type": "string",
            "description": "Optional subtitle"
        },
        "slides": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "slide_id": {"type": "string"},
                    "title": {"type": "string"},
                    "objective": {"type": "string"},
                    "key_message": {"type": "string"},
                    "bullets": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "evidence_needed": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["slide_id", "title", "objective", "key_message", "bullets"]
            }
        }
    },
    "required": ["deck_title", "slides"],
    "additionalProperties": False
}

SCHEMA_SLIDE_SPEC = {
    "type": "object",
    "properties": {
        "slide_id": {"type": "string"},
        "title": {"type": "string"},
        "framework_id": {"type": "string"},
        "framework_name": {"type": "string"},
        "rationale": {"type": "string"},
        "layout": {
            "type": "object",
            "properties": {
                "sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "content_type": {"type": "string"},
                            "content": {"type": "string"},
                            "position": {"type": "string"}
                        },
                        "required": ["name", "content_type", "content"]
                    }
                },
                "visual_notes": {"type": "string"}
            },
            "required": ["sections"]
        },
        "copy": {
            "type": "object",
            "properties": {
                "headline": {"type": "string"},
                "body": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "footnotes": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "speaker_notes": {"type": "string"}
            },
            "required": ["headline", "body"]
        },
        "data_viz": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "title": {"type": "string"},
                "spec": {"type": "object"}
            },
            "required": ["type"]
        }
    },
    "required": ["slide_id", "title", "framework_id", "framework_name", "rationale", "layout", "copy"],
    "additionalProperties": False
}


def get_frameworks_summary(frameworks: list) -> str:
    """Generate a formatted summary of available frameworks for the LLM."""
    lines = []
    for fw in frameworks:
        lines.append(f"- {fw['id']}: {fw['name']}")
        lines.append(f"  Description: {fw['description']}")
        lines.append(f"  When to use: {fw['when_to_use']}")
        lines.append(f"  Layout: {fw['layout_hint']}")
        lines.append("")
    return "\n".join(lines)
