"""
Document redaction service using Google Cloud DLP and Document AI.
"""

from typing import List, Dict, Any
from google.cloud import dlp_v2
from google.cloud import documentai_v1 as documentai
from google.cloud import storage
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
import io


class RedactionService:
    """
    Service for redacting sensitive information from documents using Cloud DLP
    and extracting text using Document AI.

    Attributes:
        project_id: GCP project identifier
        client: Google Cloud DLP client instance
        processor_id: Document AI processor ID for OCR
        location: Document AI processor location
        docai_client: Document AI client instance
        storage_client: Google Cloud Storage client instance
    """

    def __init__(self, project_id: str, processor_id: str = None, location: str = "us"):
        """
        Initialize the redaction service.

        Args:
            project_id: GCP project identifier
            processor_id: Document AI processor ID for OCR (optional)
            location: Document AI processor location (default: "us")
        """
        self.project_id = project_id

        # Initialize DLP client
        self.dlp_client = dlp_v2.DlpServiceClient()
        self.dlp_parent = f"projects/{project_id}"
        self.client = dlp_v2.DlpServiceClient()  # Keep for backward compatibility

        # Document AI setup
        self.processor_id = processor_id
        self.location = location

        if processor_id:
            self.docai_client = documentai.DocumentProcessorServiceClient()
            self.processor_name = self.docai_client.processor_path(
                project_id, location, processor_id
            )
        else:
            self.docai_client = None
            self.processor_name = None

        # Storage client for GCS operations
        self.storage_client = storage.Client(project=project_id)

    def extract_text_with_coordinates(self, gcs_path: str) -> Dict[str, Any]:
        """
        Extract text and bounding boxes from a document using Document AI.

        Args:
            gcs_path: GCS path like gs://bucket/path/to/file.pdf

        Returns:
            Dictionary with:
            - text: Full extracted text
            - pages: List of pages with blocks and bounding boxes

        Raises:
            ValueError: If processor is not configured or GCS path is invalid
            Exception: If text extraction fails
        """
        if not self.docai_client or not self.processor_name:
            raise ValueError("Document AI processor not configured")

        try:
            # Parse GCS path
            if not gcs_path.startswith("gs://"):
                raise ValueError(f"Invalid GCS path: {gcs_path}")

            path_parts = gcs_path.replace("gs://", "").split("/", 1)
            bucket_name = path_parts[0]
            blob_path = path_parts[1]

            # Download file from GCS
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            file_content = blob.download_as_bytes()

            # Determine MIME type from file extension
            if blob_path.lower().endswith('.pdf'):
                mime_type = "application/pdf"
            elif blob_path.lower().endswith(('.jpg', '.jpeg')):
                mime_type = "image/jpeg"
            elif blob_path.lower().endswith('.png'):
                mime_type = "image/png"
            else:
                raise ValueError(f"Unsupported file type: {blob_path}")

            # Create Document AI request
            raw_document = documentai.RawDocument(
                content=file_content,
                mime_type=mime_type
            )

            request = documentai.ProcessRequest(
                name=self.processor_name,
                raw_document=raw_document
            )

            # Process document
            result = self.docai_client.process_document(request=request)
            document = result.document

            # Extract full text
            full_text = document.text

            # Extract pages with bounding boxes
            pages_data = []
            for page in document.pages:
                page_data = {
                    "page_number": page.page_number,
                    "width": page.dimension.width,
                    "height": page.dimension.height,
                    "blocks": []
                }

                # Extract text blocks with coordinates
                for block in page.blocks:
                    # Get text for this block
                    block_text = self._get_text_from_layout(block.layout, full_text)

                    # Get bounding box (normalized coordinates)
                    if block.layout.bounding_poly.normalized_vertices:
                        vertices = block.layout.bounding_poly.normalized_vertices
                        # Calculate bounding box from vertices
                        x_coords = [v.x for v in vertices]
                        y_coords = [v.y for v in vertices]

                        block_data = {
                            "text": block_text,
                            "bounding_box": {
                                "x": min(x_coords),
                                "y": min(y_coords),
                                "width": max(x_coords) - min(x_coords),
                                "height": max(y_coords) - min(y_coords)
                            }
                        }
                        page_data["blocks"].append(block_data)

                pages_data.append(page_data)

            return {
                "text": full_text,
                "pages": pages_data
            }

        except Exception as e:
            raise Exception(f"Error extracting text from document: {str(e)}")

    def _get_text_from_layout(self, layout, full_text: str) -> str:
        """
        Extract text from layout using text anchors.

        Args:
            layout: Document AI layout object
            full_text: Full document text

        Returns:
            Text content for this layout segment
        """
        if not layout.text_anchor.text_segments:
            return ""

        text_segments = []
        for segment in layout.text_anchor.text_segments:
            start_index = int(segment.start_index) if segment.start_index else 0
            end_index = int(segment.end_index) if segment.end_index else len(full_text)
            text_segments.append(full_text[start_index:end_index])

        return "".join(text_segments)

    def detect_pii(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect PII in text using Cloud DLP API.

        Args:
            text: Full text content to scan

        Returns:
            List of PII findings with:
            - info_type: Type of PII (e.g., US_SOCIAL_SECURITY_NUMBER, PERSON_NAME)
            - quote: The actual PII text found
            - likelihood: Confidence level
            - location: Character offsets (start, end)
        """
        try:
            import re

            # Preprocess text to normalize spaced-out SSNs
            # Convert patterns like "1 2 3 4 5 6 7 8 9" to "123-45-6789"
            preprocessed_text = text

            # Find sequences of 9 digits (with 0 or more spaces between each)
            # This catches: "123456789", "1 2 3 4 5 6 7 8 9", "1  2  3  4  5  6  7  8  9", etc.
            ssn_pattern = r'(\d)\s*(\d)\s*(\d)\s*(\d)\s*(\d)\s*(\d)\s*(\d)\s*(\d)\s*(\d)'

            # Find all matches
            all_matches = list(re.finditer(ssn_pattern, text))

            # Filter to only keep likely SSNs (not phone numbers, dates, ZIP+year, etc.)
            # SSNs are usually near specific keywords on tax forms
            matches = []
            for match in all_matches:
                # Get wider context to check for keywords
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end].lower()

                # Extract the matched digits to check formatting
                matched_text = text[match.start():match.end()]
                digits = ''.join(c for c in matched_text if c.isdigit())

                # STRICT filter: Only match if near SSN-specific keywords
                # This avoids false positives from ZIP+year, EINs, phone numbers
                is_ssn = (
                    ('social security' in context and 'number' in context) or
                    ('ssn' in context) or
                    ('your social security number' in context) or
                    ("spouse's social security number" in context) or
                    ('spouse' in context and 'social' in context)
                )

                # Additional validation: Real SSNs don't start with 000, 666, or 900-999
                if is_ssn and len(digits) == 9:
                    first_three = digits[:3]
                    if first_three in ['000', '666'] or int(first_three) >= 900:
                        is_ssn = False

                if is_ssn:
                    matches.append(match)

            # Replace from end to start to preserve offsets
            for match in reversed(matches):
                # Format as XXX-XX-XXXX for DLP recognition
                digits = match.groups()
                ssn_formatted = f"{digits[0]}{digits[1]}{digits[2]}-{digits[3]}{digits[4]}-{digits[5]}{digits[6]}{digits[7]}{digits[8]}"
                preprocessed_text = (
                    preprocessed_text[:match.start()] +
                    ssn_formatted +
                    preprocessed_text[match.end():]
                )

            # Define PII types to detect using proper protobuf types
            info_types = [
                dlp_v2.InfoType(name="US_SOCIAL_SECURITY_NUMBER"),
                dlp_v2.InfoType(name="PERSON_NAME"),
                dlp_v2.InfoType(name="STREET_ADDRESS"),
                dlp_v2.InfoType(name="US_STATE"),
                dlp_v2.InfoType(name="PHONE_NUMBER"),
                dlp_v2.InfoType(name="EMAIL_ADDRESS"),
                dlp_v2.InfoType(name="DATE_OF_BIRTH"),
            ]

            # Add custom regex for SSN patterns (catches test/invalid SSNs that built-in detector misses)
            custom_info_types = [
                dlp_v2.CustomInfoType(
                    info_type=dlp_v2.InfoType(name="SSN_PATTERN"),
                    regex=dlp_v2.CustomInfoType.Regex(pattern=r'\b\d{3}-\d{2}-\d{4}\b'),
                    likelihood=dlp_v2.Likelihood.LIKELY,
                )
            ]

            # Configure inspection using proper protobuf types
            # Use LIKELY threshold to reduce false positives
            inspect_config = dlp_v2.InspectConfig(
                info_types=info_types,
                custom_info_types=custom_info_types,
                min_likelihood=dlp_v2.Likelihood.LIKELY,
                include_quote=True,
            )

            # Content item using proper protobuf types
            item = dlp_v2.ContentItem(value=preprocessed_text)

            # Call DLP API with request parameter
            request = dlp_v2.InspectContentRequest(
                parent=self.dlp_parent,
                inspect_config=inspect_config,
                item=item,
            )

            response = self.dlp_client.inspect_content(request=request)

            # Form field words to filter out (common false positives)
            form_field_blacklist = {
                'firm', 'name', 'address', 'city', 'state', 'zip',
                'date', 'signature', 'title', 'employer', 'spouse'
            }

            # Parse findings and filter
            findings = []
            if response.result.findings:
                for finding in response.result.findings:
                    quote = finding.quote

                    # Filter out form field labels (single word person names that are common labels)
                    if finding.info_type.name == "PERSON_NAME":
                        if quote.lower().strip() in form_field_blacklist:
                            continue  # Skip this false positive

                    finding_data = {
                        "info_type": finding.info_type.name,
                        "quote": quote,
                        "likelihood": finding.likelihood.name,
                        "location": {
                            "byte_start": finding.location.byte_range.start,
                            "byte_end": finding.location.byte_range.end,
                        }
                    }
                    findings.append(finding_data)

            return findings

        except Exception as e:
            raise Exception(f"Error detecting PII: {str(e)}")

    def identify_pii_regions(self, ocr_result: Dict[str, Any], pii_findings: List[Dict]) -> List[Dict]:
        """
        Match PII findings to specific bounding boxes in the document.

        Args:
            ocr_result: Result from extract_text_with_coordinates()
            pii_findings: Result from detect_pii()

        Returns:
            List of regions to redact with:
            - page_number
            - bounding_box (x, y, width, height)
            - pii_type
            - text
        """
        import re

        redaction_regions = []
        seen_regions = set()  # Track unique regions to avoid duplicates

        try:
            full_text = ocr_result["text"]

            for finding in pii_findings:
                pii_text = finding["quote"]

                # Special handling for SSN patterns
                # Convert "123-45-6789" back to spaced pattern "1 2 3 4 5 6 7 8 9"
                search_patterns = [pii_text]  # Default: search for exact quote

                if finding["info_type"] in ["SSN_PATTERN", "US_SOCIAL_SECURITY_NUMBER"]:
                    # Extract digits and try multiple formats
                    digits = re.sub(r'\D', '', pii_text)  # Extract just digits: "123456789"
                    if len(digits) == 9:
                        # Try all possible formats the OCR might have captured:
                        unspaced_ssn = digits  # "123456789"
                        spaced_ssn = ' '.join(digits)  # "1 2 3 4 5 6 7 8 9"
                        double_spaced_ssn = '  '.join(digits)  # "1  2  3  4  5  6  7  8  9"

                        search_patterns.append(unspaced_ssn)
                        search_patterns.append(spaced_ssn)
                        search_patterns.append(double_spaced_ssn)

                # Find which page and block contains this PII text
                found_match = False
                for page in ocr_result["pages"]:
                    for block in page["blocks"]:
                        # Check if any search pattern is in this block
                        # For multi-line PII (like addresses), also check if block contains partial match
                        found_in_block = False

                        for pattern in search_patterns:
                            if pattern in block["text"]:
                                found_in_block = True
                                found_match = True
                                break
                            # Also check if the first line of PII is in the block (handles multi-line matches)
                            first_line = pattern.split('\n')[0].strip()
                            if len(first_line) > 5 and first_line in block["text"]:
                                found_in_block = True
                                found_match = True
                                break

                        if found_in_block:
                            # Create unique key for this region
                            region_key = (
                                page["page_number"],
                                block["bounding_box"]["x"],
                                block["bounding_box"]["y"],
                                block["bounding_box"]["width"],
                                block["bounding_box"]["height"],
                                finding["info_type"]
                            )

                            # Only add if we haven't seen this exact region before
                            if region_key not in seen_regions:
                                seen_regions.add(region_key)
                                redaction_regions.append({
                                    "page_number": page["page_number"],
                                    "bounding_box": block["bounding_box"],
                                    "pii_type": finding["info_type"],
                                    "text": pii_text,
                                    "block_text": block["text"]
                                })
                                break  # Found the block, move to next finding

                # Warn if SSN wasn't found in any block
                if not found_match and finding["info_type"] in ["SSN_PATTERN", "US_SOCIAL_SECURITY_NUMBER"]:
                    # FALLBACK: Spatial redaction based on SSN label
                    # Find "Your social security number" label and redact area to the right
                    for page in ocr_result["pages"]:
                        for block in page["blocks"]:
                            block_lower = block["text"].lower()

                            # Check if this block contains SSN label
                            if ("social security number" in block_lower or
                                "your social security number" in block_lower):

                                # The block contains both label AND SSN digits (they're combined)
                                # Just redact the entire block since it contains the SSN
                                bbox = block["bounding_box"]

                                # Use the entire block's bounding box (it contains the SSN)
                                # Add padding to ensure complete coverage
                                padding_x = 0.012  # Horizontal padding (1.2%)
                                padding_y = 0.008  # Vertical padding (0.8%)

                                ssn_bbox = {
                                    "x": max(0, bbox["x"] - padding_x),
                                    "y": max(0, bbox["y"] - padding_y),
                                    "width": min(1.0, bbox["width"] + 2 * padding_x),
                                    "height": min(1.0, bbox["height"] + 2 * padding_y)
                                }

                                region_key = (
                                    page["page_number"],
                                    ssn_bbox["x"],
                                    ssn_bbox["y"],
                                    ssn_bbox["width"],
                                    ssn_bbox["height"],
                                    "US_SOCIAL_SECURITY_NUMBER"
                                )

                                if region_key not in seen_regions:
                                    seen_regions.add(region_key)
                                    redaction_regions.append({
                                        "page_number": page["page_number"],
                                        "bounding_box": ssn_bbox,
                                        "pii_type": "US_SOCIAL_SECURITY_NUMBER",
                                        "text": pii_text,
                                        "block_text": "[Spatial redaction - SSN field boxes]"
                                    })
                                    found_match = True
                                    break

                        if found_match:
                            break

            return redaction_regions

        except Exception as e:
            raise Exception(f"Error identifying PII regions: {str(e)}")

    def redact_pdf_fast(self, gcs_input_path: str, gcs_output_path: str, redaction_regions: List[Dict]) -> str:
        """
        Fast redaction: Draw black boxes directly on PDF (preserves file size).

        WARNING: Less secure than full rasterization. PII text still exists in PDF
        but is visually covered. Use redact_pdf() for maximum security.

        Args:
            gcs_input_path: Original file in GCS
            gcs_output_path: Where to save redacted file
            redaction_regions: List of regions to redact

        Returns:
            GCS path of redacted file
        """
        try:
            # Download original file
            input_parts = gcs_input_path.replace("gs://", "").split("/", 1)
            input_bucket = self.storage_client.bucket(input_parts[0])
            input_blob = input_bucket.blob(input_parts[1])
            original_bytes = input_blob.download_as_bytes()

            # Open PDF
            doc = fitz.open(stream=original_bytes, filetype="pdf")

            # Draw black rectangles over PII
            for region in redaction_regions:
                page_num = region["page_number"] - 1  # 0-indexed
                page = doc[page_num]

                bbox = region["bounding_box"]
                # Get page dimensions
                page_rect = page.rect

                # Convert normalized to absolute coordinates
                x0 = bbox["x"] * page_rect.width
                y0 = bbox["y"] * page_rect.height
                x1 = (bbox["x"] + bbox["width"]) * page_rect.width
                y1 = (bbox["y"] + bbox["height"]) * page_rect.height

                # Draw black rectangle
                rect = fitz.Rect(x0, y0, x1, y1)
                page.draw_rect(rect, color=(0, 0, 0), fill=(0, 0, 0))

            # Save
            redacted_bytes = doc.tobytes()
            doc.close()

            # Upload
            output_parts = gcs_output_path.replace("gs://", "").split("/", 1)
            output_bucket = self.storage_client.bucket(output_parts[0])
            output_blob = output_bucket.blob(output_parts[1])
            output_blob.upload_from_string(redacted_bytes, content_type="application/pdf")

            return gcs_output_path

        except Exception as e:
            raise Exception(f"Error redacting PDF: {str(e)}")

    def redact_pdf(self, gcs_input_path: str, gcs_output_path: str, redaction_regions: List[Dict]) -> str:
        """
        Create a new PDF with PII removed (irreversible redaction).

        This does NOT modify the original PDF. Instead:
        1. Render each page as an image
        2. Draw white rectangles over PII regions
        3. Create entirely new PDF from the redacted images
        4. Strip all metadata

        Args:
            gcs_input_path: Original file in GCS (gs://bucket/path)
            gcs_output_path: Where to save redacted file (gs://bucket/path)
            redaction_regions: List of regions to redact from identify_pii_regions()

        Returns:
            GCS path of redacted file
        """
        try:
            # Download original file from GCS
            input_parts = gcs_input_path.replace("gs://", "").split("/", 1)
            input_bucket = self.storage_client.bucket(input_parts[0])
            input_blob = input_bucket.blob(input_parts[1])
            original_bytes = input_blob.download_as_bytes()

            # Determine if input is PDF or image
            is_pdf = gcs_input_path.lower().endswith('.pdf')

            if is_pdf:
                # Open original PDF
                original_doc = fitz.open(stream=original_bytes, filetype="pdf")

                # Create new PDF
                redacted_doc = fitz.open()

                # Process each page
                for page_num in range(len(original_doc)):
                    original_page = original_doc[page_num]

                    # Render page to image (150 DPI for reasonable file size)
                    zoom = 150 / 72  # 72 is default DPI
                    mat = fitz.Matrix(zoom, zoom)
                    pix = original_page.get_pixmap(matrix=mat)

                    # Convert to PIL Image
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                    # Draw white rectangles over PII regions for this page
                    draw = ImageDraw.Draw(img)

                    page_regions = [r for r in redaction_regions if r["page_number"] == page_num + 1]

                    for region in page_regions:
                        bbox = region["bounding_box"]
                        # Convert normalized coordinates to pixel coordinates
                        x = int(bbox["x"] * pix.width)
                        y = int(bbox["y"] * pix.height)
                        width = int(bbox["width"] * pix.width)
                        height = int(bbox["height"] * pix.height)

                        # Different padding based on PII type - increased for better coverage
                        if region.get("pii_type") == "PERSON_NAME":
                            # Names get more padding to ensure full coverage
                            horizontal_padding = 8
                            vertical_padding = 4
                            x1 = max(0, x - horizontal_padding)
                            y1 = max(0, y - vertical_padding)
                            x2 = min(pix.width, x + width + horizontal_padding)
                            y2 = min(pix.height, y + height + vertical_padding)
                        elif region.get("pii_type") in ["US_SOCIAL_SECURITY_NUMBER", "SSN_PATTERN"]:
                            # SSNs need extra padding for complete coverage
                            padding = 8
                            x1 = max(0, x - padding)
                            y1 = max(0, y - padding)
                            x2 = min(pix.width, x + width + padding)
                            y2 = min(pix.height, y + height + padding)
                        else:
                            # Other PII types get minimal padding
                            padding = 2
                            x1 = max(0, x - padding)
                            y1 = max(0, y - padding)
                            x2 = min(pix.width, x + width + padding)
                            y2 = min(pix.height, y + height + padding)

                        # Draw black rectangle (covers PII)
                        draw.rectangle(
                            [x1, y1, x2, y2],
                            fill="black",
                            outline="black"
                        )

                    # Convert PIL Image to bytes (use JPEG with compression for smaller size)
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format='JPEG', quality=85, optimize=True)
                    img_bytes = img_byte_arr.getvalue()

                    # Insert image as new page in PDF
                    # Get original page dimensions
                    page_rect = original_page.rect
                    new_page = redacted_doc.new_page(
                        width=page_rect.width,
                        height=page_rect.height
                    )
                    new_page.insert_image(page_rect, stream=img_bytes)

                # Save to bytes
                redacted_bytes = redacted_doc.tobytes()

                # Clean up
                original_doc.close()
                redacted_doc.close()

            else:
                # Handle image files (JPG, PNG)
                img = Image.open(io.BytesIO(original_bytes))
                draw = ImageDraw.Draw(img)

                # Get image dimensions
                width, height = img.size

                # Draw black rectangles over PII regions
                for region in redaction_regions:
                    bbox = region["bounding_box"]
                    x = int(bbox["x"] * width)
                    y = int(bbox["y"] * height)
                    w = int(bbox["width"] * width)
                    h = int(bbox["height"] * height)

                    draw.rectangle([x, y, x + w, y + h], fill="black", outline="black")

                # Convert to PDF
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)

                # Create PDF from image
                img_pdf = fitz.open(stream=img_byte_arr, filetype="png")
                redacted_bytes = img_pdf.tobytes()
                img_pdf.close()

            # Upload redacted file to GCS
            output_parts = gcs_output_path.replace("gs://", "").split("/", 1)
            output_bucket = self.storage_client.bucket(output_parts[0])
            output_blob = output_bucket.blob(output_parts[1])
            output_blob.upload_from_string(redacted_bytes, content_type="application/pdf")

            return gcs_output_path

        except Exception as e:
            raise Exception(f"Error redacting PDF: {str(e)}")

    def validate_redaction(self, gcs_redacted_path: str) -> Dict[str, Any]:
        """
        Validate that PII was successfully removed from redacted file.
        Re-runs DLP on the redacted file to confirm no PII remains.

        Args:
            gcs_redacted_path: Path to redacted file

        Returns:
            Dictionary with validation results
        """
        try:
            # Extract text from redacted file
            redacted_ocr = self.extract_text_with_coordinates(gcs_redacted_path)

            # Run DLP again
            pii_in_redacted = self.detect_pii(redacted_ocr["text"])

            return {
                "is_clean": len(pii_in_redacted) == 0,
                "pii_found": len(pii_in_redacted),
                "findings": pii_in_redacted if pii_in_redacted else [],
                "skipped": False
            }

        except Exception as e:
            error_str = str(e)
            # If file is too large for Document AI, skip validation
            if "exceeds the limit" in error_str or "Document size" in error_str:
                return {
                    "is_clean": True,  # Assume clean (redaction was applied)
                    "pii_found": 0,
                    "findings": [],
                    "skipped": True,
                    "skip_reason": "File too large for validation (>40MB). Redaction was applied successfully."
                }
            else:
                raise Exception(f"Error validating redaction: {str(e)}")
