import base64
import json
import logging
from typing import Dict, Any, Optional, List

from openai import AsyncOpenAI, OpenAIError

from matosinhosgrocery.config import settings

logger = logging.getLogger(__name__)

# Initialize the AsyncOpenAI client globally if the API key is present
# This avoids re-creating it on every call if the key doesn't change.
# However, for functions/lambdas, it might be better to initialize inside the function
# if the settings could change or if it's a short-lived process.
# For a long-running server, this is generally fine.
client: Optional[AsyncOpenAI] = None
if settings.OPENAI_API_KEY:
    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        client = None
else:
    logger.warning("OPENAI_API_KEY is not set. OpenAI client will not be functional.")


def get_receipt_parsing_prompt() -> List[Dict[str, Any]]:
    """
    Defines the system and user prompt structure for OpenAI receipt parsing.
    The user prompt will need the base64 image data to be inserted.
    """
    system_prompt = (
        "You are an expert receipt processing AI. Your task is to analyze an image of a grocery receipt "
        "and extract key information. You must return the information as a valid JSON object. "
        "The JSON object should strictly follow this structure: "
        "{ \n"
        '  "store_name": "STRING | null", \n'
        '  "purchase_date": "YYYY-MM-DD STRING | null", \n'
        '  "purchase_time": "HH:MM STRING | null", \n'
        '  "total_amount": "FLOAT | null", \n'
        '  "items": [ \n'
        "    { \n"
        '      "original_name": "STRING", \n'
        '      "generalized_name": "STRING (English, lowercase, common, simplified version of original_name)", \n'
        '      "quantity": "FLOAT (default to 1.0 if not specified)", \n'
        '      "price_per_unit": "FLOAT", \n'
        '      "tags": ["STRING", "STRING", "..."], \n'
        '      "weight_volume_text": "STRING | null (e.g., "200g", "1.5L", "6 pack")", \n'
        '      "parsed_weight_grams": "FLOAT | null (numeric value in grams, e.g., 200.0 for "200g")", \n'
        '      "parsed_volume_ml": "FLOAT | null (numeric value in milliliters, e.g., 1500.0 for "1.5L")" \n'
        "    } \n"
        "    // ... more items \n"
        "  ] \n"
        "}"
        "Important rules for extraction: \n"
        "1. Dates & Time: Parse dates into YYYY-MM-DD format. Parse time into HH:MM format (24-hour). If the year is ambiguous (e.g., only day/month), try to infer it logically (current year or last year if the date seems recent). If date or time is completely unreadable or not present, use null for the respective field. \n"
        "2. Total Amount: Extract the final total amount paid. If not found, use null. \n"
        "3. Items: \n"
        "   - For each item, extract its original name as accurately as possible. \n"
        "   - Create a 'generalized_name' by: 1. Translating the item name to English if it's in another language. 2. Converting to lowercase. 3. Simplifying it to a common, generic English term for the item (e.g., 'OVOS SOLO CLASSE M' should become 'eggs'; 'Leite Mimosa Meio-Gordo' should become 'milk'). 4. Removing brand names unless essential or very generic (e.g., 'Coca-Cola'). \n"
        "   - Extract quantity. This is the number of units for which 'price_per_unit' is given (e.g., if 2 items are bought for $5 each, quantity is 2, price_per_unit is 5. If 0.5kg is bought at $4/kg, quantity is 0.5, price_per_unit is 4). Default to 1.0 if not specified. \n"
        "   - Extract the price per unit. \n"
        "   - Create 'tags': Extract descriptive keywords from the 'original_name' and 'generalized_name' in English. These should include: \n"
        "        1. Specific attributes from 'original_name' not fully captured by 'generalized_name' (e.g., brand, size, variant, flavor - for 'OVOS SOLO CLASSE M' generalized to 'eggs', tags like ['solo', 'classe m', 'eggs']). \n"
        "        2. Broader categories related to the 'generalized_name' (e.g., if 'generalized_name' is 'raspberries', include ['berries', 'fruit']). \n"
        "     The 'tags' field should be an array of strings (e.g., [\"attribute\", \"category\", \"brand\"]), or an empty array [] if no distinct tags are applicable. All tags must be in English and lowercase. Aim for concise, informative tags. Avoid redundancy where possible (e.g., if generalized_name is 'apple', a tag 'apple' might be redundant unless it adds specific context not otherwise present). \n"
        '   - Extract \'weight_volume_text\': The textual representation of weight or volume if present (e.g., "200g", "1.5L", "6 x 330ml"). Set to null if not present. \n'
        '   - Extract \'parsed_weight_grams\': If weight is specified (e.g., in grams, kg, oz, lb), convert it to a numerical value in GRAMS. Example: "200g" -> 200.0; "0.5kg" -> 500.0; "1kg" -> 1000.0. Set to null if not applicable or not present. \n'
        '   - Extract \'parsed_volume_ml\': If volume is specified (e.g., in milliliters, L, cl), convert it to a numerical value in MILLILITERS. Example: "1.5L" -> 1500.0; "75cl" -> 750.0; "330ml" -> 330.0. Set to null if not applicable or not present. \n'
        "4. If any top-level field (store_name, purchase_date, purchase_time, total_amount) cannot be determined, its value should be null. \n"
        "5. The 'items' array should be empty ([]) if no items can be clearly identified, but never null. Each item in the array must have all specified item fields, using null where appropriate. \n"
        "6. Ensure the output is ONLY the JSON object. Do not include any other text, explanations, or markdown formatting like '''json ... '''.\n"
        "7. If time is not present on the receipt, set purchase_time to null."
    )

    user_prompt_template = [
        {
            "type": "text",
            "text": "Please analyze this receipt image and extract the information according to the rules and JSON format provided in the system prompt.",
        },
        {
            "type": "image_url",
            "image_url": {
                "url": "",  # To be filled with base64 encoded image
                "detail": "high",  # Use high detail for better accuracy
            },
        },
    ]
    return [
        {"role": "system", "content": system_prompt},
        # The user message with the image will be constructed dynamically
    ]


