import io
import logging
import asyncio
from typing import Dict, Optional, Tuple, Any

from google.oauth2 import service_account
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

from matosinhosgrocery.config import settings

logger = logging.getLogger(__name__)

# Define the scopes needed for the Google Drive API
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

_drive_service: Optional[Resource] = None


def get_gdrive_service() -> Optional[Resource]:
    """
    Authenticates and returns a Google Drive API service client.
    Caches the service client for reuse.
    """
    global _drive_service
    if _drive_service:
        return _drive_service

    if not settings.GOOGLE_DRIVE_CREDENTIALS_PATH:
        logger.error(
            "Google Drive credentials path is not configured. Cannot initialize GDrive service."
        )
        return None

    try:
        creds = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_DRIVE_CREDENTIALS_PATH, scopes=SCOPES
        )
        _drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)
        logger.info("Google Drive API service initialized successfully.")
        return _drive_service
    except FileNotFoundError:
        logger.error(
            f"Google Drive credentials file not found at: {settings.GOOGLE_DRIVE_CREDENTIALS_PATH}"
        )
        return None
    except Exception as e:
        logger.exception(f"Failed to initialize Google Drive API service: {e}")
        return None


async def upload_file_to_gdrive(
    file_bytes: bytes,
    file_name_on_drive: str,
    mime_type: str = "application/octet-stream",
) -> Optional[Dict[str, str]]:
    """
    Uploads a file (from bytes) to Google Drive.

    Args:
        file_bytes: The bytes of the file to upload.
        file_name_on_drive: The name the file should have on Google Drive.
        mime_type: The MIME type of the file.

    Returns:
        A dictionary containing the 'id' and 'webViewLink' of the uploaded file, or None if upload fails.
    """
    service = get_gdrive_service()
    if not service:
        logger.error("Google Drive service is not available. Cannot upload file.")
        return None

    file_metadata = {"name": file_name_on_drive}
    if settings.GOOGLE_DRIVE_FOLDER_ID:
        file_metadata["parents"] = [settings.GOOGLE_DRIVE_FOLDER_ID]

    media = MediaIoBaseUpload(
        io.BytesIO(file_bytes), mimetype=mime_type, resumable=True
    )

    try:
        # This is a synchronous (blocking) call.
        # To make it non-blocking for an async context, run it in a thread pool.
        loop = asyncio.get_running_loop()
        request = service.files().create(
            body=file_metadata, media_body=media, fields="id, webViewLink"
        )

        # Wrap the synchronous execute() call in asyncio.to_thread
        file_resource = await loop.run_in_executor(None, request.execute)

        logger.info(
            f"Successfully uploaded file '{file_name_on_drive}' to Google Drive. File ID: {file_resource.get('id')}"
        )
        return {
            "id": file_resource.get("id"),
            "webViewLink": file_resource.get("webViewLink"),
        }
    except HttpError as error:
        logger.error(f"An HTTP error occurred while uploading to Google Drive: {error}")
        return None
    except Exception as e:
        logger.exception(
            f"An unexpected error occurred while uploading to Google Drive: {e}"
        )
        return None


# Example usage (for testing this module directly, if needed)
async def main_test():
    # Configure settings for testing (normally done via .env)
    # settings.GOOGLE_DRIVE_CREDENTIALS_PATH = "/path/to/your/credentials.json"
    # settings.GOOGLE_DRIVE_FOLDER_ID = "your_folder_id"

    if not settings.GOOGLE_DRIVE_CREDENTIALS_PATH:
        print(
            "Please set GOOGLE_DRIVE_CREDENTIALS_PATH in your .env or directly in settings for testing."
        )
        return

    # Create some dummy file bytes
    dummy_file_content = b"This is a test file for Google Drive upload."
    file_name = "test_upload.txt"
    mime = "text/plain"

    print(f"Attempting to upload '{file_name}'...")
    upload_result = await upload_file_to_gdrive(dummy_file_content, file_name, mime)

    if upload_result:
        print(f"Upload successful!")
        print(f"  File ID: {upload_result.get('id')}")
        print(f"  Web Link: {upload_result.get('webViewLink')}")
    else:
        print("Upload failed.")


if __name__ == "__main__":
    # This allows running this script directly for testing the GDrive upload.
    # Ensure your .env file is configured with GOOGLE_DRIVE_CREDENTIALS_PATH
    # and optionally GOOGLE_DRIVE_FOLDER_ID for this test to work.
    asyncio.run(main_test())
