#!/usr/bin/env python3
"""
Google Gemini AI Based PDF Extractor
Uses Google AI Studio API (free tier) for superior OCR and table extraction
"""

import os
import csv
import json
from datetime import datetime
from typing import List, Dict, Any
import google.generativeai as genai
from pdf2image import convert_from_path
import pandas as pd
import fitz
from PIL import Image

# Increase PIL's image size limit for large PDF pages
# Default is ~89 million pixels, we increase to 500 million for high-res PDFs
Image.MAX_IMAGE_PIXELS = 500000000


class GeminiExtractor:
    """Extract voter list data using Google Gemini Vision API"""

    def __init__(self, pdf_path: str, api_key: str = None):
        """
        Initialize Gemini extractor

        Args:
            pdf_path: Path to PDF file
            api_key: Google AI Studio API key (or set GEMINI_API_KEY env var)
        """
        self.pdf_path = pdf_path
        self.pdf_name = os.path.basename(pdf_path)
        self.num_pages = self._get_page_count()

        # Configure Gemini API
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError(
                "API key required. Set GEMINI_API_KEY environment variable or pass api_key parameter.\n"
                "Get your free API key from: https://aistudio.google.com/app/apikey"
            )

        genai.configure(api_key=self.api_key)
        # Using gemini-2.5-flash (latest stable flash model)
        # Alternative models: 'gemini-2.5-pro', 'gemini-2.0-flash-exp'
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def _get_page_count(self) -> int:
        """Get total pages in PDF"""
        try:
            doc = fitz.open(self.pdf_path)
            count = len(doc)
            doc.close()
            return count
        except:
            return 0

    def extract_page_as_csv(self, page_number: int, dpi: int = 300, max_retries: int = 3) -> str:
        """
        Extract voter data from a page using Gemini Vision API

        Args:
            page_number: Page to extract
            dpi: Image resolution

        Returns:
            CSV formatted string with voter data
        """
        print(f"Processing page {page_number} with Gemini AI...")

        # Convert PDF page to image
        images = convert_from_path(
            self.pdf_path,
            dpi=dpi,
            first_page=page_number,
            last_page=page_number
        )

        if not images:
            return ""

        # Save image temporarily
        temp_image_path = f"temp_page_{page_number}.png"
        images[0].save(temp_image_path)

        # Retry logic for API errors
        for attempt in range(max_retries):
            try:
                # Upload image to Gemini
                uploaded_file = genai.upload_file(temp_image_path)

                # Create prompt for structured extraction
                prompt = """
You are extracting data from a Tamil voter list (வாக்காளர் பட்டியல்) PDF page.

This page contains a table with voter information. Extract ALL voters from this page into a CSV format.

For each voter, extract these columns:
1. Serial Number (வரிசை எண்) - a number
2. Division No (பிரிவு எண்) - if visible
3. House No (வீட்டு எண்) - if visible
4. Voter Name (வாக்காளரின் பெயர்) - Tamil name
5. Relationship Code (உறவு முறை) - symbols like F, H, W, S, D etc
6. Relative Name (உறவினர் பெயர்) - Tamil name of relative
7. Age (வயது) - number
8. Gender/Caste Code (இனம்) - code or classification
9. Voter ID No (வாக்காளர் அடையாள அட்டை எண்) - format like TN27/168/xxxxxxx

IMPORTANT INSTRUCTIONS:
- Extract EVERY voter from the page - do not skip any
- Each voter should be ONE row in the CSV
- If a field is not visible or unclear, leave it empty
- Keep Tamil text exactly as shown
- Return ONLY the CSV data, no explanations
- Use comma as delimiter
- Do NOT include column headers
- Start each row with a serial number

Example output format:
1,168,A1-1,ஜெயந்தி,F,லெட்சுமிநரசிம்மன்,35,பெண்,TN27/168/0489377
2,168,A1-2,முத்து,H,செல்வம்,42,ஆண்,TN27/168/0489378

Now extract all voters from this image:
"""

                # Generate response
                response = self.model.generate_content([uploaded_file, prompt])

                # Clean up temp file
                os.remove(temp_image_path)

                return response.text.strip()

            except Exception as e:
                print(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    # Final failure
                    print(f"Error processing with Gemini after {max_retries} attempts")
                    # Clean up temp file on error
                    if os.path.exists(temp_image_path):
                        os.remove(temp_image_path)
                    return ""

    def extract_metadata(self, page_number: int = 1, dpi: int = 300) -> Dict[str, Any]:
        """
        Extract metadata from first page using Gemini

        Args:
            page_number: Metadata page number
            dpi: Image resolution

        Returns:
            Dictionary with metadata fields
        """
        print(f"Extracting metadata from page {page_number}...")

        # Convert page to image
        images = convert_from_path(
            self.pdf_path,
            dpi=dpi,
            first_page=page_number,
            last_page=page_number
        )

        if not images:
            return {}

        # Save image temporarily
        temp_image_path = f"temp_metadata.png"
        images[0].save(temp_image_path)

        try:
            uploaded_file = genai.upload_file(temp_image_path)

            prompt = """
Extract metadata from this Tamil voter list (வாக்காளர் பட்டியல்) page.

Look for and extract:
1. Assembly Constituency Number (சட்டமன்ற தொகுதியின் எண்)
2. Part Number (பாகம் எண்)
3. Year (ஆண்டு)
4. Qualifying Date (தகுதியேற்படுத்தும் நாள்)
5. State name (மாநிலம்)
6. Constituency name (தொகுதியின் பெயர்)

Return as JSON format with these exact keys:
{
  "assembly_constituency_no": "number",
  "part_no": "number",
  "year": "year",
  "qualifying_date": "DD/MM/YYYY",
  "state": "state name",
  "constituency_name": "name"
}

Only return the JSON, no explanations.
"""

            response = self.model.generate_content([uploaded_file, prompt])

            # Clean up
            os.remove(temp_image_path)

            # Parse JSON response
            try:
                # Extract JSON from response (handle code blocks)
                response_text = response.text.strip()
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()

                metadata = json.loads(response_text)
                metadata['pdf_name'] = self.pdf_name
                metadata['extraction_date'] = datetime.now().isoformat()
                return metadata
            except:
                return {'pdf_name': self.pdf_name, 'extraction_date': datetime.now().isoformat()}

        except Exception as e:
            print(f"Error extracting metadata: {e}")
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
            return {'pdf_name': self.pdf_name, 'extraction_date': datetime.now().isoformat()}

    def extract_all_pages(self, start_page: int = 2) -> List[Dict[str, Any]]:
        """
        Extract voter data from all pages

        Args:
            start_page: First data page (default: 2, after metadata)

        Returns:
            List of voter dictionaries
        """
        all_voters = []

        for page_num in range(start_page, self.num_pages + 1):
            csv_text = self.extract_page_as_csv(page_num)

            if not csv_text:
                continue

            # Parse CSV text into voter records
            lines = csv_text.strip().split('\n')
            for line in lines:
                if not line.strip():
                    continue

                try:
                    parts = line.split(',')
                    if len(parts) >= 4:  # At least serial, name required
                        voter = {
                            'serial_no': parts[0].strip() if len(parts) > 0 else '',
                            'division_no': parts[1].strip() if len(parts) > 1 else '',
                            'house_no': parts[2].strip() if len(parts) > 2 else '',
                            'voter_name': parts[3].strip() if len(parts) > 3 else '',
                            'relationship_code': parts[4].strip() if len(parts) > 4 else '',
                            'relative_name': parts[5].strip() if len(parts) > 5 else '',
                            'age': parts[6].strip() if len(parts) > 6 else '',
                            'gender_caste_code': parts[7].strip() if len(parts) > 7 else '',
                            'voter_id': parts[8].strip() if len(parts) > 8 else '',
                            'page_number': page_num
                        }
                        all_voters.append(voter)
                except Exception as e:
                    print(f"Error parsing line: {line[:50]}... - {e}")
                    continue

        return all_voters

    def extract_all_pages_streaming(self, output_path: str, start_page: int = 2) -> int:
        """
        Extract voter data from all pages with STREAMING to CSV
        Writes data immediately as each page is processed - LOW MEMORY USAGE

        Args:
            output_path: Output CSV file path
            start_page: First data page (default: 2, after metadata)

        Returns:
            Total number of voters extracted
        """
        headers = [
            ('serial_no', 'Serial Number (வரிசை எண்)'),
            ('division_no', 'Division No (பிரிவு எண்)'),
            ('house_no', 'House No (வீட்டு எண்)'),
            ('voter_name', 'Voter Name (வாக்காளரின் பெயர்)'),
            ('relationship_code', 'Relationship Code (உறவு முறை)'),
            ('relative_name', 'Relative Name (உறவினர் பெயர்)'),
            ('age', 'Age (வயது)'),
            ('gender_caste_code', 'Gender/Caste Code (இனம்)'),
            ('voter_id', 'Voter ID No (வாக்காளர் அடையாள அட்டை எண்)')
        ]

        total_voters = 0

        # Open CSV file once and write incrementally
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Write header once
            writer.writerow([h[1] for h in headers])

            # Process each page and write immediately
            for page_num in range(start_page, self.num_pages + 1):
                print(f"Processing page {page_num}/{self.num_pages}...")

                csv_text = self.extract_page_as_csv(page_num)

                if not csv_text:
                    continue

                # Parse CSV text into voter records
                lines = csv_text.strip().split('\n')
                page_voters = 0

                for line in lines:
                    if not line.strip():
                        continue

                    try:
                        parts = line.split(',')
                        if len(parts) >= 4:  # At least serial, name required
                            # Write directly to CSV - no memory accumulation!
                            row = [
                                parts[0].strip() if len(parts) > 0 else '',  # serial_no
                                parts[1].strip() if len(parts) > 1 else '',  # division_no
                                parts[2].strip() if len(parts) > 2 else '',  # house_no
                                parts[3].strip() if len(parts) > 3 else '',  # voter_name
                                parts[4].strip() if len(parts) > 4 else '',  # relationship_code
                                parts[5].strip() if len(parts) > 5 else '',  # relative_name
                                parts[6].strip() if len(parts) > 6 else '',  # age
                                parts[7].strip() if len(parts) > 7 else '',  # gender_caste_code
                                parts[8].strip() if len(parts) > 8 else '',  # voter_id
                            ]
                            writer.writerow(row)
                            page_voters += 1
                            total_voters += 1

                    except Exception as e:
                        print(f"  Warning: Error parsing line: {str(e)[:50]}")
                        continue

                print(f"  ✓ Extracted {page_voters} voters from page {page_num}")
                # CSV is already written, data can be garbage collected

        print(f"\n✓ Total: {total_voters} voters saved to {output_path}")
        return total_voters

    def save_to_csv(self, voters: List[Dict[str, Any]], output_path: str):
        """
        Save voters to CSV file

        Args:
            voters: List of voter dictionaries
            output_path: Output CSV path
        """
        headers = [
            ('serial_no', 'Serial Number (வரிசை எண்)'),
            ('division_no', 'Division No (பிரிவு எண்)'),
            ('house_no', 'House No (வீட்டு எண்)'),
            ('voter_name', 'Voter Name (வாக்காளரின் பெயர்)'),
            ('relationship_code', 'Relationship Code (உறவு முறை)'),
            ('relative_name', 'Relative Name (உறவினர் பெயர்)'),
            ('age', 'Age (வயது)'),
            ('gender_caste_code', 'Gender/Caste Code (இனம்)'),
            ('voter_id', 'Voter ID No (வாக்காளர் அடையாள அட்டை எண்)')
        ]

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow([h[1] for h in headers])

            # Write data
            for voter in voters:
                row = [voter.get(h[0], '') for h in headers]
                writer.writerow(row)

        print(f"✓ Saved {len(voters)} voters to {output_path}")


def main():
    """Test Gemini extractor"""
    # Check for API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set!")
        print("\nTo use this extractor:")
        print("1. Get free API key from: https://aistudio.google.com/app/apikey")
        print("2. Set environment variable:")
        print("   export GEMINI_API_KEY='your-api-key-here'")
        print("3. Run this script again")
        return

    pdf_path = "248-tiruveumbur-page 25.pdf"

    try:
        # Create extractor
        extractor = GeminiExtractor(pdf_path, api_key)

        print(f"PDF: {pdf_path}")
        print(f"Total pages: {extractor.num_pages}")
        print("\n" + "="*60)

        # Extract metadata
        metadata = extractor.extract_metadata(page_number=1)
        print("\nMetadata:")
        print(json.dumps(metadata, indent=2, ensure_ascii=False))

        # Extract voters using STREAMING (low memory)
        print("\n" + "="*60)
        print("Extracting voters (streaming mode - low memory)...")

        output_csv = pdf_path.replace('.pdf', '_gemini.csv')
        total_voters = extractor.extract_all_pages_streaming(output_csv, start_page=2)

        print(f"\n✓ Extracted {total_voters} voters")

        print("\n" + "="*60)
        print(f"Success! Output: {output_csv}")
        print("="*60)

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
