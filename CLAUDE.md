# CLAUDE.md - AI Development Context

This file provides comprehensive guidance to Claude Code when working with this repository. It defines coding standards, development practices, and project-specific context that should persist across all sessions.

## 🎯 Quick Session Start
- Use `/status` to check current progress and priorities
- Use `/prime` for comprehensive project analysis and context updates
- Current development focus: **Phase 2 — Individual Agent Development**
- Active development phase: **Phase 2 (Phases 0–1 complete)**

---

## 🧱 Core Development Philosophy

### KISS (Keep It Simple, Stupid)
Simplicity should be a key goal in design. Choose straightforward solutions over complex ones whenever possible. Simple solutions are easier to understand, maintain, and debug.

### YAGNI (You Aren't Gonna Need It)
Avoid building functionality on speculation. Implement features only when they are needed, not when you anticipate they might be useful in the future.

### Design Principles
- **Dependency Inversion**: High-level modules should not depend on low-level modules. Both should depend on abstractions.
- **Open/Closed Principle**: Software entities should be open for extension but closed for modification.
- **Single Responsibility**: Each function, class, and module should have one clear purpose.
- **Fail Fast**: Check for potential errors early and raise exceptions immediately when issues occur.

---

## 🏗️ Code Structure & Standards

### File and Function Limits
- **Files should be under 500 lines**. If approaching this limit, refactor by splitting into modules/components
- **Functions should be under 50 lines** with a single, clear responsibility
- **Classes/Components should be under 100 lines** and represent a single concept or entity
- **Line length should be max 100-120 characters** (following project linting rules)
- **Use project-specific environment** (virtual env, node_modules, etc.) for all commands

### Code Organization
- **Organize code into clearly separated modules/components**, grouped by feature or responsibility
- **Follow consistent directory structure** as defined in project architecture
- **Maintain clear separation of concerns** between layers (UI, business logic, data)

---

## 🛠️ Technology Stack & Environment
**Last updated:** February 2026

### Primary Technologies
- **Language**: Python 3.9+
- **ML Framework**: PyTorch 2.0+, DGL (Deep Graph Library)
- **Backend API**: FastAPI (async high-performance)
- **Parsing**: tree-sitter (multi-language AST parsing)
- **Databases**: PostgreSQL (metrics), Neo4j (knowledge graphs), Redis (caching)
- **GNN**: Graph Attention Networks (custom architecture)
- **LLM**: CodeLlama-7B (fine-tuned for code analysis)
- **RL**: Stable-Baselines3 (PPO for orchestration)
- **Testing**: pytest, hypothesis (property-based testing)
- **Frontend**: React + D3.js (visualizations)

### Development Environment
**Environment Management**: Python venv
**Package Manager**: pip
**CI/CD**: GitHub Actions
**Containerization**: Docker + docker-compose
**Documentation**: Sphinx (API docs)

### Essential Commands
```bash
# Environment setup
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python scripts/setup_parsers.py

# Testing
pytest tests/                    # Run all tests
pytest --cov=src tests/         # Run with coverage report
pytest tests/integration/ -v    # Integration tests only

# Development
python -m src.main analyze path/to/code     # Analyze code
python -m src.main refactor --repo ./project --apply
python -m src.api.server                    # Start web server (port 8000)

# Model training (research phase)
python -m src.models.gnn.train --epochs 50
python -m src.models.llm.finetune --base-model codellama-7b
python -m src.models.rl.train_ppo --timesteps 1000000

# Linting and formatting
ruff format src/ tests/         # Auto-format code
ruff check src/ tests/          # Lint checking
mypy src/                       # Type checking
```

---

## 📋 Style & Conventions

### Code Style
- **Follow language-specific best practices** (PEP 8 for Python, ESLint for JS/TS, etc.)
- **Use type annotations** where supported (TypeScript, Python type hints, etc.)
- **Prefer explicit over implicit** - make intentions clear in any language
- **Use descriptive names** that explain purpose and context

