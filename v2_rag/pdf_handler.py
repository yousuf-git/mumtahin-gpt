"""
MumtahinGPT PDF Handler Module with RAG Support
================================================
This module handles PDF document processing, text extraction, and RAG (Retrieval-Augmented Generation) setup.
It provides functionality to extract text content from uploaded PDF files and manage semantic chunking
for efficient querying with ChromaDB.

Dependencies:
    - PyMuPDF (fitz): Primary PDF text extraction
    - pdfplumber: Fallback for complex PDFs
    - ChromaDB: Vector database for RAG
    - sentence-transformers: Embedding generation
"""

import fitz  # PyMuPDF
import pdfplumber
from typing import Optional, Dict, List
import chromadb
from chromadb.utils import embedding_functions
import hashlib


class PDFHandler:
    """
    Handles PDF document processing, text extraction, and RAG setup.
    
    This class provides methods to extract text content from PDF files,
    chunk documents for semantic search, and manage ChromaDB collections
    for Retrieval-Augmented Generation.
    """
    
    def __init__(self, chroma_client, embedding_function):
        """
        Initialize the PDF handler with ChromaDB components.
        
        Args:
            chroma_client: ChromaDB client instance
            embedding_function: Sentence transformer embedding function
        """
        self.extracted_text = None
        self.metadata = {}
        self.collection = None
        self.chunks = []
        self.chroma_client = chroma_client
        self.embedding_function = embedding_function
    
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
            self.metadata = {
                'pages': len(doc),
                'title': doc.metadata.get('title', 'Unknown'),
                'author': doc.metadata.get('author', 'Unknown')
            }
            for page_num, page in enumerate(doc, 1):
                text = page.get_text()
                if text.strip():
                    text_content.append(f"--- Page {page_num} ---\n{text}")
        return "\n\n".join(text_content)
    
    def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        """
        Extract text using pdfplumber library (fallback method).
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            str: Extracted text content
        """
        text_content = []
        with pdfplumber.open(pdf_path) as pdf:
            self.metadata = {'pages': len(pdf.pages), 'title': 'Unknown', 'author': 'Unknown'}
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text and text.strip():
                    text_content.append(f"--- Page {page_num} ---\n{text}")
        return "\n\n".join(text_content)
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Split text into overlapping chunks for RAG.
        
        Args:
            text (str): Text to chunk
            chunk_size (int): Number of words per chunk
            overlap (int): Number of overlapping words between chunks
            
        Returns:
            List[str]: List of text chunks
        """
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        
        return chunks
    
    def setup_rag_collection(self, document_title: str) -> bool:
        """
        Set up ChromaDB collection for the document.
        
        Args:
            document_title (str): Title of the document
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create unique collection name based on document
            collection_name = f"doc_{hashlib.md5(document_title.encode()).hexdigest()[:8]}"
            
            # Delete existing collection if any
            try:
                self.chroma_client.delete_collection(name=collection_name)
            except:
                pass
            
            # Create new collection
            self.collection = self.chroma_client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            
            # Chunk the document
            self.chunks = self.chunk_text(self.extracted_text)
            
            # Add chunks to collection
            self.collection.add(
                documents=self.chunks,
                ids=[f"chunk_{i}" for i in range(len(self.chunks))],
                metadatas=[{"chunk_index": i} for i in range(len(self.chunks))]
            )
            
            print(f"✅ RAG collection created with {len(self.chunks)} chunks")
            return True
            
        except Exception as e:
            print(f"Error setting up RAG: {str(e)}")
            return False
    
    def retrieve_relevant_chunks(self, query: str, n_results: int = 5) -> str:
        """
        Retrieve relevant document chunks for a query.
        
        Args:
            query (str): Query text
            n_results (int): Number of results to retrieve
            
        Returns:
            str: Concatenated relevant chunks
        """
        if not self.collection:
            return self.extracted_text[:3000]  # Fallback to first 3000 chars
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(n_results, len(self.chunks))
            )
            
            if results and results['documents']:
                return "\n\n".join(results['documents'][0])
            else:
                return self.extracted_text[:3000]
                
        except Exception as e:
            print(f"Error retrieving chunks: {str(e)}")
            return self.extracted_text[:3000]
    
    def get_summary(self) -> Dict:
        """
        Get a summary of the extracted PDF content.
        
        Returns:
            Dict: Summary containing word count, page count, etc.
        """
        if not self.extracted_text:
            return {}
        words = self.extracted_text.split()
        return {
            'word_count': len(words),
            'character_count': len(self.extracted_text),
            'pages': self.metadata.get('pages', 0),
            'title': self.metadata.get('title', 'Unknown'),
            'author': self.metadata.get('author', 'Unknown'),
            'chunks': len(self.chunks) if self.chunks else 0
        }
    
    def calculate_optimal_questions(self) -> int:
        """
        Calculate optimal number of questions based on document size.
        
        Returns:
            int: Optimal number of questions
        """
        pages = self.metadata.get('pages', 0)
        
        if pages <= 10:
            return 5
        elif pages <= 50:
            return 10
        elif pages <= 100:
            return 20
        elif pages <= 500:
            return 50
        else:
            return 100
    
    def validate_content(self) -> bool:
        """
        Validate if the extracted content is sufficient for analysis.
        
        Returns:
            bool: True if content is sufficient, False otherwise
        """
        if not self.extracted_text:
            return False
        return len(self.extracted_text.strip()) >= 100
    
    def reset(self):
        """Reset the PDF handler state."""
        self.extracted_text = None
        self.metadata = {}
        self.chunks = []
        if self.collection:
            try:
                self.chroma_client.delete_collection(name=self.collection.name)
            except:
                pass
            self.collection = None
