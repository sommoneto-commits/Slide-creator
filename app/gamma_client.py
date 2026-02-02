"""
Gamma API client with mock adapter.
Handles slide generation via Gamma API or mock for development.
"""
import json
import logging
import os
import time
import uuid
from abc import ABC, abstractmethod
from typing import Optional

import httpx

from app.models import SlideSpec, GammaSlideResult

logger = logging.getLogger(__name__)


class GammaClientBase(ABC):
    """Abstract base class for Gamma client implementations."""

    @abstractmethod
    def generate_slide(self, slide_spec: SlideSpec) -> GammaSlideResult:
        """Generate a slide from specification."""
        pass

    @abstractmethod
    def get_slide_status(self, gamma_id: str) -> dict:
        """Check status of a slide generation job."""
        pass

    def spec_to_payload(self, slide_spec: SlideSpec) -> dict:
        """Convert SlideSpec to Gamma API payload format."""
        # Base transformation - can be overridden by implementations
        payload = {
            "title": slide_spec.title,
            "framework": slide_spec.framework_id,
            "content": {
                "headline": slide_spec.copy.headline,
                "body": slide_spec.copy.body,
                "footnotes": slide_spec.copy.footnotes or [],
            },
            "layout": {
                "sections": [
                    {
                        "name": section.name,
                        "type": section.content_type,
                        "content": section.content,
                        "position": section.position,
                    }
                    for section in slide_spec.layout.sections
                ],
                "visual_notes": slide_spec.layout.visual_notes,
            },
            "data_visualization": {
                "type": slide_spec.data_viz.type if slide_spec.data_viz else "none",
                "spec": slide_spec.data_viz.spec if slide_spec.data_viz else {},
            },
        }
        return payload

    def spec_to_markdown(self, slide_spec: SlideSpec) -> str:
        """Convert SlideSpec to markdown format for Gamma."""
        lines = [
            f"# {slide_spec.title}",
            "",
            f"**Framework:** {slide_spec.framework_name}",
            "",
            f"## {slide_spec.copy.headline}",
            "",
        ]

        for item in slide_spec.copy.body:
            lines.append(f"- {item}")

        lines.append("")

        if slide_spec.layout.sections:
            lines.append("## Content Sections")
            for section in slide_spec.layout.sections:
                lines.append(f"### {section.name}")
                lines.append(f"*Type: {section.content_type}*")
                lines.append(section.content)
                lines.append("")

        if slide_spec.copy.footnotes:
            lines.append("---")
            for fn in slide_spec.copy.footnotes:
                lines.append(f"_{fn}_")

        return "\n".join(lines)


