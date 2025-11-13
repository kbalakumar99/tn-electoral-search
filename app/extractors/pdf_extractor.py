#!/usr/bin/env python3
"""
PDF OCR Content Extractor
Extracts text from scanned PDFs using OCR and structures it for database storage.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import pandas as pd
import fitz  # PyMuPDF

# Increase PIL's image size limit for large PDF pages
Image.MAX_IMAGE_PIXELS = 500000000


class PDFExtractor:
    """Handles OCR extraction from scanned PDFs"""

    def __init__(self, pdf_path: str, language: str = 'eng+tam'):
        """
        Initialize the PDF extractor

        Args:
            pdf_path: Path to the PDF file
            language: OCR language(s) to use (default: 'eng+tam' for English and Tamil)
                     Common options: 'eng', 'tam', 'eng+tam', 'hin', 'san', etc.
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

    def extract_text_from_page(self, page_number: int, dpi: int = 300) -> str:
        """
        Extract text from a specific page using OCR

        Args:
            page_number: Page number to extract (1-indexed)
            dpi: DPI for image conversion (higher = better quality but slower)

        Returns:
            Extracted text as string
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
                return ""

            # Perform OCR on the image with specified language
            text = pytesseract.image_to_string(images[0], lang=self.language)
            return text.strip()

        except Exception as e:
            print(f"Error extracting text from page {page_number}: {e}")
            return ""

    def extract_metadata_page(self, page_number: int = 1) -> Dict[str, Any]:
        """
        Extract metadata from the first page
        This should be customized based on the actual structure of your PDFs

        Args:
            page_number: Page number containing metadata (default: 1)

        Returns:
            Dictionary containing metadata fields
        """
        text = self.extract_text_from_page(page_number)

        # Parse metadata - customize this based on your PDF structure
        metadata = {
            'pdf_name': self.pdf_name,
            'extraction_date': datetime.now().isoformat(),
            'total_pages': self.num_pages,
            'metadata_raw_text': text,
            'metadata_page': page_number
        }

        # You can add custom parsing logic here to extract specific fields
        # For example:
        # - Document ID
        # - Date
        # - Location
        # - Category
        # etc.

        return metadata

    def extract_data_pages(self, start_page: int = 2, end_page: int = None) -> List[Dict[str, Any]]:
        """
        Extract data from all data pages (pages after metadata)

        Args:
            start_page: First data page (default: 2)
            end_page: Last page to extract (default: all remaining pages)

        Returns:
            List of dictionaries, one per page
        """
        if end_page is None:
            end_page = self.num_pages

        data_pages = []

        for page_num in range(start_page, end_page + 1):
            print(f"Processing page {page_num}/{self.num_pages}...")

            text = self.extract_text_from_page(page_num)

            page_data = {
                'page_number': page_num,
                'pdf_name': self.pdf_name,
                'raw_text': text,
                'extraction_date': datetime.now().isoformat()
            }

            data_pages.append(page_data)

        return data_pages

    def extract_all(self) -> Dict[str, Any]:
        """
        Extract all content from the PDF: metadata + data pages

        Returns:
            Dictionary containing metadata and data pages
        """
        print(f"Extracting from {self.pdf_name} ({self.num_pages} pages)...")

        # Extract metadata from first page
        metadata = self.extract_metadata_page(page_number=1)

        # Extract data from remaining pages
        data_pages = []
        if self.num_pages > 1:
            data_pages = self.extract_data_pages(start_page=2)

        return {
            'metadata': metadata,
            'data_pages': data_pages
        }

    def save_to_json(self, output_path: str, data: Dict[str, Any] = None):
        """
        Save extracted data to JSON file

        Args:
            output_path: Path to output JSON file
            data: Data to save (if None, extracts all data first)
        """
        if data is None:
            data = self.extract_all()

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"Data saved to {output_path}")

    def to_dataframe(self, data: Dict[str, Any] = None) -> pd.DataFrame:
        """
        Convert extracted data to a pandas DataFrame for database insertion

        Args:
            data: Extracted data (if None, extracts all data first)

        Returns:
            DataFrame with flattened structure
        """
        if data is None:
            data = self.extract_all()

        # Flatten the structure for database
        rows = []
        metadata = data['metadata']

        for page_data in data['data_pages']:
            row = {
                # Metadata fields
                'pdf_name': metadata['pdf_name'],
                'total_pages': metadata['total_pages'],
                'metadata_raw_text': metadata['metadata_raw_text'],
                'extraction_date': metadata['extraction_date'],

                # Page-specific fields
                'page_number': page_data['page_number'],
                'page_text': page_data['raw_text']
            }
            rows.append(row)

        return pd.DataFrame(rows)

    def save_to_csv(self, output_path: str, data: Dict[str, Any] = None):
        """
        Save extracted data to CSV file

        Args:
            output_path: Path to output CSV file
            data: Data to save (if None, extracts all data first)
        """
        df = self.to_dataframe(data)
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"Data saved to {output_path}")


def main():
    """Main function for testing"""
    # Example usage
    pdf_path = "248-tiruveumbur-page 25.pdf"

    # Create extractor instance
    extractor = PDFExtractor(pdf_path)

    # Extract all data
    data = extractor.extract_all()

    # Save to JSON
    output_json = pdf_path.replace('.pdf', '_extracted.json')
    extractor.save_to_json(output_json, data)

    # Save to CSV (database-ready format)
    output_csv = pdf_path.replace('.pdf', '_extracted.csv')
    extractor.save_to_csv(output_csv, data)

    # Display summary
    print(f"\n{'='*60}")
    print(f"Extraction Summary:")
    print(f"{'='*60}")
    print(f"PDF: {pdf_path}")
    print(f"Total Pages: {extractor.num_pages}")
    print(f"Metadata Pages: 1")
    print(f"Data Pages: {len(data['data_pages'])}")
    print(f"Output Files:")
    print(f"  - JSON: {output_json}")
    print(f"  - CSV: {output_csv}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
