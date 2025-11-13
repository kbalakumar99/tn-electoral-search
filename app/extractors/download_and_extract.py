#!/usr/bin/env python3
"""
Download PDFs from URLs and extract content
Useful for downloading and processing PDFs from web sources
"""

import os
import argparse
from pathlib import Path
from typing import List
import urllib.request
from urllib.parse import urlparse
from pdf_extractor import PDFExtractor


class PDFDownloader:
    """Downloads and processes PDFs from URLs"""

    def __init__(self, download_dir: str = "downloaded_pdfs", output_dir: str = "extracted_data"):
        """
        Initialize PDF downloader

        Args:
            download_dir: Directory to save downloaded PDFs
            output_dir: Directory for extracted data
        """
        self.download_dir = Path(download_dir)
        self.output_dir = Path(output_dir)

        # Create directories
        self.download_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

    def download_pdf(self, url: str, filename: str = None) -> Path:
        """
        Download a PDF from URL

        Args:
            url: URL of the PDF
            filename: Custom filename (optional, will use URL filename if not provided)

        Returns:
            Path to downloaded PDF
        """
        # Generate filename if not provided
        if filename is None:
            parsed_url = urlparse(url)
            filename = Path(parsed_url.path).name

            # If no filename in URL, generate one
            if not filename or not filename.endswith('.pdf'):
                filename = f"document_{hash(url) % 10000}.pdf"

        # Full path for downloaded file
        file_path = self.download_dir / filename

        print(f"Downloading: {url}")
        print(f"Saving to: {file_path}")

        try:
            # Download the file
            urllib.request.urlretrieve(url, file_path)
            print(f"✓ Downloaded successfully ({file_path.stat().st_size / 1024:.1f} KB)")
            return file_path

        except Exception as e:
            print(f"✗ Error downloading: {e}")
            return None

    def download_and_extract(self, url: str, filename: str = None, language: str = 'eng+tam') -> dict:
        """
        Download PDF and extract content in one step

        Args:
            url: URL of the PDF
            filename: Custom filename
            language: OCR language

        Returns:
            Dictionary with results
        """
        # Download
        pdf_path = self.download_pdf(url, filename)

        if pdf_path is None:
            return {'status': 'failed', 'reason': 'download_failed'}

        # Extract
        try:
            print(f"\nExtracting content from {pdf_path.name}...")
            extractor = PDFExtractor(str(pdf_path), language=language)

            # Extract all data
            data = extractor.extract_all()

            # Save outputs
            json_output = self.output_dir / f"{pdf_path.stem}_extracted.json"
            csv_output = self.output_dir / f"{pdf_path.stem}_extracted.csv"

            extractor.save_to_json(str(json_output), data)
            extractor.save_to_csv(str(csv_output), data)

            return {
                'status': 'success',
                'url': url,
                'pdf_path': str(pdf_path),
                'json_output': str(json_output),
                'csv_output': str(csv_output),
                'pages_extracted': len(data['data_pages'])
            }

        except Exception as e:
            print(f"✗ Error extracting: {e}")
            return {
                'status': 'failed',
                'reason': 'extraction_failed',
                'error': str(e)
            }

    def process_url_list(self, url_file: str, language: str = 'eng+tam') -> List[dict]:
        """
        Process multiple PDFs from a text file containing URLs

        Args:
            url_file: Path to text file with one URL per line
            language: OCR language

        Returns:
            List of result dictionaries
        """
        # Read URLs
        with open(url_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]

        print(f"Found {len(urls)} URLs to process\n")
        print("=" * 70)

        results = []
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Processing: {url}")
            print("-" * 70)

            result = self.download_and_extract(url, language=language)
            results.append(result)

            print("-" * 70)

        # Summary
        successful = sum(1 for r in results if r['status'] == 'success')
        failed = len(results) - successful

        print(f"\n{'=' * 70}")
        print(f"Processing Complete!")
        print(f"{'=' * 70}")
        print(f"Total: {len(results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"\nDownloaded PDFs: {self.download_dir}")
        print(f"Extracted data: {self.output_dir}")
        print(f"{'=' * 70}")

        return results


def main():
    """Main function with CLI"""
    parser = argparse.ArgumentParser(
        description="Download PDFs from URLs and extract content using OCR"
    )

    parser.add_argument(
        "input",
        help="URL of a single PDF or path to text file with multiple URLs"
    )
    parser.add_argument(
        "-l", "--language",
        default="eng+tam",
        help="OCR language (default: eng+tam)"
    )
    parser.add_argument(
        "-d", "--download-dir",
        default="downloaded_pdfs",
        help="Directory for downloaded PDFs (default: downloaded_pdfs)"
    )
    parser.add_argument(
        "-o", "--output-dir",
        default="extracted_data",
        help="Directory for extracted data (default: extracted_data)"
    )
    parser.add_argument(
        "-n", "--name",
        help="Custom filename for downloaded PDF (single URL only)"
    )

    args = parser.parse_args()

    # Create downloader
    downloader = PDFDownloader(args.download_dir, args.output_dir)

    # Check if input is a file or URL
    if os.path.isfile(args.input):
        # Process multiple URLs from file
        print(f"Processing URLs from file: {args.input}")
        downloader.process_url_list(args.input, args.language)
    else:
        # Process single URL
        print(f"Processing single URL: {args.input}")
        result = downloader.download_and_extract(args.input, args.name, args.language)

        if result['status'] == 'success':
            print(f"\n✓ Success!")
            print(f"  PDF: {result['pdf_path']}")
            print(f"  JSON: {result['json_output']}")
            print(f"  CSV: {result['csv_output']}")
            print(f"  Pages: {result['pages_extracted']}")
        else:
            print(f"\n✗ Failed: {result.get('reason', 'unknown')}")


if __name__ == "__main__":
    main()
