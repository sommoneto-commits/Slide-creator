"""
Tests for Gamma client.
"""
import pytest

from app.gamma_client import MockGammaClient, get_gamma_client
from app.models import (
    SlideSpec,
    SlideLayout,
    SlideCopy,
    ContentSection,
    DataVizSpec,
)


class TestMockGammaClient:
    @pytest.fixture
    def client(self):
        return MockGammaClient(simulate_delay=False, failure_rate=0.0)

    @pytest.fixture
    def sample_spec(self):
        return SlideSpec(
            slide_id="S01",
            title="Test Slide",
            framework_id="2x2_matrix",
            framework_name="2x2 Matrix",
            rationale="Good for comparison",
            layout=SlideLayout(
                sections=[
                    ContentSection(
                        name="Quadrant 1",
                        content_type="text",
                        content="High impact, low effort",
                    ),
                    ContentSection(
                        name="Quadrant 2",
                        content_type="text",
                        content="High impact, high effort",
                    ),
                ],
                visual_notes="Use blue theme",
            ),
            copy=SlideCopy(
                headline="Strategic Priorities",
                body=["Focus on quick wins", "Plan for big bets"],
                footnotes=["Source: Analysis"],
            ),
            data_viz=DataVizSpec(type="none"),
        )

    def test_generate_slide_success(self, client, sample_spec):
        result = client.generate_slide(sample_spec)

        assert result.success is True
        assert result.slide_id == "S01"
        assert result.gamma_id is not None
        assert result.gamma_id.startswith("gamma_")
        assert result.structured_content is not None

    def test_generate_slide_structured_content(self, client, sample_spec):
        result = client.generate_slide(sample_spec)

        content = result.structured_content
        assert "elements" in content
        assert "title" in content
        assert content["framework_applied"] == "2x2_matrix"

    def test_generate_slide_elements(self, client, sample_spec):
        result = client.generate_slide(sample_spec)

        elements = result.structured_content["elements"]
        # Should have title, headline, framework elements, body, etc.
        assert len(elements) > 0

        # Check for title element
        title_elements = [e for e in elements if e.get("role") == "title"]
        assert len(title_elements) == 1

    def test_get_slide_status(self, client, sample_spec):
        result = client.generate_slide(sample_spec)
        status = client.get_slide_status(result.gamma_id)

        assert status["status"] == "completed"
        assert status["gamma_id"] == result.gamma_id

    def test_get_slide_status_not_found(self, client):
        status = client.get_slide_status("nonexistent")
        assert status["status"] == "not_found"

    def test_spec_to_payload(self, client, sample_spec):
        payload = client.spec_to_payload(sample_spec)

        assert payload["title"] == "Test Slide"
        assert payload["framework"] == "2x2_matrix"
        assert "content" in payload
        assert payload["content"]["headline"] == "Strategic Priorities"

    def test_spec_to_markdown(self, client, sample_spec):
        markdown = client.spec_to_markdown(sample_spec)

        assert "# Test Slide" in markdown
        assert "Strategic Priorities" in markdown
        assert "Focus on quick wins" in markdown

    def test_failure_rate(self):
        # Create client with 100% failure rate
        client = MockGammaClient(simulate_delay=False, failure_rate=1.0)
        spec = SlideSpec(
            slide_id="S01",
            title="Test",
            framework_id="test",
            framework_name="Test",
            rationale="Test",
            layout=SlideLayout(sections=[]),
            copy=SlideCopy(headline="Test", body=[]),
        )

        result = client.generate_slide(spec)
        assert result.success is False
        assert result.error_message is not None


class TestFrameworkSpecificElements:
    @pytest.fixture
    def client(self):
        return MockGammaClient(simulate_delay=False)

    def create_spec(self, framework_id: str, framework_name: str) -> SlideSpec:
        return SlideSpec(
            slide_id="S01",
            title="Test",
            framework_id=framework_id,
            framework_name=framework_name,
            rationale="Test",
            layout=SlideLayout(
                sections=[
                    ContentSection(name=f"Section {i}", content_type="text", content=f"Content {i}")
                    for i in range(4)
                ]
            ),
            copy=SlideCopy(headline="Test", body=["Point 1", "Point 2"]),
        )

    def test_2x2_matrix_elements(self, client):
        spec = self.create_spec("2x2_matrix", "2x2 Matrix")
        result = client.generate_slide(spec)

        elements = result.structured_content["elements"]
        matrix_elements = [e for e in elements if e.get("role") == "matrix_grid"]
        assert len(matrix_elements) == 1

    def test_funnel_elements(self, client):
        spec = self.create_spec("funnel", "Funnel")
        result = client.generate_slide(spec)

        elements = result.structured_content["elements"]
        funnel_elements = [e for e in elements if e.get("role") == "funnel"]
        assert len(funnel_elements) == 1

    def test_timeline_elements(self, client):
        spec = self.create_spec("timeline_roadmap", "Timeline")
        result = client.generate_slide(spec)

        elements = result.structured_content["elements"]
        timeline_elements = [e for e in elements if e.get("role") == "timeline"]
        assert len(timeline_elements) == 1

    def test_scr_elements(self, client):
        spec = self.create_spec("scr", "SCR")
        result = client.generate_slide(spec)

        elements = result.structured_content["elements"]
        column_elements = [e for e in elements if e.get("role") == "column"]
        assert len(column_elements) == 3


class TestGetGammaClient:
    def test_get_mock_client(self, monkeypatch):
        monkeypatch.setenv("GAMMA_USE_MOCK", "true")
        client = get_gamma_client()
        assert isinstance(client, MockGammaClient)

    def test_get_mock_when_no_api_key(self, monkeypatch):
        monkeypatch.setenv("GAMMA_USE_MOCK", "false")
        monkeypatch.delenv("GAMMA_API_KEY", raising=False)
        client = get_gamma_client()
        assert isinstance(client, MockGammaClient)

    def test_explicit_mock_parameter(self):
        client = get_gamma_client(use_mock=True)
        assert isinstance(client, MockGammaClient)
