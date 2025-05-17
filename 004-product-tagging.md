# 004: Product Tagging

## Objective

To enhance product data capture by extracting and storing specific keywords or attributes from the original product name as "tags". This complements the `generalized_name` by preserving details that might be lost during the generalization process.

## Background

The current system extracts an `original_name` (e.g., "ovos grandes M") and a `generalized_name` (e.g., "eggs"). While generalization is useful for categorization and analysis, it can discard valuable specifics about the product (e.g., "grandes M" which indicates size and class).

This feature aims to capture these specifics as a list of tags.

## Requirements

1.  **Tag Extraction**:
    *   The OpenAI service should be prompted to extract relevant keywords or attributes from the `original_name` of each product.
    *   These tags should be in English.
    *   Tags should represent characteristics like size, brand (if not part of generalization), variant, specific type, etc.
    *   For example, if `original_name` is "Leite Mimosa Meio-Gordo C/Cálcio 1L", and `generalized_name` is "milk":
        *   Potential tags could include: ["mimosa", "meio-gordo", "cálcio", "1l"].

2.  **Data Storage**:
    *   The `ProductEntry` table in the database needs a new field to store these tags.
    *   This field should store an array of strings (the tags).

3.  **API and Service Layer**:
    *   The `ReceiptProcessingService` must be updated to receive tags from the OpenAI client.
    *   It must then store these tags in the new database field for each `ProductEntry`.
    *   The existing API endpoint for receipt processing will implicitly support this, as the change is internal to the service and data model.

## OpenAI Prompt Modification

The prompt for OpenAI will be updated to include a `tags` field in the item structure:

```json
{
  "original_name": "STRING",
  "generalized_name": "STRING (English, lowercase, common, simplified version of original_name)",
  "quantity": "FLOAT (default to 1.0 if not specified)",
  "price_per_unit": "FLOAT",
  "tags": ["STRING", "STRING", "..."] // New field
}
```

Instructions will be added to guide OpenAI on how to populate the `tags` field, emphasizing the extraction of specific, descriptive English keywords from the `original_name` that are not covered by the `generalized_name`.

## Database Schema Change

The `ProductEntry` model will be updated to include:

*   `tags`: `JSON` (or equivalent for storing a list of strings)

## Impact

*   Richer product data, allowing for more detailed analysis and querying.
*   No immediate change to filename conventions or user-facing bot interaction, but provides a foundation for future enhancements. 