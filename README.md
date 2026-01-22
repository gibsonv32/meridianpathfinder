# MERIDIAN Pathfinder

**MERIDIAN** (Mode-Enabled Recursive Intelligence for Data Insight and AI Narratives) is a comprehensive ML pipeline framework that guides projects from opportunity discovery through production deployment.

## Features

- **10 Progressive Modes**: Structured workflow from ideation (Mode 0.5) to delivery (Mode 7)
- **Automated Gate Control**: Enforced prerequisites and artifact dependencies
- **Provenance Tracking**: Complete fingerprinting and lineage for all artifacts
- **LLM Integration**: Intelligent narrative generation and decision support
- **Production-Ready Scaffold**: Automatically generates runnable ML code

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/meridianpathfinder.git
cd meridianpathfinder

# Install with uv (recommended)
uv sync
uv run meridian --help

# Or with pip
pip install -e .
```

### Initialize a New Project

```bash
# Create a new directory for your project
mkdir my-ml-project
cd my-ml-project

# Initialize MERIDIAN project structure
meridian init --name "My ML Project"

# This creates:
# - meridian.yaml (configuration)
# - .meridian/ (artifacts and state)
# - data/ (for your datasets)
# - .gitignore (sensible defaults)
```

### Configure LLM Provider

MERIDIAN uses LLMs for intelligent narrative generation. Configure your provider:

```bash
# Set provider (anthropic or ollama)
meridian llm set-provider anthropic
meridian llm set-model claude-3-haiku-20240307

# Test connection
meridian llm test

# Set API key (via environment variable)
export ANTHROPIC_API_KEY="your-api-key-here"
```

### Run Your First Pipeline

1. **Place your data**:
```bash
cp /path/to/your/data.csv data/
```

2. **Start with Mode 0.5 (Opportunity Discovery)**:
```bash
meridian mode 0.5 run \
  --problem "Reduce customer churn by 20%" \
  --target-entity "customer" \
  --candidate "predictive:ML model to identify at-risk customers"
```

3. **Continue through the modes** to build your complete ML solution.

### Run the Demo

See MERIDIAN in action with a single command:

```bash
# Run complete demo with sample data
meridian demo \
  --data data/sample.csv \
  --target "target_column" \
  --row '{"feature1": 0.5, "feature2": 1.2}' \
  --verify
```

## Understanding MERIDIAN Modes

### Mode Flow

```
0.5 Opportunity → 0 EDA → 1 Decision → 2 Feasibility → 3 Strategy
    ↓                                                         ↓
    4 Business Case → 5 Code Gen → 6 Execution → 6.5 Interpret → 7 Delivery
```

### Mode Descriptions

| Mode | Name | Purpose | Key Artifacts |
|------|------|---------|---------------|
| 0.5 | Opportunity Discovery | Define business problem and ML opportunities | OpportunityBacklog, OpportunityBrief |
| 0 | Exploratory Data Analysis | Understand data characteristics | Mode0GatePacket |
| 1 | Decision Intelligence | Frame hypotheses and success criteria | DecisionIntelProfile |
| 2 | Feasibility Study | Assess ML viability | FeasibilityReport |
| 3 | Strategy | Design features and model approach | ModelRecommendations, FeatureRegistry |
| 4 | Business Case | Define success metrics and thresholds | BusinessCaseScorecard, ThresholdFramework |
| 5 | Code Generation | Generate production ML code | CodeGenerationPlan, PROJECT/ scaffold |
| 6 | Execution | Validate generated code | ExecutionOpsScorecard |
| 6.5 | Interpretation | Generate insights and explanations | InterpretationPackage |
| 7 | Delivery | Package final deliverables | DeliveryManifest |

## Working with Artifacts

### List Artifacts

```bash
# Show all artifacts
meridian artifacts list

# Filter by type
meridian artifacts list --type FeasibilityReport

# Filter by mode
meridian artifacts list --mode 2

# Show only latest per type with verification
meridian artifacts list --latest-per-type --verify
```

### View Specific Artifacts

```bash
# By type (shows latest)
meridian artifacts show --type BusinessCaseScorecard

# By ID
meridian artifacts show --id 8668a37f-f708-4c21-8759-21e1f12e202b

# By file path
meridian artifacts show --file .meridian/artifacts/mode_4/BusinessCaseScorecard_*.json
```

## Project Status

Check your project status anytime:

```bash
meridian status
```

This shows:
- Current mode
- Completion status for each mode
- Gate verdicts
- Associated artifacts

## Environment Variables

- `ANTHROPIC_API_KEY`: API key for Anthropic Claude (do not hardcode keys)
- `OLLAMA_HOST`: Ollama server URL (default: http://localhost:11434)

## Development

For development setup and contribution guidelines, see CONTRIBUTING.md.

## License

MIT License - see LICENSE file for details.

