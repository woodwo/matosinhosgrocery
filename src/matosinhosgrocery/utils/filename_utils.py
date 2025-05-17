import datetime
from typing import Optional, NamedTuple
import re
import logging

logger = logging.getLogger(__name__)


class FilenameData(NamedTuple):
    """DTO for data needed to construct a GDrive filename."""

    receipt_datetime: Optional[datetime.datetime]
    category: Optional[str]
    store_name: Optional[str]
    original_extension: str  # e.g., ".jpg", ".pdf"
    original_filename_for_log: Optional[str] = "unknown_original_file"


def _normalize_string_for_filename(
    input_str: Optional[str], default_placeholder: str, is_store_name: bool = False
) -> str:
    if not input_str or not input_str.strip():
        return default_placeholder

    s = input_str.lower()
    # For store names, specifically handle common extraneous terms before general sanitization
    if is_store_name:
        # Remove common suffixes like "supermercado", "lda", "s.a.", etc.
        # This list can be expanded. Order might matter if some terms are substrings of others.
        suffixes_to_remove = [
            r"\s+supermercado$",
            r"\s+mercado$",
            r"\s+hipermercado$",
            r"\s+mini-mercado$",
            r"\s+lda[\.\s]*$",
            r"\s+s\.a\.[\s]*$",
            r"\s+s\.a$",  # Handles S.A. and S.A
            r"\s+unipessoal[\s,]+lda\.$",
            # Add more specific terms like "modelo" if it's truly generic and not part of a distinct chain name
            # e.g., if "Continente Modelo" should just be "continente"
            # but if "Pingo Doce Modelo" is different from "Pingo Doce", then keep "modelo"
        ]
        for suffix_pattern in suffixes_to_remove:
            s = re.sub(suffix_pattern, "", s, flags=re.IGNORECASE)
        s = s.strip()
        if not s:  # If stripping suffixes left it empty
            return default_placeholder

    s = s.replace(" ", "-")  # Replace spaces with hyphens
    # Corrected regex to remove characters NOT in the allowed set [a-z0-9-]
    s = re.sub(r"[^a-z0-9-]", "", s)
    s = re.sub(r"--+", "-", s)  # Consolidate multiple hyphens to a single one
    s = s.strip("-")  # Remove leading/trailing hyphens

    return s if s else default_placeholder


def generate_gdrive_filename(data: FilenameData) -> str:
    """Generates a filename for Google Drive based on the defined convention."""

    timestamp_str: str
    if data.receipt_datetime:
        timestamp_str = data.receipt_datetime.strftime("%Y%m%dT%H%M")
    else:
        now = datetime.datetime.now()
        timestamp_str = now.strftime("%Y%m%dT%H%M")
        logger.warning(
            f"Receipt timestamp not found for original file '{data.original_filename_for_log}'. "
            f"Using current system time ({timestamp_str}) for GDrive filename."
        )

    category_str = _normalize_string_for_filename(data.category, "other")
    store_name_str = _normalize_string_for_filename(
        data.store_name, "loja", is_store_name=True
    )

    # Ensure extension has a leading dot and is lowercase
    ext = data.original_extension.lower()
    if not ext.startswith("."):
        ext = "." + ext
    if not ext:  # Handle empty extension case, default to .dat or similar if necessary
        ext = ".dat"
        logger.warning(
            f"Original file '{data.original_filename_for_log}' had no extension. Defaulting to '.dat'."
        )

    return f"{timestamp_str}_{category_str}_{store_name_str}{ext}"
