"""
Data models for Slide Creator using Pydantic.
Defines all structured data types used throughout the application.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class FlowState(str, Enum):
    """Possible states in the presentation creation flow."""
    INIT = "init"
    STORYLINE_INPUT = "storyline_input"
    PARTNER_REVIEW = "partner_review"
    SLIDE_OUTLINE = "slide_outline"
    SLIDE_SPEC = "slide_spec"
    GAMMA_GENERATION = "gamma_generation"
    EXPORT = "export"
    COMPLETED = "completed"
    ABORTED = "aborted"


class UserAction(str, Enum):
    """Possible user actions during the flow."""
    APPROVE = "approve"
    EDIT = "edit"
    RETRY = "retry"
    ABORT = "abort"
    UPDATE = "update"
    ADD = "add"
    DELETE = "delete"
    SKIP = "skip"


# ============ INPUT MODELS ============

class StorylineInput(BaseModel):
    """Input storyline and optional parameters."""
    storyline: str = Field(..., description="The main storyline text")
    target_audience: Optional[str] = Field(None, description="Target audience for the presentation")
    duration_minutes: Optional[int] = Field(None, description="Expected presentation duration in minutes")
    tone_of_voice: Optional[str] = Field(None, description="Desired tone (e.g., formal, conversational)")
    brand_constraints: Optional[str] = Field(None, description="Brand guidelines or constraints")
    additional_context: Optional[str] = Field(None, description="Any additional context")


# ============ STEP A: PARTNER REVIEW ============

class StorylineReview(BaseModel):
    """Structured feedback from the partner review step."""
    overall_assessment: str = Field(..., description="High-level assessment of the storyline")
    strengths: list[str] = Field(default_factory=list, description="What works well")
    gaps: list[str] = Field(default_factory=list, description="What's missing or unclear")
    risks: list[str] = Field(default_factory=list, description="Potential risks or issues")
    recommendations: list[str] = Field(default_factory=list, description="Actionable recommendations")
    clarifying_questions: list[str] = Field(default_factory=list, description="Questions to clarify with stakeholder")
    suggested_rewrite: Optional[str] = Field(None, description="Optional suggested rewrite of storyline")


# ============ STEP B: SLIDE OUTLINE ============

class SlideOutlineItem(BaseModel):
    """Individual slide in the outline."""
    slide_id: str = Field(..., description="Unique slide identifier (e.g., S01)")
    title: str = Field(..., description="Slide title")
    objective: str = Field(..., description="What this slide should achieve")
    key_message: str = Field(..., description="The one thing audience should remember")
    bullets: list[str] = Field(default_factory=list, description="Key points to cover (3-5)")
    evidence_needed: list[str] = Field(default_factory=list, description="Data or evidence required")


class SlideOutline(BaseModel):
    """Complete slide outline/deck structure."""
    deck_title: str = Field(..., description="Overall presentation title")
    deck_subtitle: Optional[str] = Field(None, description="Optional subtitle")
    slides: list[SlideOutlineItem] = Field(default_factory=list, description="List of slides")


# ============ STEP C: SLIDE SPEC ============

class ContentSection(BaseModel):
    """A section within a slide layout."""
    name: str = Field(..., description="Section name/identifier")
    content_type: str = Field(..., description="Type: text, table, chart, image, list")
    content: str = Field(..., description="Actual content or description")
    position: Optional[str] = Field(None, description="Position hint (e.g., left, right, top)")


class SlideLayout(BaseModel):
    """Layout specification for a slide."""
    sections: list[ContentSection] = Field(default_factory=list, description="Layout sections")
    visual_notes: Optional[str] = Field(None, description="Notes for visual design")


class SlideCopy(BaseModel):
    """Text content for a slide."""
    headline: str = Field(..., description="Main headline/title")
    body: list[str] = Field(default_factory=list, description="Body text elements")
    footnotes: list[str] = Field(default_factory=list, description="Footnotes or sources")
    speaker_notes: Optional[str] = Field(None, description="Notes for the presenter")


class DataVizSpec(BaseModel):
    """Specification for data visualization."""
    type: str = Field("none", description="Chart type: none, bar, line, pie, table, heatmap")
    title: Optional[str] = Field(None, description="Chart title")
    spec: dict = Field(default_factory=dict, description="Chart-specific configuration")


class SlideSpec(BaseModel):
    """Complete specification for a single slide."""
    slide_id: str = Field(..., description="Slide identifier")
    title: str = Field(..., description="Slide title")
    framework_id: str = Field(..., description="ID of the selected framework")
    framework_name: str = Field(..., description="Human-readable framework name")
    rationale: str = Field(..., description="Why this framework was chosen")
    layout: SlideLayout = Field(..., description="Layout specification")
    copy: SlideCopy = Field(..., description="Text content")
    data_viz: DataVizSpec = Field(default_factory=DataVizSpec, description="Data visualization spec")


# ============ STEP D: GAMMA RESULT ============

class GammaSlideResult(BaseModel):
    """Result from Gamma API for a single slide."""
    slide_id: str = Field(..., description="Slide identifier")
    success: bool = Field(..., description="Whether generation succeeded")
    image_url: Optional[str] = Field(None, description="URL to generated slide image")
    image_data: Optional[bytes] = Field(None, description="Raw image data if available")
    structured_content: Optional[dict] = Field(None, description="Structured content if available")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    gamma_id: Optional[str] = Field(None, description="Gamma's internal ID for the slide")


# ============ SESSION & STATE ============

class SlideProgress(BaseModel):
    """Progress tracking for a single slide."""
    slide_id: str
    outline_approved: bool = False
    spec_approved: bool = False
    gamma_approved: bool = False
    spec_iterations: int = 0
    gamma_iterations: int = 0
    current_spec: Optional[SlideSpec] = None
    gamma_result: Optional[GammaSlideResult] = None


class Session(BaseModel):
    """Complete session state for persistence and resume."""
    session_id: str = Field(..., description="Unique session identifier")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Current state
    current_state: FlowState = FlowState.INIT
    current_slide_index: int = 0

    # Iteration counters
    storyline_iterations: int = 0
    outline_iterations: int = 0

    # Input
    storyline_input: Optional[StorylineInput] = None

    # Step outputs
    storyline_reviews: list[StorylineReview] = Field(default_factory=list)
    current_storyline: Optional[str] = None  # May be updated after reviews

    slide_outlines: list[SlideOutline] = Field(default_factory=list)  # Version history
    current_outline: Optional[SlideOutline] = None

    # Per-slide progress
    slide_progress: list[SlideProgress] = Field(default_factory=list)

    # Final output
    output_file: Optional[str] = None

    # Metadata
    metadata: dict = Field(default_factory=dict)

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now()


# ============ API REQUEST/RESPONSE ============

class LLMRequest(BaseModel):
    """Wrapper for LLM API requests."""
    system_prompt: str
    user_prompt: str
    temperature: float = 0.5
    max_tokens: int = 4000
    response_schema: Optional[dict] = None


class LLMResponse(BaseModel):
    """Wrapper for LLM API responses."""
    content: str
    parsed: Optional[dict] = None
    usage: Optional[dict] = None
    model: str
    success: bool = True
    error: Optional[str] = None


# ============ FRAMEWORK MODEL ============

class Framework(BaseModel):
    """Pre-approved framework definition."""
    id: str
    name: str
    description: str
    when_to_use: str
    layout_hint: str
    do: list[str] = Field(default_factory=list)
    dont: list[str] = Field(default_factory=list)


class FrameworksConfig(BaseModel):
    """Configuration containing all frameworks."""
    version: str
    frameworks: list[Framework]
