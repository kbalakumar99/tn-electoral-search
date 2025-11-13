#!/usr/bin/env python3
"""
Simple Line-by-Line Parser for Voter Lists
Extracts each voter as a separate row using pattern matching
"""

import os
import re
import csv
from datetime import datetime
import pytesseract
from pdf2image import convert_from_path
import pandas as pd
import fitz
from PIL import Image

# Increase PIL's image size limit for large PDF pages
Image.MAX_IMAGE_PIXELS = 500000000


class SimpleVoterParser:
    """Simple parser that processes text line by line"""

    def __init__(self, pdf_path: str, language: str = 'eng+tam'):
        self.pdf_path = pdf_path
        self.pdf_name = os.path.basename(pdf_path)
        self.language = language
        self.num_pages = self._get_page_count()

    def _get_page_count(self) -> int:
        """Get total pages"""
        try:
            doc = fitz.open(self.pdf_path)
            count = len(doc)
            doc.close()
            return count
        except:
            return 0

    def extract_metadata(self, page_num: int = 1, dpi: int = 300) -> dict:
        """Extract metadata from first page"""
        images = convert_from_path(self.pdf_path, dpi=dpi, first_page=page_num, last_page=page_num)
        text = pytesseract.image_to_string(images[0], lang=self.language)

        metadata = {}

        # Extract Assembly Constituency Number
        ac_match = re.search(r'தொகுதியின்\s*எண்[:：]?\s*(\d+)', text)
        if ac_match:
            metadata['assembly_constituency_no'] = ac_match.group(1)

        # Extract Part Number
        part_match = re.search(r'பாகம்\s*எண்\s*[:：]?\s*(\d+)', text)
        if part_match:
            metadata['part_no'] = part_match.group(1)

        return metadata

    def extract_voters_from_page(self, page_num: int, dpi: int = 300) -> list:
        """
        Extract voters from a page - one voter per line/row

        Strategy:
        - Extract all text
        - Each voter name in Tamil becomes one row
        - Link it with corresponding relative name and other fields
        """
        print(f"Processing page {page_num}...")

        # Convert page to image and extract text
        images = convert_from_path(self.pdf_path, dpi=dpi, first_page=page_num, last_page=page_num)
        text = pytesseract.image_to_string(images[0], lang=self.language)

        lines = text.split('\n')

        voters = []
        voter_id_pattern = re.compile(r'(TN\d+/\d+/\d+)')
        tamil_name_pattern = re.compile(r'[அ-ஹ][அ-ஹா-ூெ-ௌ்]+')

        # Skip header lines
        data_started = False
        buffer = []  # Collect lines for processing

        for line in lines:
            line = line.strip()

            if not line:
                continue

            # Skip headers
            if any(skip in line for skip in ['வாக்காளரின்', 'TYPE', 'பக்கம்', 'of 29', 'சட்டமன்ற', 'பாகம்', 'உறவினர்', 'இனம்', 'அட்டை']):
                data_started = False
                continue

            # Start collecting data after headers
            if re.search(r'[அ-ஹ]', line) and not data_started:
                data_started = True

            if data_started:
                buffer.append(line)

        # Process buffer to extract voters
        # Each Tamil name should become a voter record
        serial_no = 1

        for i, line in enumerate(buffer):
            # Check if line contains a Tamil name (potential voter)
            if tamil_name_pattern.search(line):
                # This line might contain voter name

                # Look ahead for related data (relative name, age, voter ID)
                relative_name = ''
                age = ''
                voter_id = ''

                # Check current and next few lines for voter ID
                for j in range(i, min(i + 3, len(buffer))):
                    check_line = buffer[j]

                    # Look for voter ID
                    voter_id_match = voter_id_pattern.search(check_line)
                    if voter_id_match:
                        voter_id = voter_id_match.group(1)

                    # Look for age (2 digit number)
                    age_match = re.search(r'\b(\d{2})\b', check_line)
                    if age_match and not age:
                        potential_age = int(age_match.group(1))
                        if 18 <= potential_age <= 120:
                            age = age_match.group(1)

                # Look for relative name (next Tamil text line)
                if i + 1 < len(buffer):
                    next_line = buffer[i + 1]
                    if tamil_name_pattern.search(next_line):
                        # Check if it's not a voter ID line
                        if not voter_id_pattern.search(next_line):
                            relative_name = tamil_name_pattern.search(next_line).group(0)

                # Create voter record
                voter = {
                    'serial_no': serial_no,
                    'division_no': '',
                    'house_no': '',
                    'voter_name': line,
                    'relationship_code': '',
                    'relative_name': relative_name,
                    'age': age,
                    'gender_caste_code': '',
                    'voter_id': voter_id
                }

                voters.append(voter)
                serial_no += 1

        return voters

    def extract_all_pages(self, start_page: int = 2) -> list:
        """Extract voters from all data pages"""
        all_voters = []

        for page_num in range(start_page, self.num_pages + 1):
            voters = self.extract_voters_from_page(page_num)
            all_voters.extend(voters)

        return all_voters

    def save_to_csv(self, voters: list, output_path: str):
        """Save voters to CSV"""
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
    """Test the parser"""
    pdf_path = "248-tiruveumbur-page 25.pdf"

    parser = SimpleVoterParser(pdf_path)

    print(f"Extracting voters from: {pdf_path}")
    print(f"Total pages: {parser.num_pages}\n")

    # Extract metadata
    metadata = parser.extract_metadata()
    print(f"Metadata: {metadata}\n")

    # Extract voters from page 2 only (test)
    voters = parser.extract_voters_from_page(2)

    print(f"\nExtracted {len(voters)} voter records")
    print("\nSample voters:")
    for i, voter in enumerate(voters[:5]):
        print(f"{i+1}. {voter}")

    # Save to CSV
    output_csv = pdf_path.replace('.pdf', '_simple_parse.csv')
    parser.save_to_csv(voters, output_csv)

    print(f"\n{'='*60}")
    print(f"Done! Check: {output_csv}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
