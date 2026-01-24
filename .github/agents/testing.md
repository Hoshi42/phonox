# Testing Strategy

## Overview

Phonox uses a **test pyramid** approach:
- **Unit Tests** (70%): Tools, State Models, Utilities
- **Integration Tests** (20%): Agent Flows, API Endpoints, DB Queries
- **E2E Tests** (10%): Full workflows (mobile → backend → agent → response)

All tests run in Docker containers to ensure consistency.

---

## Unit Tests

### Tool Tests

Each tool must have deterministic, mocked tests.

#### Example: `test_discogs_lookup.py`

```python
import pytest
from unittest.mock import patch, MagicMock
from backend.tools.discogs import DiscogsTool
from backend.models import DiscogsResult, Evidence

@pytest.fixture
def discogs_tool():
    return DiscogsTool(api_key="test_key", rate_limit=1)

def test_discogs_lookup_success(discogs_tool):
    """Valid vinyl record found"""
    mock_response = {
        "results": [{
            "id": 12345,
            "title": "Dark Side of the Moon",
            "artists": [{"name": "Pink Floyd"}],
            "year": 1973,
            "uri": "/releases/12345"
        }]
    }
    
    with patch.object(discogs_tool, 'request', return_value=mock_response):
        result = discogs_tool.lookup("Pink Floyd", "Dark Side of the Moon")
        
        assert isinstance(result, DiscogsResult)
        assert result.confidence >= 0.8
        assert result.year == 1973
        assert isinstance(result.evidence, Evidence)

def test_discogs_lookup_no_match(discogs_tool):
    """No records found"""
    with patch.object(discogs_tool, 'request', return_value={"results": []}):
        result = discogs_tool.lookup("Nonexistent", "Record")
        assert result.confidence < 0.5

def test_discogs_rate_limit(discogs_tool):
    """Rate limit enforced"""
    discogs_tool.lookup("Test", "Record")
    
    with pytest.raises(RateLimitError):
        discogs_tool.lookup("Test", "Record")
```

#### Example: `test_image_extraction.py`

```python
import pytest
from pathlib import Path
from backend.tools.image import ImageFeatureExtractor
from backend.models import ImageFeatures

@pytest.fixture
def extractor():
    return ImageFeatureExtractor(model="vit-base")

@pytest.fixture
def sample_image(tmp_path):
    """Create dummy test image"""
    from PIL import Image
    img = Image.new('RGB', (640, 480), color='red')
    path = tmp_path / "test.jpg"
    img.save(path)
    return path

def test_image_feature_extraction(extractor, sample_image):
    """Features extracted deterministically"""
    features = extractor.extract(sample_image)
    
    assert isinstance(features, ImageFeatures)
    assert len(features.embedding) == 768  # ViT-base
    assert features.dominant_colors is not None
    assert features.text_detected is not None

def test_image_format_validation(extractor):
    """Invalid formats rejected"""
    with pytest.raises(ValueError):
        extractor.extract("not_an_image.txt")
```

### State Model Tests

```python
# test_agent_state.py
import pytest
from backend.agent.state import VinylState, ConfidenceGate
from pydantic import ValidationError

def test_vinyl_state_creation():
    """Valid state created"""
    state = VinylState(
        session_id="sess_123",
        vinyl_id="LP_001",
        images=[],
        metadata={},
        confidence=0.0,
        auto_commit=False
    )
    assert state.session_id == "sess_123"

def test_vinyl_state_validation():
    """Confidence must be 0-1"""
    with pytest.raises(ValidationError):
        VinylState(confidence=1.5)  # Invalid

def test_confidence_gate():
    """Gate logic works"""
    gate = ConfidenceGate(threshold=0.85)
    
    assert gate.should_commit(confidence=0.9) == True
    assert gate.should_commit(confidence=0.8) == False
    assert gate.should_commit(confidence=0.85) == True  # Inclusive
```

---

## Integration Tests

### Agent Flow Tests

Test complete agent workflows with mocked external APIs.

```python
# tests/integration/test_agent_flow.py
import pytest
from unittest.mock import MagicMock, patch
from backend.agent.graph import create_agent_graph
from backend.models import VinylState, DiscogsResult, Evidence
from langchain_core.messages import BaseMessage

@pytest.fixture
def mock_tools():
    """Mocked tool responses"""
    return {
        "discogs": MagicMock(return_value=DiscogsResult(
            confidence=0.9,
            title="Dark Side of the Moon",
            artist="Pink Floyd",
            year=1973,
            evidence=Evidence(source="Discogs API", urls=["https://..."])
        )),
        "musicbrainz": MagicMock(return_value=None),
        "pdf_generator": MagicMock(return_value={"status": "success"})
    }

@pytest.fixture
def agent_graph(mock_tools):
    """Create agent with mocked tools"""
    graph = create_agent_graph()
    # Inject mocked tools
    for node_name, mock in mock_tools.items():
        graph.nodes[node_name].kwargs['tool'] = mock
    return graph.compile()

def test_agent_full_flow_auto_commit(agent_graph, mock_tools):
    """Agent flow: capture → lookup → auto-commit (high confidence)"""
    
    initial_state = {
        "session_id": "test_123",
        "images": ["front.jpg", "spine.jpg"],
        "vinyl_id": None,
        "metadata": {},
        "confidence": 0.0,
        "auto_commit": False,
        "review_reason": None
    }
    
    result = agent_graph.invoke(initial_state)
    
    # Assertions
    assert result["confidence"] >= 0.85
    assert result["auto_commit"] == True
    assert result["vinyl_id"] is not None
    mock_tools["pdf_generator"].assert_called_once()

def test_agent_fallback_to_manual_review(agent_graph, mock_tools):
    """Agent flow: low confidence → manual review required"""
    
    mock_tools["discogs"].return_value = DiscogsResult(
        confidence=0.6,  # Below threshold
        title="Unknown",
        evidence=Evidence(source="Failed lookup")
    )
    
    initial_state = {"images": ["blurry.jpg"], ...}
    result = agent_graph.invoke(initial_state)
    
    assert result["confidence"] < 0.85
    assert result["auto_commit"] == False
    assert result["review_reason"] is not None

def test_agent_tool_retry_logic(agent_graph, mock_tools):
    """Tool fails → agent retries with fallback"""
    
    # First call fails, second succeeds
    mock_tools["discogs"].side_effect = [
        TimeoutError("API timeout"),
        DiscogsResult(confidence=0.8, ...)
    ]
    
    result = agent_graph.invoke(initial_state)
    
    # Should recover and succeed
    assert result["confidence"] >= 0.8
```