class MockGammaClient(GammaClientBase):
    """
    Mock Gamma client for development and testing.
    Simulates Gamma API behavior with realistic delays and responses.
    """

    def __init__(self, simulate_delay: bool = True, failure_rate: float = 0.0):
        self.simulate_delay = simulate_delay
        self.failure_rate = failure_rate  # Probability of simulated failure (0.0-1.0)
        self._slides: dict = {}  # In-memory storage for mock slides
        logger.info("MockGammaClient initialized")

    def generate_slide(self, slide_spec: SlideSpec) -> GammaSlideResult:
        """Generate a mock slide from specification."""
        import random

        # Simulate API delay
        if self.simulate_delay:
            delay = random.uniform(0.5, 2.0)
            logger.debug(f"Simulating Gamma API delay: {delay:.2f}s")
            time.sleep(delay)

        # Simulate occasional failures
        if random.random() < self.failure_rate:
            logger.warning("Simulating Gamma API failure")
            return GammaSlideResult(
                slide_id=slide_spec.slide_id,
                success=False,
                error_message="Simulated Gamma API error - please retry",
            )

        # Generate mock result
        gamma_id = f"gamma_{uuid.uuid4().hex[:12]}"

        # Create structured content that represents what Gamma would return
        structured_content = {
            "slide_id": slide_spec.slide_id,
            "gamma_id": gamma_id,
            "title": slide_spec.title,
            "framework_applied": slide_spec.framework_id,
            "elements": self._generate_mock_elements(slide_spec),
            "theme": {
                "background": "#FFFFFF",
                "primary_color": "#1A73E8",
                "font_family": "Calibri",
            },
            "dimensions": {"width": 1920, "height": 1080},
        }

        # Store for later retrieval
        self._slides[gamma_id] = structured_content

        result = GammaSlideResult(
            slide_id=slide_spec.slide_id,
            success=True,
            structured_content=structured_content,
            gamma_id=gamma_id,
            # In a real implementation, image_url would point to rendered slide
            image_url=f"https://mock.gamma.app/slides/{gamma_id}/preview.png",
        )

        logger.info(f"Mock slide generated: {gamma_id} for slide {slide_spec.slide_id}")
        return result

    def _generate_mock_elements(self, slide_spec: SlideSpec) -> list:
        """Generate mock visual elements based on framework."""
        elements = []

        # Title element
        elements.append({
            "type": "text",
            "role": "title",
            "content": slide_spec.title,
            "position": {"x": 50, "y": 50, "width": 1820, "height": 80},
            "style": {"fontSize": 36, "fontWeight": "bold"},
        })

        # Headline element
        elements.append({
            "type": "text",
            "role": "headline",
            "content": slide_spec.copy.headline,
            "position": {"x": 50, "y": 150, "width": 1820, "height": 60},
            "style": {"fontSize": 24, "fontWeight": "semibold"},
        })

        # Generate framework-specific elements
        framework_elements = self._generate_framework_elements(slide_spec)
        elements.extend(framework_elements)

        # Body content
        y_offset = 700
        for i, body_item in enumerate(slide_spec.copy.body[:5]):
            elements.append({
                "type": "text",
                "role": "bullet",
                "content": f"• {body_item}",
                "position": {"x": 50, "y": y_offset + (i * 40), "width": 1820, "height": 35},
                "style": {"fontSize": 16},
            })

        # Footnotes
        if slide_spec.copy.footnotes:
            elements.append({
                "type": "text",
                "role": "footnote",
                "content": " | ".join(slide_spec.copy.footnotes),
                "position": {"x": 50, "y": 1020, "width": 1820, "height": 30},
                "style": {"fontSize": 10, "color": "#666666"},
            })

        return elements

    def _generate_framework_elements(self, slide_spec: SlideSpec) -> list:
        """Generate mock elements specific to the framework."""
        elements = []
        framework = slide_spec.framework_id

        if framework == "2x2_matrix":
            # Create 2x2 grid
            elements.append({
                "type": "shape",
                "role": "matrix_grid",
                "shape_type": "grid_2x2",
                "position": {"x": 200, "y": 250, "width": 800, "height": 400},
                "labels": {
                    "top_left": "High Impact / Low Effort",
                    "top_right": "High Impact / High Effort",
                    "bottom_left": "Low Impact / Low Effort",
                    "bottom_right": "Low Impact / High Effort",
                },
            })

        elif framework == "funnel":
            elements.append({
                "type": "shape",
                "role": "funnel",
                "shape_type": "funnel",
                "position": {"x": 400, "y": 250, "width": 400, "height": 400},
                "stages": ["Awareness", "Interest", "Decision", "Action"],
            })

        elif framework == "timeline_roadmap":
            elements.append({
                "type": "shape",
                "role": "timeline",
                "shape_type": "horizontal_timeline",
                "position": {"x": 100, "y": 350, "width": 1720, "height": 200},
                "milestones": ["Q1", "Q2", "Q3", "Q4"],
            })

        elif framework == "kpi_scorecard":
            elements.append({
                "type": "shape",
                "role": "scorecard",
                "shape_type": "kpi_grid",
                "position": {"x": 100, "y": 250, "width": 1720, "height": 400},
                "kpis": [
                    {"name": "KPI 1", "value": "85%", "status": "green"},
                    {"name": "KPI 2", "value": "72%", "status": "yellow"},
                    {"name": "KPI 3", "value": "95%", "status": "green"},
                ],
            })

        elif framework in ["scr", "before_after_bridge"]:
            # Three-column layout
            labels = (
                ["Situation", "Complication", "Resolution"]
                if framework == "scr"
                else ["Before", "After", "Bridge"]
            )
            for i, label in enumerate(labels):
                elements.append({
                    "type": "shape",
                    "role": "column",
                    "shape_type": "rounded_rectangle",
                    "position": {"x": 100 + (i * 600), "y": 250, "width": 550, "height": 400},
                    "label": label,
                })

        elif framework == "pros_cons_tradeoff":
            # Two-column layout
            for i, label in enumerate(["Pros", "Cons"]):
                elements.append({
                    "type": "shape",
                    "role": "column",
                    "shape_type": "rounded_rectangle",
                    "position": {"x": 100 + (i * 900), "y": 250, "width": 800, "height": 400},
                    "label": label,
                    "color": "#4CAF50" if label == "Pros" else "#F44336",
                })

        # Add content sections from spec
        for section in slide_spec.layout.sections:
            elements.append({
                "type": "content_block",
                "name": section.name,
                "content_type": section.content_type,
                "content": section.content,
            })

        return elements

    def get_slide_status(self, gamma_id: str) -> dict:
        """Get status of a mock slide."""
        if gamma_id in self._slides:
            return {
                "status": "completed",
                "gamma_id": gamma_id,
                "slide": self._slides[gamma_id],
            }
        return {
            "status": "not_found",
            "gamma_id": gamma_id,
        }


