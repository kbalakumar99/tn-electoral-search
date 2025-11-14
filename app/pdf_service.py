"""
PDF Import Service for electoral data
Handles PDF upload, metadata extraction, and Gemini-based voter extraction
"""
import os
import sys
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import csv
import logging
import pandas as pd

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from database import db

# Try to import PDF processing dependencies
try:
    from extractors.gemini_extractor import GeminiExtractor
    PDF_PROCESSING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"PDF processing dependencies not available: {e}")
    logger.info("Install with: pip install -r requirements-full.txt")
    PDF_PROCESSING_AVAILABLE = False
    GeminiExtractor = None


class PDFImportService:
    """Service for importing PDF electoral data"""
    
    def __init__(self):
        self.active_imports = {}  # Track active import jobs
        self._import_lock = asyncio.Lock()  # Lock to prevent concurrent imports
        
    async def get_pdf_info(self, pdf_path: str, gemini_api_key: str = None) -> Dict[str, Any]:
        """
        Get basic PDF information without AI extraction (faster)
        NO API KEY REQUIRED - just reads page count
        
        Args:
            pdf_path: Path to uploaded PDF file
            gemini_api_key: Not used here, for compatibility only
            
        Returns:
            Dictionary with basic PDF info
        """
        try:
            if not PDF_PROCESSING_AVAILABLE:
                return {
                    'success': False,
                    'error': 'PDF processing dependencies not installed. Install with: pip install -r requirements-full.txt',
                    'pdf_name': os.path.basename(pdf_path)
                }
            
            # Use PyMuPDF (fitz) to get page count - NO API KEY NEEDED
            import fitz  # PyMuPDF
            pdf_doc = fitz.open(pdf_path)
            num_pages = len(pdf_doc)
            pdf_doc.close()
            
            result = {
                'success': True,
                'pdf_name': os.path.basename(pdf_path),
                'total_pages': num_pages,
                'district': '',
                'constituency': '',
                'polling_station': '',
                'station_number': ''
            }
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'pdf_name': os.path.basename(pdf_path)
            }
    
    async def start_import(self, import_id: str, pdf_path: str, 
                          district: str, constituency: str, 
                          polling_station: str, station_number: str = None,
                          extraction_method: str = 'gemini', gemini_api_key: str = None) -> Dict[str, Any]:
        """
        Start importing PDF in background
        
        Args:
            import_id: Unique ID for this import job
            pdf_path: Path to PDF file
            district: District name
            constituency: Constituency name
            polling_station: Polling station name
            station_number: Station number
            extraction_method: 'gemini' or 'tesseract'
            
        Returns:
            Job status dictionary
        """
        # Initialize job status
        self.active_imports[import_id] = {
            'status': 'starting',
            'progress': 0,
            'total_pages': 0,
            'current_page': 0,
            'voters_extracted': 0,
            'error': None,
            'extraction_method': extraction_method,
            'started_at': datetime.now().isoformat()
        }
        
        # Start background task
        asyncio.create_task(
            self._run_import(import_id, pdf_path, district, constituency, 
                           polling_station, station_number, extraction_method, gemini_api_key)
        )
        
        return {
            'import_id': import_id,
            'status': 'started',
            'message': 'Import job started in background'
        }
    
    async def _run_import(self, import_id: str, pdf_path: str,
                         district: str, constituency: str,
                         polling_station: str, station_number: str = None,
                         extraction_method: str = 'gemini', gemini_api_key: str = None):
        """Background task to run the actual import"""
        try:
            if not PDF_PROCESSING_AVAILABLE:
                self.active_imports[import_id]['status'] = 'failed'
                self.active_imports[import_id]['error'] = 'PDF processing dependencies not installed. Install with: pip install -r requirements-full.txt'
                return
            
            if extraction_method == 'tesseract':
                # Use Tesseract OCR
                from extractors.simple_line_parser import SimpleVoterParser
                extractor = SimpleVoterParser(pdf_path, language='eng+tam')
            else:
                # Use Gemini AI (default)
                api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
                if not api_key:
                    raise ValueError("Gemini API key not provided. Please provide your API key.")
                from extractors.gemini_extractor import GeminiExtractor
                extractor = GeminiExtractor(pdf_path, api_key)
            
            # Update status
            self.active_imports[import_id]['total_pages'] = self._get_page_count(pdf_path)
            self.active_imports[import_id]['status'] = 'extracting'
            
            # Create temporary CSV file
            temp_csv = tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.csv', 
                delete=False,
                encoding='utf-8'
            )
            temp_csv_path = temp_csv.name
            
            # Extract data page by page with incremental import
            if extraction_method == 'tesseract':
                total_voters = await self._extract_with_tesseract(
                    import_id, extractor, temp_csv, 
                    start_page=2,
                    district=district,
                    constituency=constituency,
                    polling_station=polling_station,
                    station_number=station_number
                )
            else:
                total_voters = await self._extract_with_progress(
                    import_id, extractor, temp_csv, 
                    start_page=2,
                    district=district,
                    constituency=constituency,
                    polling_station=polling_station,
                    station_number=station_number
                )
            
            temp_csv.close()
            
            # FTS is automatically synced with contentless mode, just optimize
            self.active_imports[import_id]['status'] = 'optimizing_search'
            self.active_imports[import_id]['progress'] = 95
            
            # Only optimize, don't rebuild (prevents corruption)
            try:
                async with db.get_connection() as conn:
                    await conn.execute("INSERT INTO voters_fts(voters_fts) VALUES('optimize')")
                    await conn.commit()
                logger.info("✅ Search index optimized")
            except Exception as e:
                logger.warning(f"⚠️ Search optimization failed (non-critical): {e}")
                # Don't fail the import for optimization issues
            
            stats = {
                'csv_file': temp_csv_path,
                'district': district,
                'constituency': constituency,
                'polling_station': polling_station,
                'voters_imported': total_voters
            }
            
            # Cleanup temp file
            os.unlink(temp_csv_path)
            
            # Mark as complete
            self.active_imports[import_id]['status'] = 'completed'
            self.active_imports[import_id]['progress'] = 100
            self.active_imports[import_id]['completed_at'] = datetime.now().isoformat()
            self.active_imports[import_id]['stats'] = stats
            
        except Exception as e:
            self.active_imports[import_id]['status'] = 'failed'
            self.active_imports[import_id]['error'] = str(e)
            
            # Cleanup temp file if exists
            try:
                if 'temp_csv_path' in locals():
                    os.unlink(temp_csv_path)
            except:
                pass
    
    def _get_page_count(self, pdf_path: str) -> int:
        """Get total pages in PDF"""
        try:
            import fitz
            doc = fitz.open(pdf_path)
            count = len(doc)
            doc.close()
            return count
        except:
            return 0
    
    async def _extract_with_progress(self, import_id: str, extractor: GeminiExtractor,
                                     csv_file, start_page: int, 
                                     district: str, constituency: str, 
                                     polling_station: str, station_number: str = None) -> int:
        """Extract pages with progress updates and incremental import"""
        headers = [
            'Serial Number (வரிசை எண்)',
            'Division No (பிரிவு எண்)',
            'House No (வீட்டு எண்)',
            'Voter Name (வாக்காளரின் பெயர்)',
            'Relationship Code (உறவு முறை)',
            'Relative Name (உறவினர் பெயர்)',
            'Age (வயது)',
            'Gender/Caste Code (இனம்)',
            'Voter ID No (வாக்காளர் அடையாள அட்டை எண்)'
        ]
        
        writer = csv.writer(csv_file)
        writer.writerow(headers)
        
        total_voters = 0
        total_pages = extractor.num_pages - start_page + 1
        
        # Initialize importer once
        from importer import ElectoralDataImporter
        importer = ElectoralDataImporter()
        
        # Get or create district/constituency/polling station IDs once
        district_id = await importer._get_or_create_district(district)
        logger.info(f"📍 District: {district} (ID: {district_id})")
        
        constituency_id = await importer._get_or_create_constituency(district_id, constituency)
        logger.info(f"📍 Constituency: {constituency} (ID: {constituency_id})")
        
        polling_station_id = await importer._get_or_create_polling_station(
            constituency_id, polling_station, station_number
        )
        logger.info(f"📍 Polling Station: {polling_station} (ID: {polling_station_id}, Number: {station_number})")
        logger.info(f"🚀 Starting Gemini AI extraction of {total_pages} pages...")
        
        for page_num in range(start_page, extractor.num_pages + 1):
            # Update progress
            current_page = page_num - start_page + 1
            progress = int((current_page / total_pages) * 90)  # Reserve 10% for final indexing
            
            self.active_imports[import_id]['current_page'] = page_num
            self.active_imports[import_id]['progress'] = progress
            
            logger.info(f"📄 Processing page {page_num}/{extractor.num_pages} ({progress}%)")
            
            # Extract page
            csv_text = extractor.extract_page_as_csv(page_num, dpi=300)
            
            if not csv_text:
                logger.warning(f"   ⚠️  No CSV text extracted from page {page_num}")
                continue
            
            # Log extracted raw data
            logger.info(f"   📝 Extracted CSV data from page {page_num}:")
            logger.info(f"   {'-' * 80}")
            for i, line in enumerate(csv_text.strip().split('\n')[:5], 1):  # Log first 5 lines
                logger.info(f"   {i}. {line}")
            if len(csv_text.strip().split('\n')) > 5:
                logger.info(f"   ... ({len(csv_text.strip().split('\n')) - 5} more lines)")
            logger.info(f"   {'-' * 80}")
            
            # Parse and write rows, also import incrementally
            lines = csv_text.strip().split('\n')
            page_voters = []
            
            for line in lines:
                if not line.strip():
                    continue
                
                try:
                    parts = line.split(',')
                    if len(parts) >= 4:
                        row = [
                            parts[0].strip() if len(parts) > 0 else '',
                            parts[1].strip() if len(parts) > 1 else '',
                            parts[2].strip() if len(parts) > 2 else '',
                            parts[3].strip() if len(parts) > 3 else '',
                            parts[4].strip() if len(parts) > 4 else '',
                            parts[5].strip() if len(parts) > 5 else '',
                            parts[6].strip() if len(parts) > 6 else '',
                            parts[7].strip() if len(parts) > 7 else '',
                            parts[8].strip() if len(parts) > 8 else '',
                        ]
                        writer.writerow(row)
                        
                        # Prepare for database import - Create pandas Series
                        row_dict = {
                            'Serial Number (வரிசை எண்)': row[0],
                            'Division No (பிரிவு எண்)': row[1],
                            'House No (வீட்டு எண்)': row[2],
                            'Voter Name (வாக்காளரின் பெயர்)': row[3],
                            'Relationship Code (உறவு முறை)': row[4],
                            'Relative Name (உறவினர் பெயர்)': row[5],
                            'Age (வயது)': row[6],
                            'Gender/Caste Code (இனம்)': row[7],
                            'Voter ID No (வாக்காளர் அடையாள அட்டை எண்)': row[8]
                        }
                        voter_tuple = importer._parse_voter_row(
                            pd.Series(row_dict),
                            polling_station_id
                        )
                        if voter_tuple:
                            page_voters.append(voter_tuple)
                        total_voters += 1
                except Exception as e:
                    logger.warning(f"   ⚠️  Error parsing line: {line[:100]}... - Error: {e}")
                    continue
            
            # Import this page's voters to database immediately
            if page_voters:
                logger.info(f"   💾 Inserting {len(page_voters)} voters from page {page_num} into database...")
                
                # Log first few voters being inserted
                logger.info(f"   👥 Sample voters to insert (first 3):")
                for i, voter in enumerate(page_voters[:3], 1):
                    # voter tuple: (polling_station_id, serial_number, division_no, house_no,
                    #               voter_name, voter_name_tamil, relationship_code,
                    #               relative_name, relative_name_tamil, age, gender, caste_code, voter_id)
                    logger.info(f"      {i}. Serial: {voter[1]}, Name: {voter[4]}, Age: {voter[9]}, Voter ID: {voter[12]}")
                if len(page_voters) > 3:
                    logger.info(f"      ... ({len(page_voters) - 3} more voters)")
                
                try:
                    await importer._bulk_insert_voters(page_voters)
                    logger.info(f"   ✅ Successfully inserted {len(page_voters)} voters (polling_station_id={polling_station_id})")
                except Exception as e:
                    logger.error(f"   ❌ Failed to insert voters: {e}")
                    raise
            else:
                logger.warning(f"   ⚠️  No voters found on page {page_num}")
            
            self.active_imports[import_id]['voters_extracted'] = total_voters
            
            # Allow other tasks to run
            await asyncio.sleep(0)
        
        return total_voters
    
    async def _extract_with_tesseract(self, import_id: str, extractor,
                                      csv_file, start_page: int,
                                      district: str, constituency: str,
                                      polling_station: str, station_number: str = None) -> int:
        """Extract pages using Tesseract OCR with incremental import"""
        headers = [
            'Serial Number (வரிசை எண்)',
            'Division No (பிரிவு எண்)',
            'House No (வீட்டு எண்)',
            'Voter Name (வாக்காளரின் பெயர்)',
            'Relationship Code (உறவு முறை)',
            'Relative Name (உறவினர் பெயர்)',
            'Age (வயது)',
            'Gender/Caste Code (இனம்)',
            'Voter ID No (வாக்காளர் அடையாள அட்டை எண்)'
        ]
        
        writer = csv.writer(csv_file)
        writer.writerow(headers)
        
        total_voters = 0
        total_pages = self._get_page_count(extractor.pdf_path) - start_page + 1
        
        # Initialize importer once
        from importer import ElectoralDataImporter
        importer = ElectoralDataImporter()
        
        # Get or create district/constituency/polling station IDs once
        district_id = await importer._get_or_create_district(district)
        logger.info(f"📍 District: {district} (ID: {district_id})")
        
        constituency_id = await importer._get_or_create_constituency(district_id, constituency)
        logger.info(f"📍 Constituency: {constituency} (ID: {constituency_id})")
        
        polling_station_id = await importer._get_or_create_polling_station(
            constituency_id, polling_station, station_number
        )
        logger.info(f"📍 Polling Station: {polling_station} (ID: {polling_station_id}, Number: {station_number})")
        logger.info(f"🚀 Starting Tesseract OCR extraction of {total_pages} pages...")
        
        for page_num in range(start_page, self._get_page_count(extractor.pdf_path) + 1):
            # Update progress
            current_page = page_num - start_page + 1
            progress = int((current_page / total_pages) * 90)
            
            self.active_imports[import_id]['current_page'] = page_num
            self.active_imports[import_id]['progress'] = progress
            
            logger.info(f"📄 Processing page {page_num}/{self._get_page_count(extractor.pdf_path)} ({progress}%)")
            
            # Extract page with Tesseract
            voters_on_page = extractor.extract_voters_from_page(page_num, dpi=300)
            
            if not voters_on_page:
                logger.warning(f"   ⚠️  No voters extracted from page {page_num}")
                continue
            
            # Log extracted data
            logger.info(f"   📝 Extracted {len(voters_on_page)} voters from page {page_num} (OCR):")
            logger.info(f"   {'-' * 80}")
            for i, voter in enumerate(voters_on_page[:3], 1):  # Log first 3 voters
                logger.info(f"   {i}. Serial: {voter.get('serial_no', 'N/A')}, Name: {voter.get('voter_name', 'N/A')}, Age: {voter.get('age', 'N/A')}")
            if len(voters_on_page) > 3:
                logger.info(f"   ... ({len(voters_on_page) - 3} more voters)")
            logger.info(f"   {'-' * 80}")
            
            # Write to CSV and import to database
            page_voters = []
            for voter in voters_on_page:
                row = [
                    voter.get('serial_no', ''),
                    voter.get('division_no', ''),
                    voter.get('house_no', ''),
                    voter.get('voter_name', ''),
                    voter.get('relationship_code', ''),
                    voter.get('relative_name', ''),
                    voter.get('age', ''),
                    voter.get('gender_caste_code', ''),
                    voter.get('voter_id', '')
                ]
                writer.writerow(row)
                
                # Prepare for database import - Create pandas Series
                row_dict = {
                    'Serial Number (வரிசை எண்)': row[0],
                    'Division No (பிரிவு எண்)': row[1],
                    'House No (வீட்டு எண்)': row[2],
                    'Voter Name (வாக்காளரின் பெயர்)': row[3],
                    'Relationship Code (உறவு முறை)': row[4],
                    'Relative Name (உறவினர் பெயர்)': row[5],
                    'Age (வயது)': row[6],
                    'Gender/Caste Code (இனம்)': row[7],
                    'Voter ID No (வாக்காளர் அடையாள அட்டை எண்)': row[8]
                }
                voter_tuple = importer._parse_voter_row(
                    pd.Series(row_dict),
                    polling_station_id
                )
                if voter_tuple:
                    page_voters.append(voter_tuple)
                total_voters += 1
            
            # Import this page's voters to database immediately
            if page_voters:
                logger.info(f"   💾 Inserting {len(page_voters)} voters from page {page_num} into database...")
                
                # Log first few voters being inserted
                logger.info(f"   👥 Sample voters to insert (first 3):")
                for i, voter in enumerate(page_voters[:3], 1):
                    logger.info(f"      {i}. Serial: {voter[1]}, Name: {voter[4]}, Age: {voter[9]}, Voter ID: {voter[12]}")
                if len(page_voters) > 3:
                    logger.info(f"      ... ({len(page_voters) - 3} more voters)")
                
                try:
                    await importer._bulk_insert_voters(page_voters)
                    logger.info(f"   ✅ Successfully inserted {len(page_voters)} voters (polling_station_id={polling_station_id})")
                except Exception as e:
                    logger.error(f"   ❌ Failed to insert voters: {e}")
                    raise
            else:
                logger.warning(f"   ⚠️  No voters found on page {page_num}")
            
            self.active_imports[import_id]['voters_extracted'] = total_voters
            
            # Allow other tasks to run
            await asyncio.sleep(0)
        
        return total_voters
    
    def get_import_status(self, import_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an import job"""
        return self.active_imports.get(import_id)
    
    def cleanup_completed_imports(self, max_age_hours: int = 24):
        """Clean up old completed import jobs"""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        to_delete = []
        for import_id, job in self.active_imports.items():
            if job['status'] in ['completed', 'failed']:
                started_at = datetime.fromisoformat(job['started_at']).timestamp()
                if started_at < cutoff_time:
                    to_delete.append(import_id)
        
        for import_id in to_delete:
            del self.active_imports[import_id]


# Global instance
pdf_import_service = PDFImportService()
