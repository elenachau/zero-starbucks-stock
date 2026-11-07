# Zero Starbucks Stock Constitution

## Core Principles

### I. Python Only

Every service MUST be written in Python 3.12 or newer. Each service MUST pin its runtime
dependencies to exact versions in its own `requirements.txt`.

Rationale: one language keeps services readable by every contributor and lets CI use a
single toolchain.

### II. FastAPI for Every HTTP Service

Every service that exposes HTTP MUST use FastAPI and MUST be served by uvicorn. Each service
MUST publish the OpenAPI document FastAPI generates at `/openapi.json`. Services MUST NOT use
another web framework or the standard-library `http.server`.

Rationale: FastAPI gives every service the same request validation and a machine-readable
OpenAPI contract that other services and contract tests can rely on.

### III. One Container per Service

Each service MUST build into exactly one container image from its own `Dockerfile`, and each
container MUST run exactly one service. Services MUST NOT share a container, and one container
MUST NOT start more than one service process.

Rationale: one service per container lets each service be built, tested, deployed, scaled and
rolled back on its own.

### IV. Test-First (NON-NEGOTIABLE)

Tests MUST be written before the code they cover. A new test MUST be run and seen to fail
before any implementation is written, and the change MUST NOT be merged until that test
passes. Every endpoint MUST have at least one test for its success response and one for each
refusal it can return.

Rationale: a test that has been seen to fail proves it checks the behavior; writing it first
keeps the spec, not the implementation, in charge.

### V. No Secrets in Code

Source code, tests, fixtures, Dockerfiles, CI workflows and committed config MUST NOT contain
secrets (API keys, passwords, tokens, connection strings with credentials, payment keys).
Secrets MUST be read from environment variables or a secret store at runtime. A service MUST
fail to start, with a clear error, when a required secret is missing.

Rationale: anything committed to git is permanently readable by anyone with repo access.

## Technology & Security Constraints

- Language: Python 3.12+. Web framework: FastAPI served by uvicorn. Tests: pytest.
- Packaging: one `Dockerfile` and one `requirements.txt` per service.
- Configuration: environment variables only; committed example files MUST use placeholder
  values, never real secrets.
- Logs and error responses MUST NOT include secrets or payment card data.

## Development Workflow & Quality Gates

- Order of work for every change: spec → failing test → implementation → passing test.
- CI MUST run every service's pytest suite on each push and pull request; a red CI run blocks
  merge.
- Every pull request description MUST state which principles it touches and how compliance
  was checked.
- Project-wide agent rules (fixed OpenAPI contracts, no shared database, contract-test merge
  gate, refusal rules) live in `CLAUDE.md` and apply alongside this constitution.

## Governance

This constitution supersedes any conflicting practice in this repository. Amendments MUST be
made by pull request that updates this file, states the version bump and its reason, and lists
any services that need changes to comply. Versioning follows semantic versioning: MAJOR for
removing or redefining a principle, MINOR for adding a principle or materially expanding one,
PATCH for wording fixes. Every code review MUST check the change against these principles;
any exception MUST be written in the pull request with its justification and an end date.

**Version**: 1.0.0 | **Ratified**: 2026-11-07 | **Last Amended**: 2026-11-07
