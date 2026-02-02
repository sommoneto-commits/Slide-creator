"""
Orchestrator - State machine that controls the presentation creation flow.
Manages transitions between steps and coordinates all components.
"""
import json
import logging
import os
from pathlib import Path
from typing import Optional, Callable

from app.models import (
    Session,
    FlowState,
    UserAction,
    StorylineInput,
    StorylineReview,
    SlideOutline,
    SlideOutlineItem,
    SlideSpec,
    SlideProgress,
    GammaSlideResult,
    Framework,
    FrameworksConfig,
)
from app.llm_client import LLMClient
from app.gamma_client import get_gamma_client, GammaClientBase
from app.pptx_exporter import PPTXExporter
from app.state_store import StateStore, LogStore

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Main orchestrator that controls the presentation creation flow.
    Implements a state machine with the following states:
    INIT -> STORYLINE_INPUT -> PARTNER_REVIEW -> SLIDE_OUTLINE -> SLIDE_SPEC -> GAMMA_GENERATION -> EXPORT -> COMPLETED
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        gamma_client: Optional[GammaClientBase] = None,
        pptx_exporter: Optional[PPTXExporter] = None,
        state_store: Optional[StateStore] = None,
        log_store: Optional[LogStore] = None,
    ):
        self.llm = llm_client or LLMClient()
        self.gamma = gamma_client or get_gamma_client()
        self.exporter = pptx_exporter or PPTXExporter()
        self.state_store = state_store or StateStore()
        self.log_store = log_store or LogStore()

        # Load frameworks
        self.frameworks = self._load_frameworks()

        # Configuration
        self.max_storyline_iterations = int(os.getenv("MAX_STORYLINE_ITERATIONS", "3"))
        self.max_outline_iterations = int(os.getenv("MAX_OUTLINE_ITERATIONS", "5"))
        self.max_slide_spec_iterations = int(os.getenv("MAX_SLIDE_SPEC_ITERATIONS", "5"))
        self.max_gamma_iterations = int(os.getenv("MAX_GAMMA_ITERATIONS", "3"))

        logger.info("Orchestrator initialized")

    def _load_frameworks(self) -> list[dict]:
        """Load frameworks from JSON file."""
        frameworks_path = Path(__file__).parent / "frameworks.json"

        if not frameworks_path.exists():
            logger.warning("frameworks.json not found, using empty list")
            return []

        with open(frameworks_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data.get("frameworks", [])

    def get_frameworks_list(self) -> list[dict]:
        """Get the list of available frameworks."""
        return self.frameworks

    # ============ SESSION MANAGEMENT ============

    def create_session(self, storyline: str = "") -> Session:
        """Create a new session."""
        session = self.state_store.create_session(storyline)
        logger.info(f"Created session: {session.session_id}")
        return session

    def load_session(self, session_id: str) -> Optional[Session]:
        """Load an existing session."""
        return self.state_store.load_session(session_id)

    def save_session(self, session: Session) -> None:
        """Save session state."""
        self.state_store.save_session(session)

    def list_sessions(self) -> list[dict]:
        """List all available sessions."""
        return self.state_store.list_sessions()

    # ============ STEP A: PARTNER REVIEW ============

    def run_partner_review(
        self,
        session: Session,
        storyline_input: StorylineInput,
    ) -> StorylineReview:
        """
        Run partner review on the storyline.
        Returns structured feedback.
        """
        if session.storyline_iterations >= self.max_storyline_iterations:
            raise ValueError(f"Maximum storyline iterations ({self.max_storyline_iterations}) reached")

        # Store input
        session.storyline_input = storyline_input
        session.current_storyline = storyline_input.storyline
        session.current_state = FlowState.PARTNER_REVIEW

        # Build context
        context = {
            "target_audience": storyline_input.target_audience,
            "duration_minutes": storyline_input.duration_minutes,
            "tone_of_voice": storyline_input.tone_of_voice,
            "brand_constraints": storyline_input.brand_constraints,
            "additional_context": storyline_input.additional_context,
        }

        # Call LLM
        review, response = self.llm.partner_review(
            storyline=session.current_storyline,
            context=context,
        )

        # Log the call
        self.log_store.log_llm_call(
            session_id=session.session_id,
            step="partner_review",
            request={"storyline": session.current_storyline[:500], "context": context},
            response={"review": review.model_dump()},
        )

        # Store result
        session.storyline_reviews.append(review)
        session.storyline_iterations += 1

        self.save_session(session)
        logger.info(f"Partner review completed for session {session.session_id}")

        return review

    def update_storyline(self, session: Session, new_storyline: str) -> None:
        """Update the storyline after user edits."""
        session.current_storyline = new_storyline
        self.save_session(session)
        logger.info(f"Storyline updated for session {session.session_id}")

    # ============ STEP B: SLIDE OUTLINE ============

    def generate_slide_outline(
        self,
        session: Session,
        use_review_feedback: bool = True,
    ) -> SlideOutline:
        """
        Generate slide deck outline.
        """
        if session.outline_iterations >= self.max_outline_iterations:
            raise ValueError(f"Maximum outline iterations ({self.max_outline_iterations}) reached")

        session.current_state = FlowState.SLIDE_OUTLINE

        # Compile review feedback if available
        review_feedback = None
        if use_review_feedback and session.storyline_reviews:
            latest_review = session.storyline_reviews[-1]
            review_feedback = f"""
Key recommendations to address:
{chr(10).join('- ' + r for r in latest_review.recommendations)}

Gaps to fill:
{chr(10).join('- ' + g for g in latest_review.gaps)}
"""

        # Build context
        context = {}
        if session.storyline_input:
            context = {
                "target_audience": session.storyline_input.target_audience,
                "duration_minutes": session.storyline_input.duration_minutes,
                "tone_of_voice": session.storyline_input.tone_of_voice,
            }

        # Call LLM
        outline, response = self.llm.generate_slide_outline(
            storyline=session.current_storyline,
            review_feedback=review_feedback,
            context=context,
        )

        # Log the call
        self.log_store.log_llm_call(
            session_id=session.session_id,
            step="generate_outline",
            request={"storyline": session.current_storyline[:500]},
            response={"outline": outline.model_dump()},
        )

        # Store result
        session.slide_outlines.append(outline)
        session.current_outline = outline
        session.outline_iterations += 1

        # Initialize slide progress
        session.slide_progress = [
            SlideProgress(slide_id=slide.slide_id)
            for slide in outline.slides
        ]

        self.save_session(session)
        logger.info(f"Slide outline generated for session {session.session_id}: {len(outline.slides)} slides")

        return outline

    def revise_slide_outline(
        self,
        session: Session,
        user_feedback: str,
    ) -> SlideOutline:
        """Revise the slide outline based on user feedback."""
        if not session.current_outline:
            raise ValueError("No outline to revise")

        if session.outline_iterations >= self.max_outline_iterations:
            raise ValueError(f"Maximum outline iterations ({self.max_outline_iterations}) reached")

        # Call LLM
        revised, response = self.llm.revise_slide_outline(
            current_outline=session.current_outline,
            user_feedback=user_feedback,
        )

        # Log the call
        self.log_store.log_llm_call(
            session_id=session.session_id,
            step="revise_outline",
            request={"feedback": user_feedback},
            response={"outline": revised.model_dump()},
        )

        # Store result
        session.slide_outlines.append(revised)
        session.current_outline = revised
        session.outline_iterations += 1

        # Update slide progress for new slides
        existing_ids = {sp.slide_id for sp in session.slide_progress}
        for slide in revised.slides:
            if slide.slide_id not in existing_ids:
                session.slide_progress.append(SlideProgress(slide_id=slide.slide_id))

        # Remove progress for deleted slides
        current_ids = {s.slide_id for s in revised.slides}
        session.slide_progress = [
            sp for sp in session.slide_progress if sp.slide_id in current_ids
        ]

        self.save_session(session)
        logger.info(f"Slide outline revised for session {session.session_id}")

        return revised

    def edit_slide_in_outline(
        self,
        session: Session,
        slide_id: str,
        updates: dict,
    ) -> SlideOutline:
        """Edit a specific slide in the outline."""
        if not session.current_outline:
            raise ValueError("No outline to edit")

        for slide in session.current_outline.slides:
            if slide.slide_id == slide_id:
                for key, value in updates.items():
                    if hasattr(slide, key):
                        setattr(slide, key, value)
                break

        self.save_session(session)
        return session.current_outline

    def add_slide_to_outline(
        self,
        session: Session,
        slide_data: dict,
        after_slide_id: Optional[str] = None,
    ) -> SlideOutline:
        """Add a new slide to the outline."""
        if not session.current_outline:
            raise ValueError("No outline to modify")

        # Generate new slide ID
        existing_ids = [int(s.slide_id[1:]) for s in session.current_outline.slides if s.slide_id.startswith("S")]
        new_id = f"S{max(existing_ids, default=0) + 1:02d}"

        new_slide = SlideOutlineItem(
            slide_id=new_id,
            **slide_data,
        )

        if after_slide_id:
            # Insert after specified slide
            for i, slide in enumerate(session.current_outline.slides):
                if slide.slide_id == after_slide_id:
                    session.current_outline.slides.insert(i + 1, new_slide)
                    break
        else:
            session.current_outline.slides.append(new_slide)

        # Add progress entry
        session.slide_progress.append(SlideProgress(slide_id=new_id))

        self.save_session(session)
        return session.current_outline

    def remove_slide_from_outline(
        self,
        session: Session,
        slide_id: str,
    ) -> SlideOutline:
        """Remove a slide from the outline."""
        if not session.current_outline:
            raise ValueError("No outline to modify")

        session.current_outline.slides = [
            s for s in session.current_outline.slides if s.slide_id != slide_id
        ]
        session.slide_progress = [
            sp for sp in session.slide_progress if sp.slide_id != slide_id
        ]

        self.save_session(session)
        return session.current_outline

    # ============ STEP C: SLIDE SPEC ============

    def generate_slide_spec(
        self,
        session: Session,
        slide_index: int,
    ) -> SlideSpec:
        """Generate detailed spec for a specific slide."""
        if not session.current_outline:
            raise ValueError("No outline available")

        if slide_index >= len(session.current_outline.slides):
            raise ValueError(f"Invalid slide index: {slide_index}")

        session.current_state = FlowState.SLIDE_SPEC
        session.current_slide_index = slide_index

        slide = session.current_outline.slides[slide_index]
        progress = session.slide_progress[slide_index]

        if progress.spec_iterations >= self.max_slide_spec_iterations:
            raise ValueError(f"Maximum spec iterations ({self.max_slide_spec_iterations}) reached for slide {slide.slide_id}")

        # Get previous slides' specs for context
        previous_specs = []
        for i in range(slide_index):
            sp = session.slide_progress[i]
            if sp.current_spec:
                previous_specs.append({
                    "slide_id": sp.current_spec.slide_id,
                    "title": sp.current_spec.title,
                    "framework_name": sp.current_spec.framework_name,
                })

        # Call LLM
        spec, response = self.llm.generate_slide_spec(
            slide_outline=slide.model_dump(),
            frameworks=self.frameworks,
            deck_context=f"Deck: {session.current_outline.deck_title}",
            previous_slides=previous_specs,
        )

        # Log the call
        self.log_store.log_llm_call(
            session_id=session.session_id,
            step=f"generate_spec_{slide.slide_id}",
            request={"slide": slide.model_dump()},
            response={"spec": spec.model_dump()},
        )

        # Store result
        progress.current_spec = spec
        progress.spec_iterations += 1

        self.save_session(session)
        logger.info(f"Slide spec generated for {slide.slide_id}: framework={spec.framework_id}")

        return spec

    def revise_slide_spec(
        self,
        session: Session,
        slide_index: int,
        user_feedback: str,
    ) -> SlideSpec:
        """Revise a slide spec based on user feedback."""
        if slide_index >= len(session.slide_progress):
            raise ValueError(f"Invalid slide index: {slide_index}")

        progress = session.slide_progress[slide_index]

        if not progress.current_spec:
            raise ValueError("No spec to revise")

        if progress.spec_iterations >= self.max_slide_spec_iterations:
            raise ValueError(f"Maximum spec iterations ({self.max_slide_spec_iterations}) reached")

        # Call LLM
        revised, response = self.llm.revise_slide_spec(
            current_spec=progress.current_spec,
            user_feedback=user_feedback,
            frameworks=self.frameworks,
        )

        # Log the call
        self.log_store.log_llm_call(
            session_id=session.session_id,
            step=f"revise_spec_{progress.slide_id}",
            request={"feedback": user_feedback},
            response={"spec": revised.model_dump()},
        )

        # Store result
        progress.current_spec = revised
        progress.spec_iterations += 1

        self.save_session(session)
        logger.info(f"Slide spec revised for {progress.slide_id}")

        return revised

    def approve_slide_spec(self, session: Session, slide_index: int) -> None:
        """Mark a slide spec as approved."""
        if slide_index >= len(session.slide_progress):
            raise ValueError(f"Invalid slide index: {slide_index}")

        progress = session.slide_progress[slide_index]
        progress.spec_approved = True
        self.save_session(session)
        logger.info(f"Slide spec approved for {progress.slide_id}")

    # ============ STEP D: GAMMA GENERATION ============

    def generate_with_gamma(
        self,
        session: Session,
        slide_index: int,
    ) -> GammaSlideResult:
        """Generate slide graphics with Gamma."""
        if slide_index >= len(session.slide_progress):
            raise ValueError(f"Invalid slide index: {slide_index}")

        progress = session.slide_progress[slide_index]

        if not progress.current_spec:
            raise ValueError("No spec available for generation")

        if not progress.spec_approved:
            raise ValueError("Spec must be approved before Gamma generation")

        if progress.gamma_iterations >= self.max_gamma_iterations:
            raise ValueError(f"Maximum Gamma iterations ({self.max_gamma_iterations}) reached")

        session.current_state = FlowState.GAMMA_GENERATION

        # Call Gamma
        result = self.gamma.generate_slide(progress.current_spec)

        # Log the call
        self.log_store.log_llm_call(
            session_id=session.session_id,
            step=f"gamma_generate_{progress.slide_id}",
            request={"spec": progress.current_spec.model_dump()},
            response={
                "success": result.success,
                "gamma_id": result.gamma_id,
                "error": result.error_message,
            },
        )

        # Store result
        progress.gamma_result = result
        progress.gamma_iterations += 1

        self.save_session(session)
        logger.info(f"Gamma generation for {progress.slide_id}: success={result.success}")

        return result

    def approve_gamma_result(self, session: Session, slide_index: int) -> None:
        """Mark a Gamma result as approved."""
        if slide_index >= len(session.slide_progress):
            raise ValueError(f"Invalid slide index: {slide_index}")

        progress = session.slide_progress[slide_index]
        progress.gamma_approved = True
        self.save_session(session)
        logger.info(f"Gamma result approved for {progress.slide_id}")

    def retry_gamma_with_feedback(
        self,
        session: Session,
        slide_index: int,
        user_feedback: str,
    ) -> GammaSlideResult:
        """Retry Gamma generation after revising the spec based on feedback."""
        # First revise the spec
        self.revise_slide_spec(session, slide_index, user_feedback)

        # Then regenerate
        return self.generate_with_gamma(session, slide_index)

    # ============ STEP E: EXPORT ============

    def export_to_pptx(
        self,
        session: Session,
        author: str = "Slide Creator",
    ) -> str:
        """Export all approved slides to PPTX."""
        if not session.current_outline:
            raise ValueError("No outline available")

        session.current_state = FlowState.EXPORT

        # Collect slides data
        slides_data = []
        for progress in session.slide_progress:
            if progress.current_spec:
                slides_data.append((
                    progress.current_spec,
                    progress.gamma_result,  # May be None
                ))

        if not slides_data:
            raise ValueError("No slides to export")

        # Export
        filepath = self.exporter.export_session(
            session_id=session.session_id,
            deck_title=session.current_outline.deck_title,
            slides_data=slides_data,
            author=author,
            subtitle=session.current_outline.deck_subtitle,
        )

        session.output_file = filepath
        session.current_state = FlowState.COMPLETED
        self.save_session(session)

        logger.info(f"Exported presentation to {filepath}")
        return filepath

    # ============ FLOW CONTROL ============

    def get_next_pending_slide(self, session: Session) -> Optional[int]:
        """Get the index of the next slide that needs processing."""
        for i, progress in enumerate(session.slide_progress):
            if not progress.gamma_approved:
                return i
        return None

    def is_all_slides_approved(self, session: Session) -> bool:
        """Check if all slides are approved."""
        return all(sp.gamma_approved for sp in session.slide_progress)

    def get_session_summary(self, session: Session) -> dict:
        """Get a summary of the session state."""
        total_slides = len(session.slide_progress)
        spec_approved = sum(1 for sp in session.slide_progress if sp.spec_approved)
        gamma_approved = sum(1 for sp in session.slide_progress if sp.gamma_approved)

        return {
            "session_id": session.session_id,
            "state": session.current_state.value,
            "storyline_iterations": session.storyline_iterations,
            "outline_iterations": session.outline_iterations,
            "total_slides": total_slides,
            "spec_approved": spec_approved,
            "gamma_approved": gamma_approved,
            "completion_percentage": (gamma_approved / total_slides * 100) if total_slides > 0 else 0,
            "output_file": session.output_file,
        }

    def abort_session(self, session: Session) -> None:
        """Abort the current session."""
        session.current_state = FlowState.ABORTED
        self.save_session(session)
        logger.info(f"Session aborted: {session.session_id}")
