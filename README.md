# Slide Creator

AI-powered presentation generator that transforms storylines into professional PowerPoint presentations using top-tier consulting methodology.

## Features

- **Partner Review**: Strategic feedback on your storyline using Pyramid Principle
- **Slide Outline Generation**: Structured deck creation with clear objectives and key messages
- **Framework-Based Design**: 20+ pre-approved consulting frameworks (2x2 Matrix, SCR, Funnel, etc.)
- **Visual Generation**: Integration with Gamma for slide graphics (mock available)
- **PPTX Export**: Professional PowerPoint output with framework-specific layouts
- **Session Management**: Save, resume, and track progress across sessions

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repo-url>
cd Slide-creator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# Required: OPENAI_API_KEY
# Optional: GAMMA_API_KEY (uses mock by default)
```

### 3. Run

```bash
# Start the CLI
python -m app.main

# Or run directly
python app/main.py
```

## Build Standalone Executable (.exe)

You can build a standalone executable that doesn't require Python to be installed.

### Windows

```batch
# Simply run the build script
build.bat
```

Or manually:

```batch
# Activate virtual environment
venv\Scripts\activate

# Build executable
pyinstaller slide_creator.spec --clean --noconfirm

# The executable will be at: dist\SlideCreator.exe
```

### Linux / macOS

```bash
# Make script executable and run
chmod +x build.sh
./build.sh
```

Or manually:

```bash
# Activate virtual environment
source venv/bin/activate

# Build executable
pyinstaller slide_creator.spec --clean --noconfirm

# The executable will be at: dist/SlideCreator
```

### Running the Executable

1. Navigate to the `dist` folder
2. Copy `.env.example` to `.env` and add your `OPENAI_API_KEY`
3. Run `SlideCreator.exe` (Windows) or `./SlideCreator` (Linux/Mac)

```
dist/
├── SlideCreator.exe    # The executable
├── .env                # Your configuration (create from .env.example)
├── output/             # Generated presentations
├── sessions/           # Saved sessions
└── logs/               # LLM call logs
```

**Note**: The first run may take a moment to start as it extracts bundled files.

## Usage Flow

### Step A: Partner Review
Enter your storyline and receive strategic feedback:
- Overall assessment
- Strengths and gaps
- Risks and recommendations
- Clarifying questions

### Step B: Slide Outline
Generate a structured deck outline:
- Deck title and subtitle
- Individual slides with:
  - Title (insight-driven)
  - Objective
  - Key message
  - Supporting bullets
  - Evidence needed

### Step C: Slide Design Spec
For each slide, the system:
1. Selects the most appropriate framework from 20+ options
2. Structures content to fit the framework
3. Generates detailed layout and copy specifications

### Step D: Gamma Generation
Generate visual slides using Gamma API:
- Converts spec to Gamma-compatible format
- Returns structured content or images
- Supports iterative refinement

### Step E: PPTX Export
Export to PowerPoint:
- Framework-specific layouts
- Consistent styling
- Speaker notes support
- Metadata (author, date)

## Project Structure

```
Slide-creator/
├── app/
│   ├── __init__.py
│   ├── main.py           # CLI entrypoint
│   ├── models.py         # Pydantic data models
│   ├── orchestrator.py   # State machine / flow control
│   ├── llm_client.py     # OpenAI API wrapper
│   ├── gamma_client.py   # Gamma API (with mock)
│   ├── pptx_exporter.py  # PPTX generation
│   ├── prompts.py        # LLM prompt templates
│   ├── state_store.py    # Session persistence
│   └── frameworks.json   # Pre-approved frameworks
├── tests/
│   └── test_*.py         # Unit tests
├── output/               # Generated PPTX files
├── sessions/             # Session state files
├── logs/                 # LLM call logs
├── requirements.txt
├── .env.example
├── sample_storyline.txt
└── README.md
```

## Available Frameworks

| ID | Framework | Best For |
|----|-----------|----------|
| pyramid_executive_summary | Pyramid / Executive Summary | Key recommendations, openings |
| scr | Situation-Complication-Resolution | Problem statements, proposals |
| 2x2_matrix | 2x2 Matrix | Prioritization, segmentation |
| mece_issue_tree | MECE Issue Tree | Problem decomposition |
| value_chain | Value Chain | Operations, competitive advantage |
| customer_journey | Customer Journey | CX improvement, service design |
| funnel | Funnel | Sales pipeline, conversion |
| timeline_roadmap | Timeline / Roadmap | Project planning, milestones |
| before_after_bridge | Before-After-Bridge | Transformation cases |
| pros_cons_tradeoff | Pros/Cons | Decision support |
| benchmark_table | Benchmark Table | Competitive analysis |
| waterfall_gantt | Waterfall / Gantt | Project schedules |
| kpi_scorecard | KPI Scorecard | Performance dashboards |
| heatmap | Heatmap | Risk, performance mapping |
| porter_5_forces | Porter 5 Forces | Industry analysis |
| swot | SWOT Analysis | Strategic planning |
| logic_model | Logic Model | Program design, impact |
| single_message | Single Key Message | Transitions, emphasis |
| data_chart | Data Visualization | Quantitative insights |
| agenda_toc | Agenda / TOC | Navigation, structure |

## Configuration Options

Environment variables (`.env`):

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE_REVIEW=0.4
OPENAI_TEMPERATURE_OUTLINE=0.5
OPENAI_TEMPERATURE_SPEC=0.6

# Gamma
GAMMA_API_KEY=...
GAMMA_API_URL=https://api.gamma.app/v1
GAMMA_USE_MOCK=true

# Limits
MAX_STORYLINE_ITERATIONS=3
MAX_OUTLINE_ITERATIONS=5
MAX_SLIDE_SPEC_ITERATIONS=5
MAX_GAMMA_ITERATIONS=3

# Output
OUTPUT_DIR=./output
SESSIONS_DIR=./sessions
LOGS_DIR=./logs

# Presentation Defaults
DEFAULT_FONT=Calibri
DEFAULT_FONT_SIZE_TITLE=28
DEFAULT_FONT_SIZE_BODY=14
DEFAULT_MARGIN_INCHES=0.5
```

## API Integration

### OpenAI

The system uses OpenAI's API for:
- Partner review generation
- Slide outline creation
- Slide spec design

Features:
- Structured JSON output
- Temperature control per step
- Retry with exponential backoff
- JSON repair for malformed responses

### Gamma (Mock Available)

The Gamma client supports:
- Real API (when available)
- Mock adapter for development

Mock features:
- Realistic delays
- Framework-specific element generation
- Configurable failure rate for testing

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_models.py
```

## Session Management

Sessions are automatically saved to `./sessions/` as JSON files.

Resume a session:
1. Run the CLI
2. Select "resume"
3. Choose from available sessions

Session files contain:
- Complete state history
- All LLM responses
- Current progress

## Logging

LLM calls are logged to `./logs/` for audit purposes:
- Request payloads (redacted if sensitive)
- Response content
- Timestamps

## Troubleshooting

### "OPENAI_API_KEY not found"
Ensure your `.env` file exists and contains a valid API key.

### JSON parse errors
The system automatically attempts to repair malformed JSON. If persistent, check the logs.

### Gamma generation fails
Set `GAMMA_USE_MOCK=true` in `.env` to use the mock adapter.

### Session not loading
Check the `./sessions/` directory for the session file. Ensure the JSON is valid.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## License

MIT License - see LICENSE file for details.
