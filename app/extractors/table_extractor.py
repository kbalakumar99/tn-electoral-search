#!/usr/bin/env python3
"""
Table-based PDF Extractor for Voter Lists
Uses column detection to accurately extract tabular data from voter list PDFs
"""

import os
import re
import csv
from datetime import datetime
from typing import Dict, List, Any
import pytesseract
from pdf2image import convert_from_path
import pandas as pd
import fitz
from pytesseract import Output
from PIL import Image

# Increase PIL's image size limit for large PDF pages
Image.MAX_IMAGE_PIXELS = 500000000


class TableExtractor:
    """Extracts tabular data using column-based detection"""

    def __init__(self, pdf_path: str, language: str = 'eng+tam'):
        self.pdf_path = pdf_path
        self.pdf_name = os.path.basename(pdf_path)
        self.language = language
        self.num_pages = self._get_page_count()

    def _get_page_count(self) -> int:
        """Get total number of pages"""
        try:
            doc = fitz.open(self.pdf_path)
            count = len(doc)
            doc.close()
            return count
        except Exception as e:
            print(f"Error: {e}")
            return 0

    def extract_page_with_layout(self, page_number: int, dpi: int = 300) -> pd.DataFrame:
        """
        Extract data from a page using layout analysis

        Args:
            page_number: Page to extract
            dpi: Image resolution

        Returns:
            DataFrame with extracted rows
        """
        print(f"Extracting page {page_number}...")

        # Convert page to image
        images = convert_from_path(
            self.pdf_path,
            dpi=dpi,
            first_page=page_number,
            last_page=page_number
        )

        if not images:
            return pd.DataFrame()

        # Get OCR data with positions
        ocr_data = pytesseract.image_to_data(
            images[0],
            lang=self.language,
            output_type=Output.DICT
        )

        # Group words by line and column position
        rows = self._group_by_table_structure(ocr_data)

        # Convert to DataFrame
        df = pd.DataFrame(rows)

        return df

    def _group_by_table_structure(self, ocr_data: dict) -> List[Dict]:
        """
        Group OCR words into table rows based on spatial layout

        Expected columns (left to right):
        1. Serial No (வரிசை எண்) - leftmost
        2. Division/House info - next column
        3. Voter Name (வாக்காளரின் பெயர்) - main name column
        4. Relationship Code (உறவு முறை) - symbols
        5. Relative Name (உறவினர் பெயர்) - relative's name
        6. Age/Gender - numbers
        7. Voter ID (வாக்காளர் அடையாள அட்டை எண்) - rightmost, format TN27/168/xxxxx
        """
        # Filter valid words
        words = []
        for i in range(len(ocr_data['text'])):
            text = ocr_data['text'][i].strip()
            conf = int(ocr_data['conf'][i])

            if text and conf > 30:  # Filter low confidence
                words.append({
                    'text': text,
                    'left': ocr_data['left'][i],
                    'top': ocr_data['top'][i],
                    'width': ocr_data['width'][i],
                    'height': ocr_data['height'][i],
                    'line_num': ocr_data['line_num'][i],
                    'conf': conf
                })

        # Group words by horizontal lines (same Y position, within tolerance)
        lines = {}
        y_tolerance = 15  # pixels tolerance for same line

        for word in words:
            # Find existing line at same Y position
            found_line = False
            for y_pos in lines:
                if abs(word['top'] - y_pos) < y_tolerance:
                    lines[y_pos].append(word)
                    found_line = True
                    break

            if not found_line:
                lines[word['top']] = [word]

        # Sort words in each line by X position
        for y_pos in lines:
            lines[y_pos].sort(key=lambda w: w['left'])

        # Determine column boundaries by analyzing X positions across all lines
        all_x_positions = []
        for line in lines.values():
            for word in line:
                all_x_positions.append(word['left'])

        # Define approximate column boundaries (these may need adjustment)
        # Based on typical voter list layout
        columns = {
            'serial_no': (0, 150),      # Serial number column
            'division_house': (150, 400),  # Division/House info
            'voter_name': (400, 800),   # Voter name
            'relationship': (800, 1000), # Relationship code
            'relative_name': (1000, 1400), # Relative's name
            'age_gender': (1400, 1700),  # Age and gender
            'voter_id': (1700, 2500)    # Voter ID
        }

        # Extract rows
        rows = []
        voter_id_pattern = re.compile(r'TN\d+/\d+/\d+')

        for y_pos in sorted(lines.keys()):
            line_words = lines[y_pos]

            # Check if this line contains a voter ID (indicates a complete row)
            line_text = ' '.join([w['text'] for w in line_words])

            # Skip header and footer lines
            if any(skip in line_text for skip in ['வாக்காளரின்', 'TYPE', 'பக்கம்', 'of 29', 'சட்டமன்ற', 'பாகம்']):
                continue

            # Collect words into columns
            row_data = {
                'serial_no': '',
                'division_no': '',
                'house_no': '',
                'voter_name': '',
                'relationship_code': '',
                'relative_name': '',
                'age': '',
                'gender_caste_code': '',
                'voter_id': ''
            }

            for word in line_words:
                x = word['left']
                text = word['text']

                # Categorize word by column position
                if columns['serial_no'][0] <= x < columns['serial_no'][1]:
                    if text.isdigit() and len(text) <= 3:
                        row_data['serial_no'] = text

                elif columns['voter_name'][0] <= x < columns['voter_name'][1]:
                    if re.search(r'[அ-ஹ]', text):  # Tamil text
                        row_data['voter_name'] += ' ' + text if row_data['voter_name'] else text

                elif columns['relative_name'][0] <= x < columns['relative_name'][1]:
                    if re.search(r'[அ-ஹ]', text):  # Tamil text
                        row_data['relative_name'] += ' ' + text if row_data['relative_name'] else text

                elif columns['age_gender'][0] <= x < columns['age_gender'][1]:
                    if text.isdigit() and 10 <= int(text) <= 120:  # Age range
                        row_data['age'] = text

                elif columns['voter_id'][0] <= x < columns['voter_id'][1]:
                    if voter_id_pattern.match(text):
                        row_data['voter_id'] = text

            # Only add row if it has essential data (at least voter name or voter ID)
            if row_data['voter_name'] or row_data['voter_id']:
                rows.append(row_data)

        return rows

    def save_to_csv(self, output_path: str, df: pd.DataFrame):
        """
        Save DataFrame to CSV with proper headers

        Args:
            output_path: Output CSV file path
            df: DataFrame with voter data
        """
        # Define column mapping with Tamil headers
        headers = {
            'serial_no': 'Serial Number (வரிசை எண்)',
            'division_no': 'Division No (பிரிவு எண்)',
            'house_no': 'House No (வீட்டு எண்)',
            'voter_name': 'Voter Name (வாக்காளரின் பெயர்)',
            'relationship_code': 'Relationship Code (உறவு முறை)',
            'relative_name': 'Relative Name (உறவினர் பெயர்)',
            'age': 'Age (வயது)',
            'gender_caste_code': 'Gender/Caste Code (இனம்)',
            'voter_id': 'Voter ID No (வாக்காளர் அடையாள அட்டை எண்)'
        }

        # Rename columns
        df_export = df.rename(columns=headers)

        # Save to CSV
        df_export.to_csv(output_path, index=False, encoding='utf-8')
        print(f"✓ Saved {len(df)} records to {output_path}")


def main():
    """Test the table extractor"""
    pdf_path = "248-tiruveumbur-page 25.pdf"

    extractor = TableExtractor(pdf_path)

    print(f"PDF: {pdf_path}")
    print(f"Total pages: {extractor.num_pages}")
    print("\nExtracting page 2 (sample)...")

    # Extract only page 2 as a test
    df = extractor.extract_page_with_layout(2)

    print(f"\nExtracted {len(df)} rows")
    print("\nSample data:")
    print(df.head(10))

    # Save to CSV
    output_csv = pdf_path.replace('.pdf', '_table_test.csv')
    extractor.save_to_csv(output_csv, df)

    print(f"\n{'='*60}")
    print(f"Test extraction complete!")
    print(f"Review the output: {output_csv}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
