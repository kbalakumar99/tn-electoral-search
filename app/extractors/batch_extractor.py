#!/usr/bin/env python3
"""
Batch PDF Extractor
Processes multiple PDFs and extracts content using OCR
"""

import os
import argparse
from pathlib import Path
from typing import List
import pandas as pd
from .pdf_extractor import PDFExtractor


class BatchPDFExtractor:
    """Handles batch processing of multiple PDFs"""

    def __init__(self, input_dir: str, output_dir: str = None):
        """
        Initialize batch extractor

        Args:
            input_dir: Directory containing PDF files
            output_dir: Directory for output files (default: same as input_dir)
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir) if output_dir else self.input_dir

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def find_pdfs(self) -> List[Path]:
        """Find all PDF files in the input directory"""
        pdf_files = list(self.input_dir.glob("*.pdf"))
        return sorted(pdf_files)

    def process_single_pdf(self, pdf_path: Path) -> dict:
        """
        Process a single PDF file

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with extraction results
        """
        print(f"\nProcessing: {pdf_path.name}")
        print("-" * 60)

        try:
            # Create extractor
            extractor = PDFExtractor(str(pdf_path))

            # Extract data
            data = extractor.extract_all()

            # Generate output file names
            base_name = pdf_path.stem
            json_output = self.output_dir / f"{base_name}_extracted.json"
            csv_output = self.output_dir / f"{base_name}_extracted.csv"

            # Save outputs
            extractor.save_to_json(str(json_output), data)
            extractor.save_to_csv(str(csv_output), data)

            return {
                'pdf_name': pdf_path.name,
                'status': 'success',
                'pages_extracted': len(data['data_pages']),
                'json_output': str(json_output),
                'csv_output': str(csv_output)
            }

        except Exception as e:
            print(f"Error processing {pdf_path.name}: {e}")
            return {
                'pdf_name': pdf_path.name,
                'status': 'failed',
                'error': str(e)
            }

    def process_all(self) -> pd.DataFrame:
        """
        Process all PDFs in the input directory

        Returns:
            DataFrame with processing results
        """
        pdf_files = self.find_pdfs()

        if not pdf_files:
            print(f"No PDF files found in {self.input_dir}")
            return pd.DataFrame()

        print(f"Found {len(pdf_files)} PDF files to process")
        print("=" * 60)

        results = []
        for pdf_path in pdf_files:
            result = self.process_single_pdf(pdf_path)
            results.append(result)

        # Create summary DataFrame
        summary_df = pd.DataFrame(results)

        # Save summary
        summary_path = self.output_dir / "extraction_summary.csv"
        summary_df.to_csv(summary_path, index=False)
        print(f"\n{'=' * 60}")
        print(f"Processing complete!")
        print(f"Summary saved to: {summary_path}")
        print(f"{'=' * 60}")

        return summary_df

    def merge_all_data(self, output_file: str = "merged_data.csv"):
        """
        Merge all extracted CSV files into a single database-ready file

        Args:
            output_file: Name of the merged output file
        """
        csv_files = list(self.output_dir.glob("*_extracted.csv"))

        if not csv_files:
            print("No extracted CSV files found to merge")
            return

        print(f"\nMerging {len(csv_files)} CSV files...")

        all_data = []
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                all_data.append(df)
            except Exception as e:
                print(f"Error reading {csv_file}: {e}")

        if all_data:
            merged_df = pd.concat(all_data, ignore_index=True)
            output_path = self.output_dir / output_file
            merged_df.to_csv(output_path, index=False, encoding='utf-8')
            print(f"Merged data saved to: {output_path}")
            print(f"Total records: {len(merged_df)}")
        else:
            print("No data to merge")


def main():
    """Main function with CLI interface"""
    parser = argparse.ArgumentParser(
        description="Batch PDF OCR Extractor - Process multiple PDFs with OCR"
    )
    parser.add_argument(
        "input_dir",
        help="Directory containing PDF files"
    )
    parser.add_argument(
        "-o", "--output-dir",
        help="Output directory (default: same as input directory)",
        default=None
    )
    parser.add_argument(
        "-m", "--merge",
        action="store_true",
        help="Merge all extracted data into a single CSV file"
    )

    args = parser.parse_args()

    # Create batch extractor
    batch_extractor = BatchPDFExtractor(args.input_dir, args.output_dir)

    # Process all PDFs
    summary = batch_extractor.process_all()

    # Display summary
    if not summary.empty:
        print("\nProcessing Summary:")
        print(summary.to_string(index=False))

        # Merge data if requested
        if args.merge:
            batch_extractor.merge_all_data()


if __name__ == "__main__":
    main()
