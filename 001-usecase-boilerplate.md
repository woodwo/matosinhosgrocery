# Use Case: Add Receipt via Telegram

**ID:** UC-001
**Actor:** User (Registered Telegram User)
**Goal:** To submit a receipt image/scan through the Telegram bot, have it processed, and its contents stored in the application.

## Preconditions:

1.  The MatosinhosGrocery application (FastAPI core, Telegram bot integration) is running.
2.  The User is authenticated (their Telegram User ID is in the `TELEGRAM_ALLOWED_USER_IDS` list).
3.  Required API keys (OpenAI, Google Drive) and configurations (database path, allowed user IDs) are correctly set as environment variables.
4.  Connections to external services (OpenAI, Google Drive) are available.

## Main Success Scenario:

1.  **User Action:** User sends a message to the Telegram bot containing an image (e.g., JPG, PNG) or a PDF file of a grocery receipt.
2.  **System (Telegram Bot Interface):**
    a.  Receives the message with the attached media.
    b.  Verifies the User's Telegram ID against the allowed list (`TELEGRAM_ALLOWED_USER_IDS`).
    c.  Acknowledges receipt to the User (e.g., "Got your receipt! Processing it now...").
    d.  Forwards the media file (or its reference/bytes) to the Core Application for processing.
3.  **System (Core Application - Receipt Processing Service):
**    a.  Receives the media file from the Telegram Bot Interface.
    b.  Initiates an asynchronous task to process the receipt. This task includes the following concurrent or sequential sub-steps:
        i.  **OpenAI Interaction:** Sends the media file to the OpenAI API for OCR and extraction of structured data (store name, date, items with names, generalized names, prices, quantities, weight/volume if available).
        ii. **Google Drive Upload:** Uploads the original media file to the designated Google Drive folder.
4.  **System (Core Application - Receipt Processing Service & Data Persistence):
**    a.  Upon successful completion of both OpenAI extraction and Google Drive upload:
        i.  Retrieves the structured data from OpenAI and the file link/ID from Google Drive.
        ii. Using SQLAlchemy, creates a new `Receipt` record in the SQLite database, storing the store name, date of purchase, and the Google Drive link to the original image.
        iii. For each item extracted by OpenAI, creates corresponding `Product` records (or updates existing ones based on generalized name and store, if applicable), linking them to the newly created `Receipt` record. This includes original name, generalized name, price, quantity, and weight/volume.
5.  **System (Core Application & Telegram Bot Interface):**
    a.  The Core Application signals successful processing to the Telegram Bot Interface.
    b.  The Telegram Bot Interface sends a confirmation message to the User (e.g., "Receipt from [Store Name] dated [Date] processed successfully! X items added.").

## Error Scenarios & Alternative Flows:

*   **User Not Authenticated:**
    *   If the User's Telegram ID is not in `TELEGRAM_ALLOWED_USER_IDS`:
        *   System (Telegram Bot Interface) responds with a message: "Sorry, you are not authorized to use this bot. Please deploy your own instance from [link to repository] if you wish to use this application."
*   **Invalid File Type:**
    *   If the User sends a file that is not a supported image format or PDF:
        *   System (Telegram Bot Interface or Core Application) responds with an error message: "Invalid file type. Please send a receipt as an image (JPG, PNG) or PDF."
*   **OpenAI API Error:**
    *   If the OpenAI API returns an error (e.g., unreadable image, API key issue, service unavailable):
        *   System (Core Application) logs the error from OpenAI.
        *   System (Telegram Bot Interface) sends the raw Python exception traceback (from the OpenAI client interaction) formatted in a code block to the User, as per `adr.md`.
        *   The original image might still be uploaded to Google Drive if that part is independent and configured to proceed.
*   **Google Drive API Error:**
    *   If the Google Drive API returns an error (e.g., authentication issue, storage full, service unavailable):
        *   System (Core Application) logs the error from Google Drive.
        *   System (Telegram Bot Interface) sends the raw Python exception traceback (from the Google Drive client interaction) formatted in a code block to the User.
        *   Data extracted by OpenAI might still be processed and stored in the database, but without a link to the GDrive image, or the receipt processing might be considered failed.
*   **Database Error:**
    *   If an error occurs while writing to the SQLite database:
        *   System (Core Application) logs the database error.
        *   System (Telegram Bot Interface) sends the raw Python exception traceback formatted in a code block to the User.
*   **Partial Success (Configurable Behavior):**
    *   Depending on design decisions, if OpenAI processing succeeds but Google Drive upload fails (or vice-versa), the system might partially save the data and inform the user, or treat the entire operation as a failure.

## Postconditions:

*   **On Success:**
    *   The receipt image/PDF is stored in Google Drive.
    *   Extracted receipt data (store, date, items, prices, etc.) is stored in the SQLite database.
    *   The User is notified of the successful processing.
*   **On Failure:**
    *   The User is notified of the error, potentially with a traceback.
    *   System state regarding the failed receipt is well-defined (e.g., no partial data saved, or partial data saved with clear indicators of failure).
    *   Relevant errors are logged on the server-side.
