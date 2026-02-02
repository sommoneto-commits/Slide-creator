"""
OpenAI API client wrapper with retry logic, structured output, and logging.
"""
import json
import logging
import os
from typing import Optional

from openai import OpenAI
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.models import (
    LLMResponse,
    StorylineReview,
    SlideOutline,
    SlideSpec,
)
from app.prompts import (
    SYSTEM_PARTNER_REVIEW,
    SYSTEM_SLIDE_OUTLINE,
    SYSTEM_SLIDE_SPEC,
    SYSTEM_SLIDE_SPEC_REVISION,
    SCHEMA_STORYLINE_REVIEW,
    SCHEMA_SLIDE_OUTLINE,
    SCHEMA_SLIDE_SPEC,
    build_partner_review_prompt,
    build_slide_outline_prompt,
    build_slide_outline_revision_prompt,
    build_slide_spec_prompt,
    build_slide_spec_revision_prompt,
    get_frameworks_summary,
)

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for OpenAI API interactions."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment or parameters")

        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o")
        self.client = OpenAI(api_key=self.api_key)

        # Temperature settings per step
        self.temp_review = float(os.getenv("OPENAI_TEMPERATURE_REVIEW", "0.4"))
        self.temp_outline = float(os.getenv("OPENAI_TEMPERATURE_OUTLINE", "0.5"))
        self.temp_spec = float(os.getenv("OPENAI_TEMPERATURE_SPEC", "0.6"))

        logger.info(f"LLMClient initialized with model: {self.model}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    )
    def _call_api(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        response_format: Optional[dict] = None,
        max_tokens: int = 4000,
    ) -> LLMResponse:
        """Make an API call with retry logic."""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            # Use response_format for JSON mode if schema provided
            if response_format:
                kwargs["response_format"] = {"type": "json_object"}

            logger.debug(f"Calling OpenAI API with model {self.model}")
            response = self.client.chat.completions.create(**kwargs)

            content = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

            logger.info(f"API call successful. Tokens used: {usage['total_tokens']}")

            return LLMResponse(
                content=content,
                usage=usage,
                model=response.model,
                success=True,
            )

        except Exception as e:
            logger.error(f"API call failed: {str(e)}")
            return LLMResponse(
                content="",
                model=self.model,
                success=False,
                error=str(e),
            )

    def _parse_json_response(self, content: str, schema: dict) -> tuple[dict, Optional[str]]:
        """Parse and validate JSON response."""
        try:
            # Try to extract JSON if wrapped in markdown code blocks
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                content = content[start:end].strip()

            parsed = json.loads(content)
            return parsed, None
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            return {}, f"JSON parse error: {str(e)}"

    def _repair_json(self, broken_content: str, schema: dict) -> Optional[dict]:
        """Attempt to repair broken JSON with a follow-up call."""
        repair_prompt = f"""The following JSON is malformed. Please fix it and return valid JSON only.
Do not include any explanation, just the corrected JSON.

Expected schema structure:
{json.dumps(schema, indent=2)}

Broken content:
{broken_content}"""

        response = self._call_api(
            system_prompt="You are a JSON repair assistant. Return only valid JSON.",
            user_prompt=repair_prompt,
            temperature=0.1,
            response_format={"type": "json_object"},
            max_tokens=4000,
        )

        if response.success:
            try:
                return json.loads(response.content)
            except json.JSONDecodeError:
                pass
        return None

    # ============ PARTNER REVIEW ============

    def partner_review(self, storyline: str, context: dict = None) -> tuple[StorylineReview, LLMResponse]:
        """Generate partner review of storyline."""
        context = context or {}
        user_prompt = build_partner_review_prompt(storyline, context)

        # Add JSON schema instruction to system prompt
        system_with_schema = SYSTEM_PARTNER_REVIEW + f"""

You MUST respond with valid JSON matching this exact schema:
{json.dumps(SCHEMA_STORYLINE_REVIEW, indent=2)}

Respond ONLY with the JSON object, no additional text."""

        response = self._call_api(
            system_prompt=system_with_schema,
            user_prompt=user_prompt,
            temperature=self.temp_review,
            response_format=SCHEMA_STORYLINE_REVIEW,
        )

        if not response.success:
            raise Exception(f"API call failed: {response.error}")

        parsed, error = self._parse_json_response(response.content, SCHEMA_STORYLINE_REVIEW)

        if error:
            # Try to repair
            repaired = self._repair_json(response.content, SCHEMA_STORYLINE_REVIEW)
            if repaired:
                parsed = repaired
            else:
                raise Exception(f"Failed to parse review response: {error}")

        response.parsed = parsed

        try:
            review = StorylineReview(**parsed)
            return review, response
        except ValidationError as e:
            raise Exception(f"Validation error: {e}")

    # ============ SLIDE OUTLINE ============

    def generate_slide_outline(
        self,
        storyline: str,
        review_feedback: str = None,
        context: dict = None,
    ) -> tuple[SlideOutline, LLMResponse]:
        """Generate slide deck outline."""
        user_prompt = build_slide_outline_prompt(storyline, review_feedback, context)

        system_with_schema = SYSTEM_SLIDE_OUTLINE + f"""

You MUST respond with valid JSON matching this exact schema:
{json.dumps(SCHEMA_SLIDE_OUTLINE, indent=2)}

Respond ONLY with the JSON object, no additional text."""

        response = self._call_api(
            system_prompt=system_with_schema,
            user_prompt=user_prompt,
            temperature=self.temp_outline,
            response_format=SCHEMA_SLIDE_OUTLINE,
        )

        if not response.success:
            raise Exception(f"API call failed: {response.error}")

        parsed, error = self._parse_json_response(response.content, SCHEMA_SLIDE_OUTLINE)

        if error:
            repaired = self._repair_json(response.content, SCHEMA_SLIDE_OUTLINE)
            if repaired:
                parsed = repaired
            else:
                raise Exception(f"Failed to parse outline response: {error}")

        response.parsed = parsed

        try:
            outline = SlideOutline(**parsed)
            return outline, response
        except ValidationError as e:
            raise Exception(f"Validation error: {e}")

    def revise_slide_outline(
        self,
        current_outline: SlideOutline,
        user_feedback: str,
    ) -> tuple[SlideOutline, LLMResponse]:
        """Revise slide outline based on user feedback."""
        outline_json = current_outline.model_dump_json(indent=2)
        user_prompt = build_slide_outline_revision_prompt(outline_json, user_feedback)

        system_with_schema = SYSTEM_SLIDE_OUTLINE + f"""

You are revising an existing outline based on user feedback.

You MUST respond with valid JSON matching this exact schema:
{json.dumps(SCHEMA_SLIDE_OUTLINE, indent=2)}

Respond ONLY with the JSON object, no additional text."""

        response = self._call_api(
            system_prompt=system_with_schema,
            user_prompt=user_prompt,
            temperature=self.temp_outline,
            response_format=SCHEMA_SLIDE_OUTLINE,
        )

        if not response.success:
            raise Exception(f"API call failed: {response.error}")

        parsed, error = self._parse_json_response(response.content, SCHEMA_SLIDE_OUTLINE)

        if error:
            repaired = self._repair_json(response.content, SCHEMA_SLIDE_OUTLINE)
            if repaired:
                parsed = repaired
            else:
                raise Exception(f"Failed to parse revised outline: {error}")

        response.parsed = parsed

        try:
            outline = SlideOutline(**parsed)
            return outline, response
        except ValidationError as e:
            raise Exception(f"Validation error: {e}")

    # ============ SLIDE SPEC ============

    def generate_slide_spec(
        self,
        slide_outline: dict,
        frameworks: list,
        deck_context: str = None,
        previous_slides: list = None,
    ) -> tuple[SlideSpec, LLMResponse]:
        """Generate detailed slide specification."""
        frameworks_summary = get_frameworks_summary(frameworks)

        # Create list of valid framework IDs for the guardrail
        valid_ids = [fw["id"] for fw in frameworks]
        guardrail = f"\nVALID FRAMEWORK IDs (you MUST use one of these): {', '.join(valid_ids)}"

        user_prompt = build_slide_spec_prompt(
            slide_outline,
            frameworks_summary + guardrail,
            deck_context,
            previous_slides,
        )

        system_with_schema = SYSTEM_SLIDE_SPEC + f"""

You MUST respond with valid JSON matching this exact schema:
{json.dumps(SCHEMA_SLIDE_SPEC, indent=2)}

Respond ONLY with the JSON object, no additional text."""

        response = self._call_api(
            system_prompt=system_with_schema,
            user_prompt=user_prompt,
            temperature=self.temp_spec,
            response_format=SCHEMA_SLIDE_SPEC,
        )

        if not response.success:
            raise Exception(f"API call failed: {response.error}")

        parsed, error = self._parse_json_response(response.content, SCHEMA_SLIDE_SPEC)

        if error:
            repaired = self._repair_json(response.content, SCHEMA_SLIDE_SPEC)
            if repaired:
                parsed = repaired
            else:
                raise Exception(f"Failed to parse slide spec: {error}")

        # Validate framework_id is in allowed list
        if parsed.get("framework_id") not in valid_ids:
            logger.warning(f"Invalid framework_id: {parsed.get('framework_id')}, defaulting to first framework")
            parsed["framework_id"] = valid_ids[0]
            parsed["framework_name"] = frameworks[0]["name"]

        response.parsed = parsed

        try:
            spec = SlideSpec(**parsed)
            return spec, response
        except ValidationError as e:
            raise Exception(f"Validation error: {e}")

    def revise_slide_spec(
        self,
        current_spec: SlideSpec,
        user_feedback: str,
        frameworks: list,
    ) -> tuple[SlideSpec, LLMResponse]:
        """Revise slide spec based on user feedback."""
        spec_json = current_spec.model_dump_json(indent=2)
        frameworks_summary = get_frameworks_summary(frameworks)
        valid_ids = [fw["id"] for fw in frameworks]
        guardrail = f"\nVALID FRAMEWORK IDs: {', '.join(valid_ids)}"

        user_prompt = build_slide_spec_revision_prompt(
            spec_json,
            user_feedback,
            frameworks_summary + guardrail,
        )

        system_with_schema = SYSTEM_SLIDE_SPEC_REVISION + f"""

You MUST respond with valid JSON matching this exact schema:
{json.dumps(SCHEMA_SLIDE_SPEC, indent=2)}

Respond ONLY with the JSON object, no additional text."""

        response = self._call_api(
            system_prompt=system_with_schema,
            user_prompt=user_prompt,
            temperature=self.temp_spec,
            response_format=SCHEMA_SLIDE_SPEC,
        )

        if not response.success:
            raise Exception(f"API call failed: {response.error}")

        parsed, error = self._parse_json_response(response.content, SCHEMA_SLIDE_SPEC)

        if error:
            repaired = self._repair_json(response.content, SCHEMA_SLIDE_SPEC)
            if repaired:
                parsed = repaired
            else:
                raise Exception(f"Failed to parse revised spec: {error}")

        # Validate framework_id
        if parsed.get("framework_id") not in valid_ids:
            parsed["framework_id"] = current_spec.framework_id
            parsed["framework_name"] = current_spec.framework_name

        response.parsed = parsed

        try:
            spec = SlideSpec(**parsed)
            return spec, response
        except ValidationError as e:
            raise Exception(f"Validation error: {e}")
