from google.cloud import aiplatform
from google.cloud import storage
import vertexai
from vertexai.generative_models import GenerativeModel, Part
import json
import time
from typing import Dict, Optional
import base64

class ExtractionService:
    def __init__(self, project_id: str, location: str = "us-central1"):
        """
        Initialize Vertex AI extraction service.

        Args:
            project_id: GCP project ID
            location: Vertex AI location
        """
        self.project_id = project_id
        self.location = location
        self.storage_client = storage.Client(project=project_id)

        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)

        # Initialize Gemini 2.5 Pro model (stable, production-ready)
        # Using gemini-2.5-pro (latest stable, best for complex reasoning and extraction)
        # Alternative: gemini-2.5-flash (faster, cost-efficient)
        self.model = GenerativeModel("gemini-2.5-pro")

    def extract_tax_fields(self, gcs_vault_path: str) -> Dict[str, Optional[float]]:
        """
        Extract 5 tax fields from a redacted PDF in the vault.

        Args:
            gcs_vault_path: GCS path to redacted PDF (gs://bucket/path)

        Returns:
            Dictionary with 5 extracted fields:
            - filing_status: str
            - w2_wages: float
            - total_deductions: float
            - ira_distributions_total: float
            - capital_gain_or_loss: float
        """
        try:
            # Load PDF from GCS
            pdf_data = self._load_pdf_from_gcs(gcs_vault_path)

            # Create PDF part for Gemini
            pdf_part = Part.from_data(
                data=pdf_data,
                mime_type="application/pdf"
            )

            # Create extraction prompt
            prompt = self._create_extraction_prompt()

            # Call Gemini with retry logic for rate limits
            response = self._call_gemini_with_retry(pdf_part, prompt)

            # Parse response
            extracted_fields = self._parse_response(response.text)

            return extracted_fields

        except Exception as e:
            raise Exception(f"Failed to extract tax fields: {str(e)}")

    def _call_gemini_with_retry(self, pdf_part, prompt, max_retries=3):
        """
        Call Gemini with exponential backoff retry for rate limits (429 errors)

        Args:
            pdf_part: PDF part to send to Gemini
            prompt: Extraction prompt
            max_retries: Maximum number of retry attempts

        Returns:
            Gemini response
        """
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content([pdf_part, prompt])
                return response
            except Exception as e:
                error_str = str(e)

                # Check if it's a rate limit error (429)
                if "429" in error_str or "Resource exhausted" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    if attempt < max_retries - 1:
                        # Exponential backoff: 2^attempt seconds (2s, 4s, 8s)
                        wait_time = 2 ** (attempt + 1)
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"Rate limit exceeded after {max_retries} attempts. Please try again later.")
                else:
                    # Not a rate limit error, raise immediately
                    raise

    def _load_pdf_from_gcs(self, gcs_path: str) -> bytes:
        """Load PDF file from GCS"""
        try:
            # Parse GCS path
            if not gcs_path.startswith("gs://"):
                raise ValueError(f"Invalid GCS path: {gcs_path}")

            parts = gcs_path.replace("gs://", "").split("/", 1)
            bucket_name = parts[0]
            blob_path = parts[1]

            # Download file
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)

            if not blob.exists():
                raise FileNotFoundError(f"File not found: {gcs_path}")

            pdf_data = blob.download_as_bytes()

            return pdf_data

        except Exception as e:
            raise Exception(f"Failed to load PDF from GCS: {str(e)}")

    def _create_extraction_prompt(self) -> str:
        """Create structured prompt for tax field extraction"""
        prompt = """You are a tax document analyzer. Extract EXACTLY these 5 fields from this IRS Form 1040 tax document.

IMPORTANT INSTRUCTIONS:
1. This is a REDACTED document - some information has been removed (shown as white boxes)
2. Extract ONLY the 5 fields listed below
3. Return ONLY a JSON object, no other text
4. Use null for any field you cannot find
5. For monetary values, extract as numbers without $ or commas (e.g., 75000.00)
6. For filing status, return one of: "Single", "Married Filing Jointly", "Married Filing Separately", "Head of Household", "Qualifying Surviving Spouse"

FIELDS TO EXTRACT:

1. filing_status (string):
   - Look for the "Filing Status" section near the top
   - Return the checked option exactly as written

2. w2_wages (number):
   - Look for Line 1a: "Total amount from Form(s) W-2, box 1"
   - This is in the "Income" section
   - Extract the dollar amount as a number

3. total_deductions (number):
   - Look for Line 12e: "Standard deduction or itemized deductions"
   - This is in the "Tax and Credits" section
   - Extract the dollar amount as a number

4. ira_distributions_total (number):
   - Look for Line 4a or 4b: "IRA distributions"
   - Line 4a shows total distributions, Line 4b shows taxable amount
   - Prefer Line 4a if both are present, otherwise use Line 4b
   - This is in the "Income" section
   - Extract the dollar amount as a number

5. capital_gain_or_loss (number):
   - Look for Line 7a: "Capital gain or (loss)"
   - This is in the "Income" section
   - Extract the dollar amount as a number
   - Can be negative (loss) or positive (gain)

RESPONSE FORMAT (return ONLY this JSON, nothing else):
{
  "filing_status": "Single",
  "w2_wages": 75000.00,
  "total_deductions": 12550.00,
  "ira_distributions_total": 5000.00,
  "capital_gain_or_loss": 2500.00
}

If any field is not visible or cannot be determined, use null:
{
  "filing_status": null,
  "w2_wages": null,
  "total_deductions": 12550.00,
  "ira_distributions_total": null,
  "capital_gain_or_loss": 2500.00
}

Now extract these 5 fields from the provided tax document. Return ONLY the JSON object.
"""
        return prompt

    def _parse_response(self, response_text: str) -> Dict:
        """Parse Gemini response and extract fields"""
        try:
            # Remove markdown code blocks if present
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]

            cleaned_text = cleaned_text.strip()

            # Parse JSON
            fields = json.loads(cleaned_text)

            # Validate and normalize fields
            result = {
                "filing_status": fields.get("filing_status"),
                "w2_wages": self._to_float(fields.get("w2_wages")),
                "total_deductions": self._to_float(fields.get("total_deductions")),
                "ira_distributions_total": self._to_float(fields.get("ira_distributions_total")),
                "capital_gain_or_loss": self._to_float(fields.get("capital_gain_or_loss"))
            }

            return result

        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response from Gemini: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to parse extraction response: {str(e)}")

    def _to_float(self, value) -> Optional[float]:
        """Convert value to float, handling null and various formats"""
        if value is None:
            return None

        try:
            # Remove $ and commas if present
            if isinstance(value, str):
                value = value.replace("$", "").replace(",", "").strip()
                if value.lower() == "null" or value == "":
                    return None

            return float(value)
        except (ValueError, TypeError):
            return None