### API Endpoint Tests

```python
# tests/integration/test_api_endpoints.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_upload_vinyl_endpoint(client):
    """POST /vinyl/upload returns job_id"""
    with open("test_image.jpg", "rb") as f:
        response = client.post(
            "/vinyl/upload",
            files={"image": f},
            data={"position": "front"}
        )
    
    assert response.status_code == 202
    assert "job_id" in response.json()

def test_get_vinyl_status(client):
    """GET /vinyl/{vinyl_id} returns state"""
    response = client.get("/vinyl/LP_001")
    
    assert response.status_code == 200
    assert "metadata" in response.json()
    assert "confidence" in response.json()

def test_manual_review_endpoint(client):
    """POST /vinyl/{vinyl_id}/review accepts manual correction"""
    response = client.post(
        "/vinyl/LP_001/review",
        json={
            "title": "Corrected Title",
            "artist": "Corrected Artist",
            "approval": True
        }
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "committed"
```

### Database Tests

```python
# tests/integration/test_db.py
import pytest
from backend.db import get_session, VinylRecord

@pytest.fixture
def db_session():
    """Create test DB session"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    return Session()

def test_vinyl_record_persistence(db_session):
    """Record persists to DB"""
    record = VinylRecord(
        title="Test Album",
        artist="Test Artist",
        confidence=0.9
    )
    
    db_session.add(record)
    db_session.commit()
    
    fetched = db_session.query(VinylRecord).filter_by(title="Test Album").first()
    assert fetched.confidence == 0.9

def test_vinyl_record_update(db_session):
    """Record can be updated"""
    record = VinylRecord(title="Original", confidence=0.5)
    db_session.add(record)
    db_session.commit()
    
    record.title = "Updated"
    record.confidence = 0.9
    db_session.commit()
    
    fetched = db_session.query(VinylRecord).filter_by(id=record.id).first()
    assert fetched.title == "Updated"
```

---

## E2E Tests (Optional for Phase 1)

### Mobile App Flow

```python
# tests/e2e/test_mobile_flow.py
import pytest
from selenium import webdriver

@pytest.fixture
def browser():
    driver = webdriver.Chrome()
    yield driver
    driver.quit()

def test_complete_capture_flow(browser):
    """User captures record → agent processes → result shown"""
    
    # Navigate to PWA
    browser.get("http://localhost:5173")
    
    # Capture image (simulated)
    capture_btn = browser.find_element("id", "capture-button")
    capture_btn.click()
    
    # Wait for processing
    browser.implicitly_wait(5)
    
    # Check result
    title_element = browser.find_element("id", "record-title")
    assert title_element.text == "Dark Side of the Moon"
```

---

## Running Tests

### Local (in Docker)

```bash
# All tests
docker compose exec backend pytest tests/ -v

# Specific test file
docker compose exec backend pytest tests/unit/test_discogs_lookup.py -v

# Agent flow tests only
docker compose exec backend pytest tests/integration/test_agent_flow.py -v

# With coverage
docker compose exec backend pytest tests/ --cov=backend --cov-report=html
```

### In CI/CD Pipeline

```bash
# Runs automatically on push
# See .github/workflows/test.yml
```

---

## Test Configuration

### `pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --strict-markers --disable-warnings
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow tests
```

### `conftest.py` (Global Fixtures)

```python
# tests/conftest.py
import pytest
from backend.db import get_session

@pytest.fixture(scope="session")
def test_db():
    """Test database for all tests"""
    from sqlalchemy import create_engine
    engine = create_engine("sqlite:///:memory:")
    # Create tables
    return engine

@pytest.fixture
def mock_llm():
    """Mock LLM responses"""
    from unittest.mock import MagicMock
    return MagicMock()
```

---

## Coverage Goals

| Category | Target | Current |
|----------|--------|---------|
| Unit Tests | 85% | TBD |
| Integration Tests | 70% | TBD |
| Agent Logic | 90% | TBD |
| Tools | 80% | TBD |

---

## Continuous Integration

### GitHub Actions Workflow

Tests run on:
- Every push to `main` and feature branches
- Pull requests
- Scheduled nightly builds

**Failures block merges** to main.

---

## Best Practices

1. **Isolation**: Each test is independent (no shared state)
2. **Mocking**: External APIs always mocked
3. **Determinism**: Tests produce same result every run
4. **Speed**: Target <500ms per unit test
5. **Clarity**: Test names describe exact behavior tested
6. **Idempotency**: Tests can run in any order

---

## Resources

- [Pytest Docs](https://docs.pytest.org/)
- [LangGraph Testing Guide](https://python.langchain.com/docs/langgraph/how-tos/agent-testing/)
- [FastAPI Testing](https://fastapi.tiangolo.com/advanced/testing-dependencies/)
- [Docker Compose + Pytest](https://docs.docker.com/language/python/test-using-compose/)
