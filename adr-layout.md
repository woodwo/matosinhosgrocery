# ADR: Project File Layout

This document outlines the suggested file layout for the `matosinhosgrocery` project, based on a FastAPI core, Python best practices (including src-layout), and the components described in `adr.md` and `adr-implementations.md`.

```plaintext
matosinhosgrocery/
├── .env.example            # Example environment variables
├── .gitignore
├── alembic.ini             # Alembic configuration
├── Dockerfile
├── LICENSE                 # Optional, but good practice for open source
├── pyproject.toml          # Preferred for managing dependencies and project metadata (e.g., with Poetry or Hatch)
│                           # Alternatively, requirements.txt and requirements-dev.txt
├── README.md
│
├── alembic/                # Alembic auto-generated migration scripts directory
│   ├── env.py              # Alembic environment setup
│   ├── script.py.mako      # Migration script template
│   └── versions/           # Individual migration files
│       └── ...timestamp_description.py
│
├── src/
│   └── matosinhosgrocery/  # The main Python package
│       ├── __init__.py
│       ├── main.py             # FastAPI application factory/instance and Uvicorn entry point
│       │
│       ├── config.py           # Pydantic models for loading settings from environment variables
│       ├── logging_config.py   # Centralized logging setup function/configuration
│       │
│       ├── api_routers/        # FastAPI routers for any HTTP API endpoints (e.g., health checks)
│       │   ├── __init__.py
│       │   └── health.py       # Example: /health endpoint
│       │
│       ├── bot/                # Telegram bot specific logic
│       │   ├── __init__.py
│       │   ├── core.py         # Bot initialization (python-telegram-bot Application setup), dispatcher
│       │   ├── auth.py         # User ID authentication logic (decorator or utility)
│       │   └── handlers/       # Telegram command and message handlers
│       │       ├── __init__.py
│       │       ├── general.py  # e.g., /start, /help commands
│       │       ├── receipts.py # Handles receipt submission, queries about receipts
│       │       ├── grocery.py  # Handles grocery list interactions, smart suggestions
│       │       └── errors.py   # Custom error handler to send tracebacks to users
│       │
│       ├── database/           # Database interaction layer (SQLAlchemy async)
│       │   ├── __init__.py
│       │   ├── connection.py   # SQLAlchemy async engine, SessionLocal factory
│       │   ├── models/         # SQLAlchemy ORM models (Pydantic models can also be here or in schemas)
│       │   │   ├── __init__.py
│       │   │   ├── base.py     # Declarative base for SQLAlchemy models
│       │   │   ├── product.py
│       │   │   ├── receipt.py
│       │   │   ├── store.py
│       │   │   └── price_log.py # For tracking price changes
│       │   └── crud/           # Create, Read, Update, Delete (CRUD) database operations
│       │       ├── __init__.py # e.g., crud_receipt.py, crud_product.py
│       │       ├── base_crud.py # Optional: Base class for generic CRUD operations
│       │       ├── crud_receipt.py
│       │       └── crud_product.py
│       │
│       ├── schemas/            # Pydantic schemas for data validation, serialization (API and internal)
│       │   ├── __init__.py
│       │   ├── product.py
│       │   ├── receipt.py
│       │   └── common.py       # Common/shared Pydantic schemas (e.g., for ID, timestamps)
│       │
│       ├── services/           # Core business logic and orchestration layer
│       │   ├── __init__.py
│       │   ├── receipt_processing_service.py # Orchestrates OpenAI, GDrive, DB for new receipts
│       │   ├── grocery_list_service.py  # Manages unified grocery list, smart suggestions
│       │   └── price_data_service.py    # Manages price table, updates from receipts & crawling
│       │
│       ├── external_apis/      # Typed clients for interacting with third-party APIs
│       │   ├── __init__.py
│       │   ├── openai_client.py
│       │   └── gdrive_client.py
│       │
│       └── web_crawlers/       # Modules for web crawling supermarket data
│           ├── __init__.py
│           ├── base_crawler.py # Abstract base class or common utilities for crawlers
│           ├── pingo_doce.py
│           ├── continente.py
│           └── ...             # Other supermarket crawlers
│
├── static/                 # Static files (if ever needed, unlikely for a bot-only UI)
├── templates/              # Templates (if ever needed, unlikely for a bot-only UI)
│
└── tests/                  # Test suite
    ├── __init__.py
    ├── conftest.py         # Global pytest fixtures
    ├── integration/        # Integration tests (testing interactions between components)
    │   ├── __init__.py
    │   └── test_receipt_flow.py
    └── unit/               # Unit tests (testing individual components in isolation)
        ├── __init__.py     # Mirrors src structure, e.g., tests/unit/bot/, tests/unit/services/
        ├── bot/
        │   └── test_handlers.py
        └── services/
            └── test_receipt_processing.py
```

## Explanation of Key Choices:

*   **`src`-layout (`src/matosinhosgrocery/`)**: This is a standard Python best practice that clearly separates your actual package code from project root files like `README.md`, `Dockerfile`, etc.
*   **`pyproject.toml`**: Modern way to manage dependencies and build settings. Tools like Poetry or Hatch use this. If you prefer, you can use `requirements.txt` (for main dependencies) and `requirements-dev.txt` (for development tools like `pytest`, `black`, `isort`).
*   **`alembic/` at root**: Standard location for Alembic migration scripts and configuration.
*   **`main.py`**: Common entry point for a FastAPI application. This is where your FastAPI app instance would be created and configured. Uvicorn would point to this file (e.g., `uvicorn src.matosinhosgrocery.main:app --reload`).
*   **`config.py`**: Uses Pydantic to load and validate all application settings from environment variables, as per your ADR.
*   **`logging_config.py`**: Centralizes the setup of your logging system.
*   **Separation of Concerns:**
    *   **`api_routers/`**: For any actual HTTP endpoints your FastAPI app might serve (e.g., a `/health` check).
    *   **`bot/`**: All Telegram-specific code, including handlers for different commands/messages and bot initialization.
    *   **`database/`**: Contains everything related to database interaction: `connection.py` for engine/session setup, `models/` for SQLAlchemy ORM classes, and `crud/` for data access functions.
    *   **`schemas/`**: Pydantic schemas used for data validation by FastAPI (if you have HTTP endpoints), for structuring data passed between services, and for defining the shape of data returned by CRUD operations.
    *   **`services/`**: This is a crucial layer for your business logic. Bot handlers or API routers would call functions in these service modules. Services orchestrate operations, calling CRUD functions, external API clients, etc.
    *   **`external_apis/`**: Clients for interacting with OpenAI, Google Drive, etc. These should handle the actual HTTP requests and responses, ideally using an async library like `httpx`.
    *   **`web_crawlers/`**: Dedicated modules for each supermarket crawler.
*   **`tests/`**: Follows the `src` layout, with `unit/` tests for isolated components and `integration/` tests for interactions between them. 