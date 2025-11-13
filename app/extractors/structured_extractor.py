#!/usr/bin/env python3
"""
Structured PDF Extractor for Voter Lists
Extracts tabular data from Tamil voter list PDFs and creates database-ready CSV
"""

import os
import re
import csv
from datetime import datetime
from typing import Dict, List, Any, Tuple
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import pandas as pd
import fitz  # PyMuPDF
from pytesseract import Output

# Increase PIL's image size limit for large PDF pages
Image.MAX_IMAGE_PIXELS = 500000000


class VoterListExtractor:
    """Extracts voter list data in structured tabular format"""

    def __init__(self, pdf_path: str, language: str = 'eng+tam'):
        """
        Initialize the voter list extractor

        Args:
            pdf_path: Path to the PDF file
            language: OCR language(s) to use (default: 'eng+tam')
        """
        self.pdf_path = pdf_path
        self.pdf_name = os.path.basename(pdf_path)
        self.language = language
        self.num_pages = self._get_page_count()

    def _get_page_count(self) -> int:
        """Get the total number of pages in the PDF"""
        try:
            doc = fitz.open(self.pdf_path)
            count = len(doc)
            doc.close()
            return count
        except Exception as e:
            print(f"Error getting page count: {e}")
            return 0

    def extract_metadata_page(self, page_number: int = 1, dpi: int = 300) -> Dict[str, Any]:
        """
        Extract metadata from the first page

        Args:
            page_number: Page number containing metadata (default: 1)
            dpi: DPI for image conversion

        Returns:
            Dictionary containing metadata fields
        """
        try:
            # Convert PDF page to image
            images = convert_from_path(
                self.pdf_path,
                dpi=dpi,
                first_page=page_number,
                last_page=page_number
            )

            if not images:
                return {}

            # Perform OCR
            text = pytesseract.image_to_string(images[0], lang=self.language)

            # Parse metadata fields
            metadata = {
                'pdf_name': self.pdf_name,
                'extraction_date': datetime.now().isoformat(),
                'total_pages': self.num_pages,
                'raw_metadata_text': text.strip()
            }

            # Extract specific fields using regex patterns
            # Assembly Constituency Number (சட்டமன்ற தொகுதியின் எண்)
            ac_match = re.search(r'தொகுதியின்\s*எண்[:：]?\s*(\d+)', text)
            if ac_match:
                metadata['assembly_constituency_no'] = ac_match.group(1)

            # Part Number (பாகம் எண்)
            part_match = re.search(r'பாகம்\s*எண்\s*[:：]?\s*(\d+)', text)
            if part_match:
                metadata['part_no'] = part_match.group(1)

            # Year (ஆண்டு)
            year_match = re.search(r'(\d{4})', text)
            if year_match:
                metadata['year'] = year_match.group(1)

            # Qualifying Date (தகுதியேற்படுத்தும் நாள்)
            date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
            if date_match:
                metadata['qualifying_date'] = date_match.group(1)

            return metadata

        except Exception as e:
            print(f"Error extracting metadata: {e}")
            return {}

    def extract_data_page_structured(self, page_number: int, dpi: int = 300) -> List[Dict[str, Any]]:
        """
        Extract structured voter data from a data page using position-based parsing

        Args:
            page_number: Page number to extract
            dpi: DPI for image conversion

        Returns:
            List of voter records
        """
        try:
            # Convert PDF page to image
            images = convert_from_path(
                self.pdf_path,
                dpi=dpi,
                first_page=page_number,
                last_page=page_number
            )

            if not images:
                return []

            # Get OCR data with bounding boxes
            ocr_data = pytesseract.image_to_data(
                images[0],
                lang=self.language,
                output_type=Output.DICT
            )

            # Parse the OCR data into structured rows
            voters = self._parse_table_from_ocr(ocr_data, page_number)

            return voters

        except Exception as e:
            print(f"Error extracting page {page_number}: {e}")
            return []

    def _parse_table_from_ocr(self, ocr_data: dict, page_number: int) -> List[Dict[str, Any]]:
        """
        Parse OCR data into table rows based on spatial layout

        Args:
            ocr_data: OCR data with bounding boxes from pytesseract
            page_number: Current page number

        Returns:
            List of voter records
        """
        # Group text by line number
        lines = {}
        for i, text in enumerate(ocr_data['text']):
            if text.strip() and int(ocr_data['conf'][i]) > 30:  # Filter low confidence
                line_num = ocr_data['line_num'][i]
                left = ocr_data['left'][i]

                if line_num not in lines:
                    lines[line_num] = []

                lines[line_num].append({
                    'text': text.strip(),
                    'left': left,
                    'top': ocr_data['top'][i],
                    'conf': ocr_data['conf'][i]
                })

        # Sort words in each line by horizontal position
        for line_num in lines:
            lines[line_num].sort(key=lambda x: x['left'])

        # Group lines into rows (voters)
        voters = []
        current_row = []

        for line_num in sorted(lines.keys()):
            line_data = lines[line_num]
            line_text = ' '.join([item['text'] for item in line_data])

            # Skip header lines and footer
            if any(keyword in line_text for keyword in ['வாக்காளரின்', 'உறவு', 'TYPE', 'பக்கம்', 'சட்டமன்ற', 'பாகம்']):
                continue

            current_row.append({
                'line_num': line_num,
                'text': line_text,
                'words': line_data
            })

        # Now extract voter records using a simpler line-by-line approach
        # Get all text content
        all_text = pytesseract.image_to_string(
            convert_from_path(self.pdf_path, dpi=300, first_page=page_number, last_page=page_number)[0],
            lang=self.language
        )

        voters = self._parse_voters_from_text(all_text, page_number)

        return voters

    def _parse_voters_from_text(self, text: str, page_number: int) -> List[Dict[str, Any]]:
        """
        Parse voter records from plain text using patterns

        Args:
            text: Extracted text from page
            page_number: Page number

        Returns:
            List of voter records
        """
        voters = []
        lines = text.split('\n')

        # Pattern to identify voter ID numbers
        voter_id_pattern = re.compile(r'TN\d+/\d+/\d+')

        # Skip until we find data (after headers)
        in_data_section = False
        current_voter = {}

        serial_no = 1

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Skip headers and metadata
            if any(keyword in line for keyword in ['வாக்காளரின்', 'TYPE', 'பக்கம்', 'சட்டமன்ற', 'பாகம்', 'of 29']):
                continue

            # Check if this line contains a voter ID (end of record)
            voter_id_match = voter_id_pattern.search(line)

            if voter_id_match:
                # Extract voter ID and any numbers before it
                voter_id = voter_id_match.group(0)

                # Try to extract age from the line before voter ID
                age_match = re.search(r'\b(\d{2})\b', line)
                age = age_match.group(1) if age_match else ''

                # Create voter record
                if current_voter.get('name'):
                    current_voter['voter_id'] = voter_id
                    current_voter['age'] = age
                    current_voter['serial_no'] = serial_no
                    voters.append(current_voter.copy())
                    serial_no += 1

                current_voter = {}

            # Check if line looks like a name (Tamil text, not numbers or codes)
            elif re.search(r'[அ-ஹ]', line) and not line.startswith('3') and 'TYPE' not in line:
                # This could be a voter name or relative name
                if not current_voter.get('name'):
                    current_voter['name'] = line
                elif not current_voter.get('relative_name'):
                    current_voter['relative_name'] = line

        return voters

    def extract_all_structured(self, metadata_page: int = 1, start_data_page: int = 2) -> Dict[str, Any]:
        """
        Extract all data in structured format

        Args:
            metadata_page: Page containing metadata
            start_data_page: First page with voter data

        Returns:
            Dictionary with metadata and voter records
        """
        print(f"Extracting structured data from {self.pdf_name}...")

        # Extract metadata
        metadata = self.extract_metadata_page(metadata_page)
        print(f"✓ Metadata extracted")

        # Extract voter data from all data pages
        all_voters = []
        for page_num in range(start_data_page, self.num_pages + 1):
            print(f"Processing page {page_num}/{self.num_pages}...")
            voters = self.extract_data_page_structured(page_num)

            # Add metadata to each voter record
            for voter in voters:
                voter.update({
                    'pdf_name': self.pdf_name,
                    'page_number': page_num,
                    'assembly_constituency_no': metadata.get('assembly_constituency_no', ''),
                    'part_no': metadata.get('part_no', ''),
                    'year': metadata.get('year', ''),
                    'extraction_date': datetime.now().isoformat()
                })

            all_voters.extend(voters)

        print(f"✓ Extracted {len(all_voters)} voter records")

        return {
            'metadata': metadata,
            'voters': all_voters
        }

    def save_to_csv(self, output_path: str, data: Dict[str, Any] = None):
        """
        Save voter data to CSV in the specified format

        Args:
            output_path: Path to output CSV file
            data: Extracted data (if None, extracts all first)
        """
        if data is None:
            data = self.extract_all_structured()

        voters = data['voters']

        if not voters:
            print("No voter data to save")
            return

        # Define CSV columns in the required order
        fieldnames = [
            'serial_no',
            'division_no',
            'house_no',
            'voter_name',
            'relationship_code',
            'relative_name',
            'age',
            'gender_caste_code',
            'voter_id'
        ]

        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # Write header with Tamil translations
            writer.writerow({
                'serial_no': 'Serial Number (வரிசை எண்)',
                'division_no': 'Division No (பிரிவு எண்)',
                'house_no': 'House No (வீட்டு எண்)',
                'voter_name': 'Voter Name (வாக்காளரின் பெயர்)',
                'relationship_code': 'Relationship Code (உறவு முறை)',
                'relative_name': 'Relative Name (உறவினர் பெயர்)',
                'age': 'Age (வயது)',
                'gender_caste_code': 'Gender/Caste Code (இனம்)',
                'voter_id': 'Voter ID No (வாக்காளர் அடையாள அட்டை எண்)'
            })

            # Write voter data
            for voter in voters:
                writer.writerow({
                    'serial_no': voter.get('serial_no', ''),
                    'division_no': voter.get('assembly_constituency_no', ''),
                    'house_no': '',  # To be extracted from detailed parsing
                    'voter_name': voter.get('name', ''),
                    'relationship_code': '',  # To be extracted from detailed parsing
                    'relative_name': voter.get('relative_name', ''),
                    'age': voter.get('age', ''),
                    'gender_caste_code': '',  # To be extracted from detailed parsing
                    'voter_id': voter.get('voter_id', '')
                })

        print(f"✓ Data saved to {output_path}")
        print(f"  Records: {len(voters)}")


def main():
    """Main function for testing"""
    pdf_path = "248-tiruveumbur-page 25.pdf"

    # Create extractor
    extractor = VoterListExtractor(pdf_path, language='eng+tam')

    # Extract structured data
    data = extractor.extract_all_structured()

    # Save to CSV
    output_csv = pdf_path.replace('.pdf', '_voters.csv')
    extractor.save_to_csv(output_csv, data)

    print(f"\n{'='*60}")
    print(f"Extraction Complete!")
    print(f"{'='*60}")
    print(f"Output: {output_csv}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