class RealGammaClient(GammaClientBase):
    """
    Real Gamma API client.
    TODO: Implement when Gamma API documentation is available.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("GAMMA_API_KEY")
        self.api_url = api_url or os.getenv("GAMMA_API_URL", "https://api.gamma.app/v1")

        if not self.api_key:
            raise ValueError("GAMMA_API_KEY not found")

        self.client = httpx.Client(
            base_url=self.api_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

        logger.info(f"RealGammaClient initialized with URL: {self.api_url}")

    def generate_slide(self, slide_spec: SlideSpec) -> GammaSlideResult:
        """
        Generate a slide using Gamma API.
        TODO: Implement actual API call when documentation is available.
        """
        # Placeholder implementation
        # In production, this would:
        # 1. Convert slide_spec to Gamma's expected format
        # 2. POST to Gamma API
        # 3. Poll for completion or wait for webhook
        # 4. Return the result with image URL or structured content

        try:
            payload = self.spec_to_payload(slide_spec)

            # TODO: Replace with actual Gamma API endpoint
            # response = self.client.post("/slides/generate", json=payload)
            # response.raise_for_status()
            # result_data = response.json()

            # For now, return error indicating real API not implemented
            return GammaSlideResult(
                slide_id=slide_spec.slide_id,
                success=False,
                error_message="Real Gamma API not yet implemented. Set GAMMA_USE_MOCK=true",
            )

        except Exception as e:
            logger.error(f"Gamma API error: {e}")
            return GammaSlideResult(
                slide_id=slide_spec.slide_id,
                success=False,
                error_message=str(e),
            )

    def get_slide_status(self, gamma_id: str) -> dict:
        """Check status of a slide generation job."""
        # TODO: Implement actual status check
        return {
            "status": "not_implemented",
            "gamma_id": gamma_id,
        }


def get_gamma_client(use_mock: Optional[bool] = None) -> GammaClientBase:
    """
    Factory function to get the appropriate Gamma client.
    Returns MockGammaClient if GAMMA_USE_MOCK is true or no API key is set.
    """
    if use_mock is None:
        use_mock = os.getenv("GAMMA_USE_MOCK", "true").lower() == "true"

    if use_mock:
        logger.info("Using MockGammaClient")
        return MockGammaClient()

    # Check for API key before returning real client
    if not os.getenv("GAMMA_API_KEY"):
        logger.warning("GAMMA_API_KEY not set, falling back to MockGammaClient")
        return MockGammaClient()

    return RealGammaClient()