### Naming Conventions
**Python-specific (PEP 8):**
- **Variables/Functions**: `snake_case` (e.g., `analyze_code`, `feature_vector`)
- **Classes**: `PascalCase` (e.g., `ArchitectureAgent`, `CodeEntity`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_FEATURE_DIM`, `DEFAULT_THRESHOLD`)
- **Files**: `snake_case.py` (e.g., `architecture_agent.py`, `graph_builder.py`)
- **Directories**: `snake_case` (e.g., `src/parsing`, `tests/integration`)
- **Private members**: `_leading_underscore` (e.g., `_internal_state`)
- **Type variables**: `T`, `KT`, `VT` for generic types

### Documentation Standards
**[Language-specific documentation format]**
```
// JavaScript/TypeScript JSDoc
/**
 * Brief description of function purpose
 * @param {string} param1 - Description of parameter
 * @param {number} param2 - Description of parameter  
 * @returns {boolean} Description of return value
 * @throws {Error} When validation fails
 */

# Python docstrings
"""Brief description of function purpose.

Args:
    param1: Description of parameter
    param2: Description of parameter
    
Returns:
    Description of return value
    
Raises:
    ValueError: When validation fails
"""
```

---

## 🧪 Testing Strategy

### Test-Driven Development (TDD)
1. **Write tests first** - Define expected behavior before implementation
2. **Run tests and confirm they fail** - Ensure tests are actually testing something
3. **Write minimal code** to make tests pass
4. **Refactor** while keeping tests green

### Test Organization
- **Unit tests**: Test individual functions and classes in isolation
- **Integration tests**: Test component interactions
- **End-to-end tests**: Test complete user workflows
- **Test file naming**: `test_[module_name].py`

---

## 🔧 Project-Specific Context
**Last updated:** February 2026

### Current Architecture

**Mavr**
```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                      │
│              (Web Dashboard / CLI / IDE Plugin)              │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   FastAPI Gateway                            │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              Code Analysis Pipeline                          │
│   Parser → AST → Knowledge Graph → Feature Extraction       │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│         Multi-Agent Orchestration (RL-based PPO)             │
│                                                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │Architecture│  │Performance │  │  Security  │            │
│  │   Agent    │  │   Agent    │  │   Agent    │            │
│  │   (GNN)    │  │  (Static)  │  │  (Taint)   │            │
│  └────────────┘  └────────────┘  └────────────┘            │
│                                                               │
│  ┌────────────────────────────────────────────┐             │
│  │      Maintainability Agent (LLM)           │             │
│  └────────────────────────────────────────────┘             │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│            Refactoring Execution Engine                      │
│   AST Transform → Test Gen → Sandbox → Validation           │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              Data Layer (PostgreSQL + Neo4j + Redis)         │
└──────────────────────────────────────────────────────────────┘
```

### Key Files and Directories

**Planning Documents (Current):**
- `PRD.md` - Comprehensive product requirements document
- `ROADMAP.md` - Phased development roadmap with milestones
- `README.md` - Project overview and research objectives
- `CLAUDE.md` - This file - AI development context
- `docs/planning/` - Additional planning materials

**Source Structure:**
- `src/parsing/` - Multi-language parsers: Python, Java, JavaScript, TypeScript (tree-sitter)
- `src/graph/` - Knowledge graph construction (NetworkX in-memory, Neo4j Protocol deferred)
- `src/metrics/` - Entity metrics (complexity, LOC, nesting) and structural metrics (coupling, cohesion, DIT, NOC)
- `src/features/` - 128-dim feature vector generation with min-max normalization
- `src/analysis/` - CFG builder, symbol tables, data flow analysis, taint analysis framework
- `src/pipeline/` - End-to-end pipeline orchestration with Protocol-based cache/storage backends
- `src/models/` - Core data models (CodeEntity, Issue, Refactoring, SourceLocation)
- `src/config/` - Configuration management (parser config, settings)
- `src/utils/` - Shared utilities (logger)
- `tests/` - 178 tests across 16 test files, 88% coverage

**To Be Created (Phase 2+):**
- `src/agents/` - Four specialized agents (Architecture, Performance, Security, Maintainability)
- `src/orchestrator/` - Multi-agent coordination (RL-based)
- `src/refactoring/` - Refactoring execution engine
- `src/api/` - FastAPI REST endpoints and web interface
- `data/` - Benchmark datasets (25 repos, 5000+ labeled smells)

### Database Schema

**PostgreSQL (Metrics & Results):**
- `issues` - Detected code smells and vulnerabilities
- `refactorings` - Proposed and applied refactorings
- `metrics` - Code quality metrics over time
- `experiments` - ML training experiments and results

**Neo4j (Knowledge Graphs):**
- Nodes: Classes, Functions, Variables, Modules
- Relationships: CALLS, INHERITS, USES, IMPORTS, DEPENDS_ON
- Properties: Complexity metrics, feature vectors (128-dim)

**Redis (Caching):**
- AST parsing results
- Feature vector caches
- Analysis results (TTL-based)

### API Endpoints (To Be Implemented)

**Analysis Endpoints:**
- `POST /api/v1/analyze` - Analyze codebase
- `GET /api/v1/issues/{repo_id}` - Get detected issues
- `GET /api/v1/metrics/{repo_id}` - Get quality metrics

**Refactoring Endpoints:**
- `POST /api/v1/refactor` - Apply refactorings
- `GET /api/v1/refactorings/{refactoring_id}` - Get refactoring status
- `POST /api/v1/rollback/{refactoring_id}` - Rollback refactoring

**Agent Endpoints:**
- `GET /api/v1/agents/status` - Agent health and status
- `POST /api/v1/agents/train` - Trigger model training

### External Dependencies

**Core ML/AI:**
- `torch` - PyTorch deep learning framework
- `dgl` - Deep Graph Library for GNNs
- `transformers` - Hugging Face (CodeLlama fine-tuning)
- `stable-baselines3` - RL algorithms (PPO)

**Code Analysis:**
- `tree-sitter` - Multi-language parsing
- `networkx` - Graph algorithms
- `neo4j-driver` - Graph database client
- `pygments` - Syntax highlighting

**Backend & API:**
- `fastapi` - High-performance async web framework
- `pydantic` - Data validation
- `sqlalchemy` - PostgreSQL ORM
- `redis` - Caching client

**Testing & Quality:**
- `pytest` - Testing framework
- `pytest-cov` - Coverage reporting
- `hypothesis` - Property-based testing
- `ruff` - Linter and formatter
- `mypy` - Type checker

---

## 🚨 Error Handling & Logging

### Exception Best Practices
- **Use language-specific exception types** rather than generic errors
- **Provide meaningful error messages** that help with debugging
- **Log errors with context** including relevant data for diagnosis
- **Fail fast** - validate inputs early and handle errors gracefully

### Logging Strategy
**[Adapt to language/framework logging system]**
```
// JavaScript/Node.js
console.debug('Detailed information for diagnosis');
console.info('General information about execution');
console.warn('Something unexpected happened');
console.error('A serious problem occurred');

// Python
import logging
logger = logging.getLogger(__name__)
logger.debug("Detailed information")
logger.info("General information")
logger.warning("Something unexpected")
logger.error("Serious problem")

// Java
logger.debug("Detailed information");
logger.info("General information");  
logger.warn("Something unexpected");
logger.error("Serious problem");
```

---

## 🔄 Development Workflow

### Git Workflow
- **Feature branches** for all new development
- **Descriptive commit messages** following conventional format
- **Small, focused commits** that represent single logical changes
- **Pull request reviews** before merging to main

### Branch Strategy
```bash
main              # Production-ready code
staging           # Integration branch for features
feature/[name]    # Individual feature development
hotfix/[name]     # Critical production fixes
```

### Commit Message Format
```
type(scope): brief description

Detailed explanation if needed

- List any breaking changes
- Reference related issues (#123)

Types: feat, fix, docs, style, refactor, test, chore
```

---

## 🛡️ Security & Performance

### Security Guidelines
- **Never commit secrets** - use environment variables or secure vaults
- **Validate all inputs** - sanitize and validate user data appropriately
- **Use parameterized queries** - prevent injection attacks
- **Implement proper authentication** and authorization patterns
- **Follow OWASP guidelines** for web applications
- **Keep dependencies updated** - regularly update packages/libraries

### Performance Considerations
- **Database optimization**: Use indexes, avoid N+1 queries, optimize query patterns
- **Caching strategies**: Implement appropriate caching at multiple levels
- **Resource management**: Properly close connections, manage memory usage
- **Profiling**: Measure performance before optimizing - don't guess
- **Bundle/Build optimization**: Minimize bundle size, optimize assets

---

## 📚 Development Commands & Tools

### Essential Development Commands
```bash
# Environment setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python scripts/setup_parsers.py  # Install tree-sitter grammars

# Development workflow
python -m src.main analyze path/to/file.py            # Analyze single file
python -m src.main analyze --repo https://github.com/user/repo.git
python -m src.main refactor --repo ./my-project --apply
python -m src.api.server                              # Start web server (port 8000)

# Testing
pytest tests/                      # Run all tests
pytest --cov=src --cov-report=html tests/  # Coverage report
pytest tests/test_agents/test_architecture_agent.py    # Specific test
pytest tests/integration/ -v       # Integration tests only

# Model training (research phase)
python -m src.models.gnn.train --data data/training/code_smells.json --epochs 50 --batch-size 32
python -m src.models.llm.finetune --base-model codellama-7b --dataset data/training/explanations.jsonl --epochs 3
python -m src.models.rl.train_ppo --env CodeRefactoringEnv --timesteps 1000000

# Code quality
ruff format src/ tests/            # Auto-format code
ruff check src/ tests/             # Lint checking
mypy src/                          # Type checking
```

### Debugging Tools
- **Python debugger**: pdb, ipdb for interactive debugging
- **Logging**: Python logging module with structured logs (DEBUG/INFO/WARNING/ERROR levels)
- **Testing**: pytest -vv for verbose output, pytest --pdb to drop into debugger on failure
- **Profiling**: cProfile for CPU profiling, memory_profiler for memory usage
- **Network debugging**: FastAPI auto-docs at /docs, curl for API testing
- **Graph visualization**: Neo4j Browser for knowledge graph exploration
- **ML monitoring**: TensorBoard for training metrics, MLflow for experiment tracking

---

## 🎯 Current Development Context
**Last updated:** February 2026

### Active Phase
**Phase**: Phase 2 — Individual Agent Development
**Focus**: Building the four specialized agents (Architecture, Performance, Security, Maintainability)
**Progress**: Phase 0 and Phase 1 complete; Phase 2 starting

### Completed Phases

**Phase 0 — Foundation & Infrastructure (Complete):**
- Project structure with 35+ files, Python 3.9+ with full type hints
- tree-sitter parsers for Python, Java, JavaScript, TypeScript
- Core data models (CodeEntity, Issue, Refactoring, SourceLocation) with Pydantic validation
- pytest infrastructure, GitHub Actions CI/CD, ruff/mypy

**Phase 1 — Core Analysis Pipeline (Complete):**
- Knowledge graph (NetworkX-backed, 10 relationship types, cycle detection, incremental updates)
- Code metrics (entity-level + structural: complexity, LOC, coupling, cohesion, DIT, NOC)
- 128-dim feature vectors (32 syntactic + 32 structural + 64 reserved for semantic/historical)
- Static analysis (CFG builder, symbol tables, data flow, taint analysis framework)
- Pipeline orchestration (parse → graph → metrics → features → CFG → taint)
- 178 tests passing, 88% coverage, all linting clean

### Recent Decisions
**February 2026:**
- Deferred **CodeBERT** semantic embeddings entirely (vector slots zeroed, reserved for future)
- Chose **Protocols + in-memory only** for storage/cache backends (Redis/PostgreSQL/Neo4j adapters deferred)
- Cross-file reference resolution is **name-based** (ambiguous matches left unresolved)

**October 2025:**
- Chose **tree-sitter** for multi-language parsing (unified AST representation)
- Selected **PyTorch + DGL** for GNN implementation
- Decided on **CodeLlama-7B** for LLM agent (fits 16GB GPU)
- Adopted **Stable-Baselines3 PPO** for RL orchestrator
- Chose **FastAPI** for API layer

### Next Priorities
1. **Design base agent interface** — Common agent protocol, communication, and result structures
2. **Architecture Agent (GNN-based)** — God Class, Feature Envy, Circular Dependency detection
3. **Performance Agent (Static Analysis)** — Algorithmic complexity, memory leaks, N+1 queries
4. **Security Agent (Taint Analysis)** — SQL injection, XSS, auth checks, crypto misuse
5. **Maintainability Agent (LLM-based)** — Readability, documentation quality, naming conventions

### Known Issues & Blockers
- **CodeBERT embeddings zeroed** — Semantic feature slots (64:96) reserved but not yet populated
- **Neo4j/Redis/PostgreSQL** — Protocol interfaces defined, adapters not yet implemented
- **Cross-file references** — Name-based resolution may be ambiguous for common names
- **CFG builder** — Tested primarily with Python AST patterns
- **Hardware constraint**: GNN training and LLM fine-tuning must fit in 16GB GPU memory
- **Dataset availability**: Need to curate 25 open-source repos and manually label 5000+ code smells

---

## ⚠️ Important Development Notes

### Critical Guidelines
- **NEVER ASSUME OR GUESS** - When in doubt, ask for clarification
- **Always verify file paths and imports** before use
- **Use project environment** (venv, node_modules, etc.) for all commands
- **Test your code** - No feature is complete without tests
- **Update documentation** when making architectural changes
- **Follow the planning workflow** - use `/plan-feature` before coding

### Session Management
- **Use `/clear`** when switching to completely different features
- **Use `/update-planning`** to save progress and decisions
- **Keep CLAUDE.md current** - update when patterns or practices change

### Quality Checklist
Before completing any feature:
- [ ] Code follows style guidelines
- [ ] Tests are written and passing
- [ ] Documentation is updated
- [ ] Error handling is implemented
- [ ] Performance impact is considered
- [ ] Security implications are reviewed

---

## 🔍 Search & Discovery Commands

When analyzing code or debugging:
1. **Use `tree` command** to understand project structure
2. **Search for patterns** using `grep` or `rg` (ripgrep)
3. **Check git history** for context on changes
4. **Review test files** to understand expected behavior
5. **Examine config files** for environment setup

---

---

## 🔬 Research-Specific Context

### Novel Contributions (For Publication)
1. **Multi-Agent Architecture**: First heterogeneous multi-agent system where each agent uses different AI/ML techniques for different quality dimensions
2. **RL-based Orchestration**: Novel application of PPO for dynamically prioritizing refactoring tasks based on impact, effort, and risk
3. **Graph Neural Networks for Code**: Custom GNN architecture capturing semantic, structural, and historical information in code knowledge graphs
4. **Automated Semantic Verification**: Comprehensive verification pipeline ensuring refactorings preserve program semantics (95%+ test pass rate)
5. **Transfer Learning for Code Quality**: Cross-language adaptation achieving 70%+ zero-shot accuracy

### Academic Timeline
- **Workshop Paper (MSR 2025)**: January 2025 deadline - Focus on benchmark dataset
- **Conference Paper (ICSE/FSE 2026)**: August 2025 deadline - Complete system evaluation

### Evaluation Metrics (For Paper)
- **Detection Performance**: Precision, Recall, F1-score vs. SonarQube, PMD, ESLint
- **Refactoring Success**: Test preservation rate, semantic correctness, quality improvement
- **Efficiency**: Processing time vs. codebase size, memory usage patterns
- **Transfer Learning**: Zero-shot, 5-shot, 10-shot accuracy across languages
- **Ablation Studies**: Impact of each agent, RL vs. rule-based orchestration

### Benchmark Dataset Requirements
- 25 open-source repositories (diverse domains and languages)
- 5000+ manually labeled code smells (validated by experts)
- Ground truth refactoring examples
- Training (60%), Validation (20%), Test (20%) split

---

*This document is automatically updated by `/prime` command and should be maintained as the project evolves. Last updated: February 2026*