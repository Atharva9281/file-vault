from google.cloud import aiplatform
from google.cloud import storage
from google.cloud import documentai_v1 as documentai
import vertexai
from vertexai.generative_models import GenerativeModel, Part
import json
import time
from typing import Dict, Optional
import base64

class ExtractionService:
    def __init__(self, project_id: str, location: str = "us-central1",
                 docai_processor_id: str = None, docai_location: str = "us"):
        """
        Initialize Vertex AI extraction service with Document AI OCR.

        Args:
            project_id: GCP project ID
            location: Vertex AI location
            docai_processor_id: Document AI processor ID for OCR
            docai_location: Document AI processor location
        """
        self.project_id = project_id
        self.location = location
        self.storage_client = storage.Client(project=project_id)

        # Initialize Document AI for OCR
        self.docai_processor_id = docai_processor_id
        self.docai_location = docai_location

        if docai_processor_id:
            self.docai_client = documentai.DocumentProcessorServiceClient()
            self.processor_name = self.docai_client.processor_path(
                project_id, docai_location, docai_processor_id
            )
        else:
            self.docai_client = None
            self.processor_name = None

        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)

        # Initialize Gemini 2.5 Pro model (stable, production-ready)
        # Using gemini-2.5-pro (latest stable, best for complex reasoning and extraction)
        # Now using Document AI OCR for accurate text extraction, Gemini for field parsing
        self.model = GenerativeModel("gemini-2.5-pro")

    def extract_tax_fields(self, gcs_vault_path: str) -> Dict[str, Optional[float]]:
        """
        Extract 5 tax fields from a redacted PDF in the vault.
        Uses Document AI OCR for accurate text extraction, then Gemini for field parsing.

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
            # Step 1: Extract accurate text using Document AI OCR
            ocr_text = self._extract_text_with_docai(gcs_vault_path)

            # Step 2: Create extraction prompt with OCR text
            prompt = self._create_extraction_prompt_from_text(ocr_text)

            # Step 3: Call Gemini to parse fields from text
            response = self._call_gemini_with_retry_text(prompt)

            # Step 4: Parse response
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

    def _extract_text_with_docai(self, gcs_path: str) -> str:
        """
        Extract text from PDF using Document AI OCR.
        This provides much more accurate text extraction than Gemini vision.

        Args:
            gcs_path: GCS path to PDF (gs://bucket/path)

        Returns:
            Extracted text from the PDF

        Raises:
            ValueError: If Document AI is not configured
            Exception: If OCR fails
        """
        if not self.docai_client or not self.processor_name:
            raise ValueError("Document AI processor not configured for OCR")

        try:
            # Parse GCS path
            if not gcs_path.startswith("gs://"):
                raise ValueError(f"Invalid GCS path: {gcs_path}")

            parts = gcs_path.replace("gs://", "").split("/", 1)
            bucket_name = parts[0]
            blob_path = parts[1]

            # Download file from GCS
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)

            if not blob.exists():
                raise FileNotFoundError(f"File not found: {gcs_path}")

            file_content = blob.download_as_bytes()

            # Determine MIME type
            mime_type = "application/pdf"

            # Create Document AI request
            raw_document = documentai.RawDocument(
                content=file_content,
                mime_type=mime_type
            )

            request = documentai.ProcessRequest(
                name=self.processor_name,
                raw_document=raw_document
            )

            # Process document with Document AI OCR
            result = self.docai_client.process_document(request=request)
            document = result.document

            # Log OCR text for debugging (first 2000 chars)
            ocr_preview = document.text[:2000] if len(document.text) > 2000 else document.text
            print(f"[DEBUG] Document AI OCR Text Preview (first 2000 chars):\n{ocr_preview}\n")
            print(f"[DEBUG] Total OCR text length: {len(document.text)} characters")

            # Return extracted text
            return document.text

        except Exception as e:
            raise Exception(f"Failed to extract text with Document AI: {str(e)}")

    def _call_gemini_with_retry_text(self, prompt: str, max_retries=3):
        """
        Call Gemini with text prompt and exponential backoff retry for rate limits.

        Args:
            prompt: Text prompt for Gemini
            max_retries: Maximum number of retry attempts

        Returns:
            Gemini response
        """
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)

                # Log Gemini response for debugging
                print(f"[DEBUG] Gemini raw response:\n{response.text}\n")

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

    def _create_extraction_prompt_from_text(self, ocr_text: str) -> str:
        """
        Create structured prompt for tax field extraction from OCR text.
        Uses Document AI OCR text instead of Gemini vision for better accuracy.

        Args:
            ocr_text: OCR text extracted from Document AI

        Returns:
            Formatted prompt for Gemini
        """
        prompt = f"""You are a tax document analyzer. You have been given the OCR text from an IRS Form 1040 tax document. Extract EXACTLY these 5 fields.

IMPORTANT INSTRUCTIONS:
1. The OCR text may have been extracted from a REDACTED document
2. Extract ONLY the 5 fields listed below
3. Return ONLY a JSON object, no other text
4. Use null for any field you cannot find in the text
5. For monetary values, extract as numbers without $ or commas (e.g., 75000.00)
6. For filing status, return one of: "Single", "Married Filing Jointly", "Married Filing Separately", "Head of Household", "Qualifying Surviving Spouse"

FIELDS TO EXTRACT:

1. filing_status (string):
   - Look for the "Filing Status" section near the top of the form
   - Common options: "Single", "Married filing jointly", "Married filing separately", "Head of household", "Qualifying surviving spouse"
   - The checkbox mark (☑ or X) might not OCR well, so look for:
     * Text that appears AFTER a checkbox mark or X
     * Lines with "Single", "Married", "Head of household" keywords
     * Any indication of which filing status was selected
   - If you cannot determine which box is checked, return null
   - Return the filing status text exactly as written (capitalization matters)

2. w2_wages (number):
   - Look for Line 1a, Line 1, or Line 1a-c: related to W-2 wages
   - Common labels: "Wages, salaries, tips", "Total amount from Form(s) W-2", "W-2 wages"
   - This is usually the FIRST line in the Income section
   - The amount is typically large (e.g., 50,000 to 200,000)
   - Look for numbers near these keywords: "W-2", "wages", "salaries", "Line 1"
   - Extract the dollar amount as a number (remove $, commas)

3. total_deductions (number):
   - Look for Line 12e: "Standard deduction or itemized deductions" or similar text
   - This is in the "Tax and Credits" or "Deductions" section
   - Extract the dollar amount as a number

4. ira_distributions_total (number):
   - Look for Line 4a or 4b: "IRA distributions"
   - Line 4a shows total distributions, Line 4b shows taxable amount
   - Prefer Line 4a if both are present, otherwise use Line 4b
   - This is in the "Income" section
   - Extract the dollar amount as a number

5. capital_gain_or_loss (number):
   - Look for Line 7a or 7: "Capital gain or (loss)"
   - This is in the "Income" section
   - Extract the dollar amount as a number
   - Can be negative (loss) or positive (gain)

OCR TEXT FROM FORM 1040:
{ocr_text}

RESPONSE FORMAT (return ONLY this JSON, nothing else):
{{
  "filing_status": "Single",
  "w2_wages": 75000.00,
  "total_deductions": 12550.00,
  "ira_distributions_total": 5000.00,
  "capital_gain_or_loss": 2500.00
}}

If any field is not visible in the OCR text, use null:
{{
  "filing_status": null,
  "w2_wages": null,
  "total_deductions": 12550.00,
  "ira_distributions_total": null,
  "capital_gain_or_loss": 2500.00
}}

Now extract these 5 fields from the OCR text above. Return ONLY the JSON object.
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

            # Log parsed result for debugging
            print(f"[DEBUG] Parsed extraction result: {result}")

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
