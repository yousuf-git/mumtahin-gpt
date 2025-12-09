"""
PDF Handler Module
==================
This module handles PDF document extraction and processing.
It provides functionality to extract text content from uploaded PDF files.

Dependencies:
    - PyMuPDF (fitz): Primary PDF text extraction
    - pdfplumber: Fallback for complex PDFs
"""

import fitz  # PyMuPDF
import pdfplumber
from typing import Optional, Dict


class PDFHandler:
    """
    Handles PDF document processing and text extraction.
    
    This class provides methods to extract text content from PDF files
    using multiple approaches to ensure reliable extraction.
    """
    
    def __init__(self):
        """Initialize the PDF handler."""
        self.extracted_text = None
        self.metadata = {}
    
    def extract_text(self, pdf_path: str) -> Optional[str]:
        """
        Extract text content from a PDF file.
        
        Tries PyMuPDF first for speed, falls back to pdfplumber
        if extraction yields poor results.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            Optional[str]: Extracted text content, or None if extraction fails
        """
        try:
            # Try PyMuPDF first (faster)
            text = self._extract_with_pymupdf(pdf_path)
            
            # If text is too short, try pdfplumber as fallback
            if not text or len(text.strip()) < 50:
                text = self._extract_with_pdfplumber(pdf_path)
            
            self.extracted_text = text
            return text
            
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
            return None
    
    def _extract_with_pymupdf(self, pdf_path: str) -> str:
        """
        Extract text using PyMuPDF library.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            str: Extracted text content
        """
        text_content = []
        
        with fitz.open(pdf_path) as doc:
            # Store metadata
            self.metadata = {
                'pages': len(doc),
                'title': doc.metadata.get('title', 'Unknown'),
                'author': doc.metadata.get('author', 'Unknown')
            }
            
            # Extract text from each page
            for page_num, page in enumerate(doc, 1):
                text = page.get_text()
                if text.strip():
                    text_content.append(f"--- Page {page_num} ---\n{text}")
        
        return "\n\n".join(text_content)
    
    def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        """
        Extract text using pdfplumber library (fallback method).
        
        This method is more robust for complex PDFs with tables
        and unusual layouts.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            str: Extracted text content
        """
        text_content = []
        
        with pdfplumber.open(pdf_path) as pdf:
            # Store metadata
            self.metadata = {
                'pages': len(pdf.pages),
                'title': 'Unknown',
                'author': 'Unknown'
            }
            
            # Extract text from each page
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text and text.strip():
                    text_content.append(f"--- Page {page_num} ---\n{text}")
        
        return "\n\n".join(text_content)
    
    def get_summary(self) -> Dict[str, any]:
        """
        Get a summary of the extracted PDF content.
        
        Returns:
            Dict: Summary information including word count, page count, etc.
        """
        if not self.extracted_text:
            return {}
        
        words = self.extracted_text.split()
        
        return {
            'word_count': len(words),
            'character_count': len(self.extracted_text),
            'pages': self.metadata.get('pages', 0),
            'title': self.metadata.get('title', 'Unknown'),
            'author': self.metadata.get('author', 'Unknown')
        }
    
    def validate_content(self) -> bool:
        """
        Validate if the extracted content is sufficient for analysis.
        
        Returns:
            bool: True if content is valid, False otherwise
        """
        if not self.extracted_text:
            return False
        
        # Check if we have meaningful content (at least 100 characters)
        return len(self.extracted_text.strip()) >= 100
    
    def reset(self):
        """Reset the PDF handler state."""
        self.extracted_text = None
        self.metadata = {}


# Utility function for easy access
def extract_pdf_text(pdf_path: str) -> Optional[str]:
    """
    Convenience function to extract text from a PDF file.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        Optional[str]: Extracted text content
    """
    handler = PDFHandler()
    return handler.extract_text(pdf_path)
