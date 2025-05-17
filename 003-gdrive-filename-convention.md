# Google Drive Filename Convention (Revised)

**ID:** FILE-CONV-003
**Purpose:** To define a standardized, human-readable naming convention for receipt files uploaded to Google Drive. This convention aims for easy sorting and identification, with a strategy for handling duplicates.

## 1. Filename Structure

The general structure for a filename will be:

`YYYYMMDDTHHMM_<category>_<store-name>.<extension>`

**Examples:**
*   `20231026T1530_grocery_pingo-doce.jpg`
*   `20240115T0900_grocery_continente.pdf` (Assuming "modelo" is part of the specific store name, otherwise just "continente")
*   `20231105T1200_furniture_ikea.png`
*   `20240220T1845_grocery_loja.jpg` (Store name not found, using current time for an old receipt)

## 2. Component Breakdown

### 2.1. Timestamp (`YYYYMMDDTHHMM`)

*   **Format:** `YYYYMMDDTHHMM` (YearMonthDay"T"HourMinute). No hyphens, no seconds.
    *   Example: `20231026T1530` for October 26, 2023, 3:30 PM.
*   **Source:**
    1.  **Primary:** Extracted purchase date and time (to the minute) from the receipt content.
        *   If only the date is available, time can be defaulted to `T0000` (beginning of the day) or `T1200` (midday).
        *   If seconds are available from OCR, they should be truncated (not rounded) to the minute for the filename.
    2.  **Fallback:** If the purchase date/time cannot be extracted from the receipt, the **current system timestamp** (to the minute) at the moment of processing will be used.
        *   **Logging:** When the current system timestamp is used, a **WARNING** level log message must be generated (e.g., `WARN: Receipt timestamp not found for file [original_filename]. Using current system time for GDrive filename.`).
*   **Purpose:** Enables chronological sorting by filename.

### 2.2. Category (`<category>`)

*   **Format:** A short, lowercase string representing the general category.
*   **Values (examples, can be expanded):** `grocery`, `restaurant`, `fuel`, `clothes`, `electronics`, `furniture`, `other`.
*   **Source:** Determined by OpenAI extraction, future user input, or a default (e.g., `grocery`). Generic terms like "receipt" or "scan" should not be used here.
*   **Purpose:** Broad categorization.

### 2.3. Store Name (`<store-name>`)

*   **Format:** Lowercase string. Spaces within a store name replaced with a hyphen (`-`). Avoid generic components like "modelo" unless it is intrinsic to the specific store's common name (e.g. if OCR consistently returns "Continente Modelo" and it refers to a distinct chain from "Continente"). If OCR returns "Pingo Doce Supermercado", it should likely be normalized to `pingo-doce`.
    *   Examples: `pingo-doce`, `continente`, `fnac`, `ikea`.
*   **Source:** Extracted and normalized store name from the receipt.
*   **Fallback:** If the store name cannot be extracted or is empty/too generic, use `loja`.
    *   **Logging (Optional):** An INFO/DEBUG log can note the use of `loja`.
*   **Purpose:** Identifies the merchant clearly.

### 2.4. Extension (`.<extension>`)

*   **Format:** The original file extension in lowercase (e.g., `.jpg`, `.png`, `.pdf`).
*   **Source:** Derived from the original uploaded file. No conversion of file format should occur solely for naming purposes.
*   **Purpose:** Indicates the file type.

## 3. General Rules

*   **Lowercase:** All parts of the filename should be lowercase.
*   **Field Delimiter:** Fields (Timestamp, Category, Store Name) are separated by `_`.
*   **Intra-Field Delimiter:** Within a field (like Store Name), spaces are replaced by `-`.
*   **Character Set:** Stick to alphanumeric characters, underscores, and hyphens.

## 4. Duplicate Handling and File Uniqueness

*   The filename, excluding the extension, is composed of `YYYYMMDDTHHMM_<category>_<store-name>`.
*   **If a new file is uploaded that generates this exact same base name (`YYYYMMDDTHHMM_<category>_<store-name>) AND has the same file extension as an existing file in Google Drive, the new file should REPLACE the existing one.** This implies the system considers it a rescan or updated version of the exact same receipt document.
*   **If a new file is uploaded that generates this exact same base name BUT has a different file extension (e.g., `.pdf` vs. `.jpg`), both files should coexist in Google Drive.** They will share the same base name but differ in their extension.
    *   Example: `20231026T1530_grocery_pingo-doce.jpg` and `20231026T1530_grocery_pingo-doce.pdf` can both exist.
*   No artificial elements (hashes, UUIDs) will be added to ensure filename uniqueness beyond this scheme.

## 5. Implementation Notes

*   Filename construction logic should be abstracted into a dedicated utility function or class (e.g., in a `src/matosinhosgrocery/lib/filename_utils.py` module). The `ReceiptProcessingService` (or equivalent) will then call this utility, likely passing it a Data Transfer Object (DTO) containing the necessary components (parsed date/time, category, store name, original filename/extension).
*   Robust date/time parsing from OCR results is critical. If time is missing, a default (e.g., `T0000`) should be applied consistently.
*   Store name normalization logic might be needed (e.g., removing generic suffixes like "Supermercado", handling common abbreviations, consistently casing before lowercasing and hyphenating). This normalization could also be part of the `filename_utils` or a separate utility.
*   The Google Drive upload mechanism must support overwriting files if the name and extension match, and allow co-existence if only the extension differs. 