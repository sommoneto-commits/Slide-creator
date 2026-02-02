"""
Tests for data models.
"""
import pytest
from datetime import datetime

from app.models import (
    FlowState,
    UserAction,
    StorylineInput,
    StorylineReview,
    SlideOutlineItem,
    SlideOutline,
    ContentSection,
    SlideLayout,
    SlideCopy,
    DataVizSpec,
    SlideSpec,
    GammaSlideResult,
    SlideProgress,
    Session,
    Framework,
)


class TestStorylineInput:
    def test_create_minimal(self):
        input_data = StorylineInput(storyline="Test storyline")
        assert input_data.storyline == "Test storyline"
        assert input_data.target_audience is None
        assert input_data.duration_minutes is None

    def test_create_full(self):
        input_data = StorylineInput(
            storyline="Test storyline",
            target_audience="Executives",
            duration_minutes=30,
            tone_of_voice="formal",
            brand_constraints="Blue theme",
            additional_context="Q4 presentation",
        )
        assert input_data.target_audience == "Executives"
        assert input_data.duration_minutes == 30


class TestStorylineReview:
    def test_create_review(self):
        review = StorylineReview(
            overall_assessment="Good storyline with room for improvement",
            strengths=["Clear structure", "Good data"],
            gaps=["Missing competitor analysis"],
            risks=["Timeline too aggressive"],
            recommendations=["Add market context"],
            clarifying_questions=["Who are key stakeholders?"],
        )
        assert len(review.strengths) == 2
        assert len(review.gaps) == 1

    def test_review_with_suggested_rewrite(self):
        review = StorylineReview(
            overall_assessment="Needs work",
            strengths=[],
            gaps=[],
            risks=[],
            recommendations=[],
            clarifying_questions=[],
            suggested_rewrite="Here is a better version...",
        )
        assert review.suggested_rewrite is not None


class TestSlideOutline:
    def test_create_outline_item(self):
        item = SlideOutlineItem(
            slide_id="S01",
            title="Executive Summary",
            objective="Set context and recommendations",
            key_message="We recommend a 3-year transformation",
            bullets=["Point 1", "Point 2", "Point 3"],
            evidence_needed=["Market data", "Financial projections"],
        )
        assert item.slide_id == "S01"
        assert len(item.bullets) == 3

    def test_create_full_outline(self):
        slides = [
            SlideOutlineItem(
                slide_id=f"S{i:02d}",
                title=f"Slide {i}",
                objective=f"Objective {i}",
                key_message=f"Message {i}",
                bullets=[f"Bullet {i}"],
            )
            for i in range(1, 6)
        ]
        outline = SlideOutline(
            deck_title="Digital Transformation",
            deck_subtitle="Strategy Presentation",
            slides=slides,
        )
        assert outline.deck_title == "Digital Transformation"
        assert len(outline.slides) == 5


class TestSlideSpec:
    def test_create_slide_spec(self):
        layout = SlideLayout(
            sections=[
                ContentSection(
                    name="Main",
                    content_type="text",
                    content="Main content here",
                    position="center",
                )
            ],
            visual_notes="Use blue theme",
        )
        copy = SlideCopy(
            headline="The market has shifted",
            body=["Point 1", "Point 2"],
            footnotes=["Source: Industry Report 2024"],
            speaker_notes="Emphasize the urgency",
        )
        data_viz = DataVizSpec(
            type="bar",
            title="Market Share",
            spec={"categories": ["A", "B", "C"]},
        )
        spec = SlideSpec(
            slide_id="S01",
            title="Market Overview",
            framework_id="pyramid_executive_summary",
            framework_name="Pyramid / Executive Summary",
            rationale="Best for executive opening",
            layout=layout,
            copy=copy,
            data_viz=data_viz,
        )
        assert spec.framework_id == "pyramid_executive_summary"
        assert len(spec.layout.sections) == 1
        assert spec.data_viz.type == "bar"


class TestGammaSlideResult:
    def test_success_result(self):
        result = GammaSlideResult(
            slide_id="S01",
            success=True,
            gamma_id="gamma_abc123",
            image_url="https://gamma.app/preview/abc123.png",
            structured_content={"elements": []},
        )
        assert result.success is True
        assert result.gamma_id is not None

    def test_failure_result(self):
        result = GammaSlideResult(
            slide_id="S01",
            success=False,
            error_message="API rate limit exceeded",
        )
        assert result.success is False
        assert result.error_message is not None


class TestSession:
    def test_create_session(self):
        session = Session(session_id="test_session_001")
        assert session.session_id == "test_session_001"
        assert session.current_state == FlowState.INIT
        assert session.storyline_iterations == 0

    def test_update_timestamp(self):
        session = Session(session_id="test")
        old_time = session.updated_at
        import time
        time.sleep(0.01)
        session.update_timestamp()
        assert session.updated_at > old_time

    def test_session_with_progress(self):
        session = Session(session_id="test")
        session.slide_progress = [
            SlideProgress(slide_id="S01", spec_approved=True),
            SlideProgress(slide_id="S02", spec_approved=False),
        ]
        assert len(session.slide_progress) == 2
        assert session.slide_progress[0].spec_approved is True


class TestFlowState:
    def test_flow_states(self):
        assert FlowState.INIT.value == "init"
        assert FlowState.PARTNER_REVIEW.value == "partner_review"
        assert FlowState.COMPLETED.value == "completed"


class TestUserAction:
    def test_user_actions(self):
        assert UserAction.APPROVE.value == "approve"
        assert UserAction.EDIT.value == "edit"
        assert UserAction.ABORT.value == "abort"


class TestFramework:
    def test_create_framework(self):
        framework = Framework(
            id="2x2_matrix",
            name="2x2 Matrix",
            description="Four-quadrant framework",
            when_to_use="Strategic prioritization",
            layout_hint="Equal quadrants",
            do=["Choose orthogonal axes"],
            dont=["Overcrowd quadrants"],
        )
        assert framework.id == "2x2_matrix"
        assert len(framework.do) == 1
        assert len(framework.dont) == 1
