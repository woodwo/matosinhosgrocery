# ADR Implementations: High-Level Design for Grocery List Application

This document outlines the high-level design for the grocery list application, incorporating FastAPI as the core application framework. This design aligns with the architectural decisions in `adr.md` and aims to fulfill the features described in `overview.md`.

## I. Core Application (Python/FastAPI)

*   **Purpose:** Acts as the central orchestrator, built around an `asyncio`-native framework.
*   **Responsibilities:**
    *   Initialize and configure all other modules (database, Telegram bot, API clients, etc.) leveraging FastAPI's startup events.
    *   Provide a FastAPI-based application core. While the primary UI is Telegram, FastAPI will manage the application lifecycle, dependencies, and background tasks. Any potential internal HTTP endpoints (e.g., for health checks, or future administrative tasks) would be defined here.
    *   Implement the business logic for:
        *   Unified grocery list management.
        *   Smart shopping assistance features.
        *   Price tracking and comparison logic.
    *   Handle application-level configuration using Pydantic (which FastAPI integrates natively), loading from environment variables as specified in `adr.md`.
*   **Key Technologies:** Python, FastAPI, Pydantic.

## II. Telegram Bot Interface

*   **Purpose:** Handles all user interaction via the Telegram Bot API.
*   **Responsibilities:**
    *   Receive user messages, commands, and media (receipt images).
    *   Authenticate users based on `TELEGRAM_ALLOWED_USER_IDS`.
    *   Integrate with the FastAPI application to trigger business logic. Callbacks from `python-telegram-bot` can invoke `async` functions within the FastAPI managed application context.
    *   Format and send responses back to the user (grocery lists, suggestions, error tracebacks).
*   **Key Technologies:** `python-telegram-bot` library, `asyncio`.

## III. Data Persistence Layer

*   **Purpose:** Store and manage all application data.
*   **Responsibilities:**
    *   **Database (SQLite with SQLAlchemy ORM - async support):**
        *   Store structured data including receipt details, extracted product information, unified grocery list items, crawled supermarket price data, user preferences, and historical purchase data.
        *   Utilize SQLAlchemy's `asyncio` extension (e.g., with `aiosqlite` for SQLite) for non-blocking database operations, integrating smoothly with FastAPI.
        *   Manage schema migrations using Alembic.
    *   **Image Storage (Google Drive API):**
        *   Store original scanned receipt images/files.
        *   Link stored images to database records.
*   **Key Technologies:** SQLite, SQLAlchemy (with `asyncio` support), Alembic, Google Drive API client library, `asyncio`.

## IV. Asynchronous Task Management (Leveraging FastAPI & `asyncio`)

*   **Purpose:** Handle long-running or I/O-bound operations efficiently without blocking the main application.
*   **Responsibilities:**
    *   FastAPI's background tasks or direct use of `asyncio.create_task` will manage:
        *   **Receipt Processing:** Asynchronously sending receipt data to the OpenAI API and awaiting results.
        *   **Google Drive Interactions:** Asynchronously uploading receipt images.
        *   **Web Crawling:** Asynchronously fetching price data from supermarket websites.
*   **Key Technologies:** Python's `asyncio` library, FastAPI's background task features.

## V. External Service Integrations (Async Clients)

*   **A. OpenAI API Client:**
    *   **Purpose:** Extract structured data from receipt images.
    *   **Responsibilities:** Communicate with the OpenAI API using an `async` HTTP client (like `httpx`) for non-blocking operations.
*   **B. Google Drive API Client:**
    *   **Purpose:** Long-term storage of receipt images.
    *   **Responsibilities:** Utilize an `async`-compatible version of the Google Drive client library, or wrap synchronous calls appropriately for `asyncio` (e.g., using `asyncio.to_thread`).
*   **C. Web Crawling Module:**
    *   **Purpose:** Gather product price and availability data from supermarket websites.
    *   **Responsibilities:** Implement crawlers using `async` HTTP clients (`httpx`, `aiohttp`) and HTML parsing libraries.

## VI. Configuration and Deployment

*   **Configuration:**
    *   FastAPI's settings management (typically using Pydantic models) will load all configurations (API keys, Telegram token, `TELEGRAM_ALLOWED_USER_IDS`, database path, log level, etc.) from environment variables.
*   **Deployment:**
    *   The application will be packaged as a Docker container.
    *   It will be run using an ASGI server like Uvicorn, which is standard for FastAPI applications.

## VII. Logging and Error Handling

*   **User-Facing Errors (via Telegram):**
    *   As defined in `adr.md`, when an operation initiated by a user via Telegram results in an error, the application will respond by sending the raw Python exception traceback formatted within a code block.
*   **Server-Side Logging:**
    *   The standard Python `logging` module will be used.
    *   Logs will be written to standard output (`stdout`) for capture by Docker/Systemd.
    *   The log level will be configurable via an environment variable, controlling verbosity (e.g., DEBUG, INFO, WARNING, ERROR). FastAPI can integrate with standard logging configurations.

## Workflow Example (Receipt Submission):

1.  User sends a receipt image via Telegram.
2.  The **Telegram Bot Interface** receives the image and authenticates the user.
3.  It passes the image data to an appropriate endpoint/handler in the **Core Application (FastAPI)**.
4.  The **Core Application** initiates asynchronous tasks via the **Asynchronous Task Manager**:
    a.  One task sends the image data to the **OpenAI API Client** for processing.
    b.  Concurrently or subsequently, another async task uploads the original image via the **Google Drive API Client**.
5.  Once data is extracted and the image is stored, the information (extracted details and the link to the Google Drive image) is saved to the **Data Persistence Layer (SQLite/SQLAlchemy async)**.
6.  The **Core Application** updates the unified grocery list and any relevant price tracking data.
7.  The **Telegram Bot Interface** formats and sends a confirmation message (or an error traceback if issues occurred) back to the user. 