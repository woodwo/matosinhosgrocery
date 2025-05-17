# Core Application Testability & Boilerplate

**ID:** TEST-002
**Related Use Case:** [UC-001 Add Receipt via Telegram](001-usecase-boilerplate.md)

## 1. Introduction

This document outlines the testing strategy for the core application components of the MatosinhosGrocery project. The primary goal is to ensure the reliability and correctness of the business logic, particularly the "Receipt Processing Service" and "Data Persistence" layers as defined in UC-001.

Tests will focus on unit and integration aspects of the core services. For unit tests, external dependencies such as OpenAI, Google Drive, and the Telegram Bot Interface will be mocked. This approach allows for fast, repeatable tests suitable for CI/CD pipelines.

Additionally, API endpoints will be provided to interact directly with core services using their real external client integrations (OpenAI, Google Drive), offering an alternative to Telegram-based interaction for testing and direct access.

## 2. Testing Frameworks and Tools

*   **Test Runner:** `pytest`
*   **Mocking (for unit tests):** `pytest-mock` (integrating `unittest.mock`)
*   **Code Coverage:** `pytest-cov`
*   **Assertions:** Standard `pytest` `assert` statements.

## 3. Test Structure

*   Tests in `tests/`, mirroring `src/`.
*   Test files: `test_*.py`.
*   Shared fixtures in `tests/conftest.py`.

```
tests/
├── conftest.py
└── core/
    ├── services/
    │   └── test_receipt_processing_service.py
    └── models/
        └── test_receipt_model.py
        └── test_product_model.py
```

## 4. Mocking Strategy (for Unit Tests)

To isolate core logic in unit tests, external services are mocked:

*   **OpenAI API:** Interactions patched via `mocker.patch()` or by injecting mock callables. Mocks simulate successful responses and error conditions.
*   **Google Drive API:** Interactions patched or callables mocked, simulating uploads and errors.
*   **Database:** In-memory SQLite for most unit tests (via fixtures). For specific error simulations not easily done with in-memory SQLite, session methods might be mocked.
*   **Telegram Bot Interface:** Core service calls to notify/interact with the bot (if any) are mocked.

## 5. API for Direct Service Interaction (Integration Testing / Direct Use)

In addition to unit tests with mocks, API endpoints (e.g., in `src/matosinhosgrocery/receipt_routes.py`) will allow direct interaction with services like `ReceiptProcessingService`. These endpoints will use the **real** external clients for OpenAI and Google Drive.

*   **Purpose:**
    *   End-to-end testing of the service logic with actual external dependencies.
    *   Provides a direct way to trigger service operations (e.g., receipt processing) via HTTP calls (e.g., `curl`, Postman, Swagger UI) without going through the Telegram bot.
*   **Example Endpoint:** `POST /api/v1/receipts/upload` for `ReceiptProcessingService`.
*   **Testing:** These endpoints can be tested using an HTTP client in integration tests, verifying behavior with live (or sandboxed) external services.