async def extract_receipt_data_from_image(
    image_bytes: bytes, file_name: Optional[str] = "receipt.jpg"
) -> Dict[str, Any]:
    """
    Sends a receipt image to OpenAI Vision API (GPT-4o or similar) for data extraction.

    Args:
        image_bytes: The byte content of the image file.
        file_name: Optional name of the file, primarily for logging.

    Returns:
        A dictionary containing the extracted receipt data, conforming to the specified JSON structure.
        Returns a basic error structure if processing fails.
    """
    if not client:
        logger.error(
            "OpenAI client is not initialized (API key likely missing). Cannot process receipt."
        )
        # Consistent error structure might be useful for the service layer
        return {
            "error": "OpenAI client not initialized",
            "store_name": None,
            "purchase_date": None,
            "total_amount": None,
            "items": [],
        }

    try:
        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        # Determine MIME type - assuming jpeg for now if not obvious, but png is also common
        # For more robustness, consider using python-magic or inferring from file_name if available
        mime_type = "image/jpeg"
        if file_name and file_name.lower().endswith(".png"):
            mime_type = "image/png"

        data_url = f"data:{mime_type};base64,{base64_image}"

        prompt_messages = get_receipt_parsing_prompt()
        # Construct the user message with the image
        user_message_with_image = [
            {
                "type": "text",
                "text": "Please analyze this receipt image and extract the information according to the rules and JSON format provided in the system prompt.",
            },
            {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
        ]

        full_messages = [prompt_messages[0]] + [
            {"role": "user", "content": user_message_with_image}
        ]

        logger.info(
            f"Sending receipt image '{file_name}' to OpenAI for processing. Image size: {len(image_bytes)} bytes."
        )

        completion = await client.chat.completions.create(
            model="gpt-4o",  # Or "gpt-4-turbo" or other capable vision model
            messages=full_messages,  # type: ignore
            # The type checker might complain about List[Dict] vs specific MessageParam types.
            # openai SDK v1 uses Pydantic models. Explicitly casting or using model constructors
            # might be needed if strict type checking is an issue.
            # For now, this structure generally works.
            max_tokens=2048,  # Adjust as needed, ensure it's enough for detailed receipts
            temperature=0.2,  # Lower temperature for more deterministic output
        )

        response_content = completion.choices[0].message.content
        if not response_content:
            logger.error("OpenAI API returned an empty response content.")
            raise ValueError("OpenAI API returned empty content.")

        logger.debug(f"OpenAI raw response: {response_content}")

        # The model should return just JSON. If it includes markdown, try to strip it.
        if response_content.startswith("```json"):
            response_content = response_content[len("```json") :].strip()
            if response_content.endswith("```"):
                response_content = response_content[: -len("```")]

        extracted_data = json.loads(response_content)
        logger.info(
            f"Successfully extracted data from receipt '{file_name}' using OpenAI."
        )
        return extracted_data

    except OpenAIError as e:
        logger.exception(
            f"OpenAI API error while processing receipt '{file_name}': {e}"
        )
        return {
            "error": str(e),
            "store_name": None,
            "purchase_date": None,
            "total_amount": None,
            "items": [],
        }
    except json.JSONDecodeError as e:
        logger.exception(
            f"Failed to parse JSON response from OpenAI for receipt '{file_name}'. Response: {response_content}. Error: {e}"
        )
        return {
            "error": "Invalid JSON response from OpenAI",
            "raw_response": response_content,
            "store_name": None,
            "purchase_date": None,
            "total_amount": None,
            "items": [],
        }
    except Exception as e:
        logger.exception(
            f"An unexpected error occurred in extract_receipt_data_from_image for '{file_name}': {e}"
        )
        return {
            "error": "Unexpected error during OpenAI processing",
            "store_name": None,
            "purchase_date": None,
            "total_amount": None,
            "items": [],
        }
