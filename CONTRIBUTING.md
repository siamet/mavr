# Contributing to Multi-Agent Code Review

Thank you for your interest in contributing to this research project! This guide will help you get started.

## 🎯 Project Overview

This is an academic research project developing a multi-agent AI system for automated code review and refactoring. The system uses:
- **Graph Neural Networks (GNN)** for architecture analysis
- **Fine-tuned LLM (CodeLlama-7B)** for maintainability assessment
- **Static analysis** for performance and security
- **Reinforcement Learning (PPO)** for multi-agent orchestration

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- 16GB+ RAM recommended
- GPU with 16GB VRAM (for model training, optional for general development)

### Environment Setup

```bash
# Clone the repository
git clone https://github.com/siamet/multi-agent-code-review.git
cd multi-agent-code-review

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install tree-sitter parsers
python scripts/setup_parsers.py

# Run tests to verify setup
pytest tests/
```

## 📋 Development Workflow

### 1. Find or Create an Issue

- Check existing [issues](https://github.com/[username]/multi-agent-code-review/issues)
- Comment on an issue to claim it
- For new features, create an issue first to discuss the approach

### 2. Create a Feature Branch

```bash
git checkout -b feature/descriptive-name
```

Branch naming conventions:
- `feature/[name]` - New features
- `fix/[name]` - Bug fixes
- `docs/[name]` - Documentation updates
- `refactor/[name]` - Code refactoring

### 3. Make Your Changes

Follow our coding standards (see below) and ensure:
- Code is well-documented
- Tests are included
- Linting passes
- Type hints are used

### 4. Test Your Changes

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src --cov-report=html tests/

# Run specific test file
pytest tests/test_agents/test_architecture_agent.py -v

# Run linting
ruff format src/ tests/
ruff check src/ tests/
mypy src/
```

### 5. Commit Your Changes

Follow conventional commit format:

```
type(scope): brief description

Detailed explanation if needed

- List any breaking changes
- Reference related issues (#123)
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Examples**:
```bash
git commit -m "feat(gnn): add graph attention layer for code dependencies"
git commit -m "fix(parser): handle nested class definitions in tree-sitter"
git commit -m "docs(api): update FastAPI endpoint documentation"
```

### 6. Submit a Pull Request

```bash
# Push your branch
git push origin feature/descriptive-name

# Create PR on GitHub
# - Use descriptive title following commit convention
# - Reference related issues
# - Describe changes and rationale
# - Add screenshots/examples if applicable
```

## 🏗️ Code Standards

### Python Style (PEP 8)

- **Max line length**: 100 characters
- **Indentation**: 4 spaces
- **Function length**: Under 50 lines
- **File length**: Under 500 lines
- **Naming**:
  - `snake_case` for variables/functions
  - `PascalCase` for classes
  - `UPPER_SNAKE_CASE` for constants
  - `_leading_underscore` for private members

### Type Hints

Always use type hints for function signatures:

```python
from typing import List, Dict, Optional

def analyze_function(
    code: str,
    language: str = "python",
    options: Optional[Dict[str, bool]] = None
) -> List[Issue]:
    """Analyze function for code smells.

    Args:
        code: Source code to analyze
        language: Programming language (default: python)
        options: Additional analysis options

    Returns:
        List of detected issues

    Raises:
        ValueError: If language is not supported
    """
    pass
```

### Documentation (Docstrings)

Use Google-style docstrings for all public functions/classes:

```python
"""Brief one-line description.

Detailed multi-line description if needed.
Explain the purpose, behavior, and any important details.

Args:
    param1: Description of first parameter
    param2: Description of second parameter

Returns:
    Description of return value

Raises:
    ExceptionType: When and why this exception is raised

Example:
    >>> result = my_function("input")
    >>> print(result)
    "output"
"""
```

### Error Handling

- Use specific exception types
- Provide meaningful error messages
- Log errors with context
- Fail fast - validate inputs early

```python
import logging

logger = logging.getLogger(__name__)

def process_code(code: str) -> Result:
    if not code or not code.strip():
        raise ValueError("Code cannot be empty")

    try:
        result = parse_code(code)
    except ParseError as e:
        logger.error(f"Failed to parse code: {e}", exc_info=True)
        raise

    return result
```

## 🧪 Testing Guidelines

### Test Structure

- **Unit tests**: Test individual functions/classes in isolation
- **Integration tests**: Test component interactions
- **End-to-end tests**: Test complete workflows

### Writing Tests

```python
import pytest
from src.agents.architecture_agent import ArchitectureAgent

class TestArchitectureAgent:
    """Test suite for ArchitectureAgent."""

    @pytest.fixture
    def agent(self):
        """Create agent instance for testing."""
        return ArchitectureAgent()

    def test_analyze_simple_function(self, agent):
        """Test analysis of simple function."""
        code = """
        def add(a, b):
            return a + b
        """
        issues = agent.analyze(code)
        assert len(issues) == 0

    def test_detect_long_parameter_list(self, agent):
        """Test detection of long parameter list smell."""
        code = """
        def process(a, b, c, d, e, f, g, h):
            return a + b + c + d + e + f + g + h
        """
        issues = agent.analyze(code)
        assert any(issue.type == "long_parameter_list" for issue in issues)
```

### Property-Based Testing

Use Hypothesis for complex logic:

```python
from hypothesis import given, strategies as st

@given(st.text())
def test_parser_handles_any_input(code: str):
    """Parser should handle any string input without crashing."""
    result = parse_code(code)
    assert result is not None
```

## 🤝 Contribution Areas

We welcome contributions in these areas:

### 🔧 Core Development
- Implementing agents (Architecture, Performance, Security, Maintainability)
- Building parsing infrastructure (tree-sitter integration)
- Developing refactoring execution engine
- Creating knowledge graph construction

### 🧠 Machine Learning
- Training GNN models for code analysis
- Fine-tuning CodeLlama for maintainability assessment
- Developing RL orchestrator (PPO-based)
- Creating feature extraction pipelines

### 📊 Data & Evaluation
- Curating benchmark dataset (25 repos)
- Labeling code smells and refactorings
- Creating evaluation scripts
- Running ablation studies

### 🌐 API & Frontend
- Building FastAPI endpoints
- Creating React + D3.js visualization dashboard
- Developing CLI interface
- Writing API documentation

### 📚 Documentation
- Writing user guides
- Creating API documentation
- Adding code examples
- Improving CLAUDE.md context

### 🧪 Testing
- Writing unit tests
- Creating integration tests
- Developing property-based tests
- Building test fixtures and utilities

## 🎓 Research Context


### Novel Contributions
1. Multi-agent architecture with heterogeneous AI/ML techniques
2. RL-based orchestration for refactoring prioritization
3. GNN for code structure analysis
4. Automated semantic verification pipeline
5. Cross-language transfer learning

### Academic Standards
- All claims must be backed by empirical evaluation
- Code must be reproducible
- Experiments must be documented
- Ethical considerations must be addressed

## 📖 Resources

### Documentation
- [README.md](README.md) - Project overview
- [PRD.md](PRD.md) - Product requirements
- [ROADMAP.md](ROADMAP.md) - Development roadmap
- [CLAUDE.md](CLAUDE.md) - AI development context

### Key Technologies
- [PyTorch](https://pytorch.org/docs/) - Deep learning framework
- [DGL](https://docs.dgl.ai/) - Graph neural networks
- [tree-sitter](https://tree-sitter.github.io/tree-sitter/) - Code parsing
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [Stable-Baselines3](https://stable-baselines3.readthedocs.io/) - RL algorithms

### Communication
- **Issues**: Bug reports and feature requests
- **Discussions**: General questions and ideas
- **Pull Requests**: Code contributions

## ⚖️ Code of Conduct

### Our Standards
- Be respectful and inclusive
- Focus on constructive feedback
- Accept differing viewpoints
- Prioritize community well-being
- Maintain professional conduct

### Unacceptable Behavior
- Harassment or discrimination
- Trolling or inflammatory comments
- Personal attacks
- Publishing private information
- Unprofessional conduct

## 📝 License

By contributing, you agree that your contributions will be licensed under the same license as the project (see [LICENSE](LICENSE) file).

## 🙏 Recognition

Contributors will be acknowledged in:
- Project README
- Research paper acknowledgments (for significant contributions)
- Release notes

Thank you for contributing to advancing automated code quality research!

---

*For questions, contact the maintainers or open a discussion.*
