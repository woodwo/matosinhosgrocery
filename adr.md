# App
This app should be written in Python 3.10+

## Service
The app is a single server application, packed inside a Docker container, orchestrated by Systemd as a Linux service. NB: no such thing, as docker compose or k8s here.

## Third-party integrations
- The OpenAI API will be utilized for parsing receipt images/scans and extracting relevant data.
- The Google Drive API will be used for long-term storage of receipt images/scans.
- Telegram Bot API will be used for the user interface.

## Storage
The primary data store will be an SQLite database. However, the application core will be designed for storage engine agnosticism by utilizing an Object Relational Mapper (ORM), with SQLAlchemy being the preferred choice. This approach will facilitate potential future migrations to different database backends. Alembic will be used for managing database schema migrations.

## UX
The app UI is a Telegram.
- The application will utilize the `python-telegram-bot` library for interacting with the Telegram Bot API.
- User access will be managed by restricting functionality to a predefined list of Telegram User IDs. For users not on the predefined list, the application will suggest they deploy their own instance from the project repository.

## Configuration Management
Application settings (e.g., Telegram Bot Token, OpenAI API Key, Google Drive API credentials, allowed Telegram User IDs, database file path) will be managed via environment variables.
- Allowed Telegram User IDs will be specifically configured via a single environment variable, `TELEGRAM_ALLOWED_USER_IDS`, containing a comma-separated list of user IDs (e.g., `TELEGRAM_ALLOWED_USER_IDS="12345,67890,54321"`).
- Consideration should be given to using a library such as Pydantic for loading, validation, and management of these environment variable-based configurations, including parsing the comma-separated list of user IDs.

## Background Task Management
Long-running or I/O-bound operations, such as web crawling for supermarket prices, receipt processing via the OpenAI API, and interactions with the Google Drive API, will be managed using Python's `asyncio` library. This will allow the application to handle these tasks concurrently without blocking the main thread, ensuring responsiveness of the Telegram UI.

## Logging and Error Handling
- **User-Facing Errors:** When an operation initiated by a user via Telegram results in an error, the application will respond by sending the raw Python exception traceback formatted within a code block. This aids in direct debugging for the user.
- **Server-Side Logging:** 
    - The standard Python `logging` module will be used for application logging.
    - Logs will be written to standard output (`stdout`), allowing them to be captured by the container orchestration (Systemd/Docker).
    - The log level (e.g., DEBUG, INFO, WARNING, ERROR) will be configurable, likely via an environment variable, to control verbosity.