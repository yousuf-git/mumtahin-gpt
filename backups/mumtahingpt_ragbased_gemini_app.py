# Backup file, All code at one place
"""
🎓 MumtahinGPT - AI Examination System (Gemini with RAG)

An intelligent examination system powered by **Google Gemini** that:
- 📄 Analyzes PDF documents with RAG (Retrieval-Augmented Generation)
- ❓ Generates contextual questions based on document chunks
- ✅ Evaluates answers with detailed feedback
- 📊 Provides comprehensive performance reports
- 🔍 Scalable for documents with thousands of pages

---

## Setup Instructions
1. Run the installation cell
2. Set your GEMINI_API_KEY in environment
3. Upload your PDF document
4. Start the examination!

---

Developed By:
- M. Yousuf

In the supervision of:
- Dr. Ghulam Jillani Ansari
- Dr. Shahbaz Hassan Wasti
"""

import os
from google.colab import userdata

# Get from Colab secrets (recommended)
try:
    GEMINI_API_KEY = userdata.get('GEMINI_API_KEY')
    os.environ['GEMINI_API_KEY'] = GEMINI_API_KEY
except:
    pass

# Or uncomment and add your API key here:
# os.environ['GEMINI_API_KEY'] = 'your-google-api-key-here'

# Or load from .env file (recommended for security)
from dotenv import load_dotenv
load_dotenv()

# Check if API key is set
if os.getenv('GEMINI_API_KEY'):
    print("✅ GEMINI_API_KEY found!")
else:
    print("⚠️ GEMINI_API_KEY not set!")
    print("Please set it using Colab secrets or by uncommenting the line above.")

"""# 📦 Install Required Packages"""

# !pip install -q pymupdf pdfplumber gradio reportlab python-dotenv chromadb sentence-transformers google-generativeai

import os
print("✅ Packages installed successfully!")
print("\n🔑 Please set your GEMINI_API_KEY:")
print("   os.environ['GEMINI_API_KEY'] = 'your-api-key-here'")

"""# 🔑 Set your Google API Key"""

import os
from google.colab import userdata

# Get from Colab secrets (recommended)
try:
    GEMINI_API_KEY = userdata.get('GEMINI_API_KEY')
    os.environ['GEMINI_API_KEY'] = GEMINI_API_KEY
except:
    pass

# Or uncomment and add your API key here:
# os.environ['GEMINI_API_KEY'] = 'your-google-api-key-here'

# Or load from .env file (recommended for security)
from dotenv import load_dotenv
load_dotenv()

# Check if API key is set
if os.getenv('GEMINI_API_KEY'):
    print("✅ GEMINI_API_KEY found!")
else:
    print("⚠️ GEMINI_API_KEY not set!")
    print("Please set it using Colab secrets or by uncommenting the line above.")

"""# 🔧 Import Libraries and Initialize"""

import fitz  # PyMuPDF
import pdfplumber
import gradio as gr
import google.generativeai as genai
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import re
import chromadb
from chromadb.utils import embedding_functions
import hashlib

# Get API key from environment
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY not found! Please set it in Colab secrets or environment")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Initialize ChromaDB for RAG
chroma_client = chromadb.Client()
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

print("✅ Libraries imported successfully!")
print(f"🤖 Using Google Gemini for examination")
print(f"🔍 RAG system initialized with ChromaDB")

"""# 📄 PDF Handler Class with RAG Support"""

# 📄 PDF Handler Class with RAG Support
class PDFHandler:
    """Handles PDF document processing, text extraction, and RAG setup."""

    def __init__(self):
        self.extracted_text = None
        self.metadata = {}
        self.collection = None
        self.chunks = []

    def extract_text(self, pdf_path: str) -> Optional[str]:
        """Extract text content from a PDF file."""
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
        """Extract text using PyMuPDF library."""
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
        """Extract text using pdfplumber library (fallback method)."""
        text_content = []
        with pdfplumber.open(pdf_path) as pdf:
            self.metadata = {'pages': len(pdf.pages), 'title': 'Unknown', 'author': 'Unknown'}
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text and text.strip():
                    text_content.append(f"--- Page {page_num} ---\n{text}")
        return "\n\n".join(text_content)

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks for RAG."""
        words = text.split()
        chunks = []

        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)

        return chunks

    def setup_rag_collection(self, document_title: str):
        """Set up ChromaDB collection for the document."""
        try:
            # Create unique collection name based on document
            collection_name = f"doc_{hashlib.md5(document_title.encode()).hexdigest()[:8]}"

            # Delete existing collection if any
            try:
                chroma_client.delete_collection(name=collection_name)
            except:
                pass

            # Create new collection
            self.collection = chroma_client.create_collection(
                name=collection_name,
                embedding_function=embedding_function
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
        """Retrieve relevant document chunks for a query."""
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
        """Get a summary of the extracted PDF content."""
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
        """Calculate optimal number of questions based on document size."""
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
        """Validate if the extracted content is sufficient for analysis."""
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
                chroma_client.delete_collection(name=self.collection.name)
            except:
                pass
            self.collection = None

print("✅ PDF Handler with RAG support created")

"""# 🧠 MumtahinGPT - State Management"""

# 🧠 Mumtahin GPT - State Management
@dataclass
class ConversationState:
    """Maintains the state of the examination conversation."""
    document_text: str = ""
    questions_asked: List[str] = field(default_factory=list)
    answers_given: List[str] = field(default_factory=list)
    evaluations: List[str] = field(default_factory=list)
    marks: List[int] = field(default_factory=list)
    current_question_index: int = 0
    total_questions: int = 5
    document_analysis: str = ""
    document_title: str = "Unknown Document"
    document_type: str = "general"
    focus_areas: List[str] = field(default_factory=list)
    lifelines_total: int = 0
    lifelines_remaining: int = 0
    lifelines_used: List[Tuple[int, str]] = field(default_factory=list)
    awaiting_lifeline_response: bool = False
    last_lifeline_type: str = ""
    final_evaluation: str = ""
    chat_session: Optional[any] = None  # Gemini chat session
    pdf_handler: Optional['PDFHandler'] = None  # Reference to PDF handler for RAG

print("✅ State management created")

"""# 🤖 MumtahinGPT - Core Logic with Gemini Chat"""

# 🤖 Mumtahin GPT - Core Logic with Gemini Chat
class MumtahinGPT:
    """Main class for Mumtahin GPT functionality using Gemini with chat context."""

    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.state = ConversationState()
        self.examiner_personality = """You are a professional academic examiner with a friendly yet formal demeanor.
Your role is to:
- Ask insightful questions about documents
- Evaluate answers constructively
- Provide specific, actionable feedback
- Acknowledge good answers without over-praising
- Be encouraging but maintain academic rigor
Keep responses concise and focused."""

    def _send_message(self, message: str, system_context: Optional[str] = None) -> Tuple[str, Optional[str]]:
        """
        Send message using Gemini chat API with automatic context retention.
        """
        try:
            # Initialize chat session if not exists
            if not self.state.chat_session:
                self.state.chat_session = self.model.start_chat(history=[])

            # Add system context if provided
            full_message = message
            if system_context:
                full_message = f"{system_context}\n\n{message}"

            # Send message and get response
            response = self.state.chat_session.send_message(full_message)
            return response.text, None

        except Exception as e:
            return "", f"Error: {str(e)}"

    def is_examination_complete(self) -> bool:
        """Check if all questions have been asked."""
        return self.state.current_question_index >= self.state.total_questions

    def set_total_questions(self, total: int):
        """Set the total number of questions for the examination."""
        if 1 <= total <= 100:
            self.state.total_questions = total
            self.state.lifelines_total = max(1, total // 3)
            self.state.lifelines_remaining = self.state.lifelines_total

    def use_lifeline(self, lifeline_type: str) -> bool:
        """Use a lifeline (rephrase or new question)."""
        if self.state.lifelines_remaining > 0:
            self.state.lifelines_remaining -= 1
            self.state.lifelines_used.append((self.state.current_question_index, lifeline_type))
            self.state.awaiting_lifeline_response = True
            self.state.last_lifeline_type = lifeline_type
            return True
        return False

    def get_lifelines_status(self) -> Tuple[int, int]:
        """Get lifelines status."""
        return (self.state.lifelines_remaining, self.state.lifelines_total)

    def _get_generic_focus_areas(self) -> List[str]:
        """Get generic focus areas that work for any document type."""
        return [
            "the main topic and central purpose — what is this document about and why does it matter?",
            "the scope and boundaries — what is included, what is excluded, and what are the limitations?",
            "the key points, arguments, or findings — what are the main claims, conclusions, or discoveries?",
            "the evidence, methods, or reasoning — how are conclusions supported and validated?",
            "the implications, significance, and future directions — what impact does this have and what comes next?"
        ]

    def analyze_document(self, document_text: str, document_title: str = "Unknown Document") -> Tuple[str, Optional[str]]:
        """Analyze the uploaded PDF document using RAG."""
        self.state.document_text = document_text
        self.state.document_title = document_title

        # Use RAG to get relevant context for analysis
        analysis_context = self.state.pdf_handler.retrieve_relevant_chunks(
            f"document overview summary main topic {document_title}",
            n_results=3
        ) if self.state.pdf_handler else document_text[:3000]

        prompt = f"""You are analyzing a document to prepare for an examination. Identify the document type and provide a brief summary.

Document Title: {document_title}
Document Content (excerpt):
{analysis_context}...

Provide ONLY:
1. Document Type: Choose ONE from (research_paper, thesis, proposal, book_chapter, book, technical_report, essay, case_study, review_article, tutorial, topic, general)
   - "book" = complete books with multiple chapters
   - "book_chapter" = single chapter from a book
   - "topic" = documents explaining a specific concept (e.g., "Types of AI Models")
   - "general" = if none fit

2. Brief Summary: Write 2-3 concise sentences describing:
   - What this document is about
   - The main subject/focus
   - Key themes covered

Format EXACTLY as:
**Type:** [document_type]
**Summary:** [3-4 sentences only]

Keep the summary brief and factual. Do NOT include suggestions for improvement."""

        analysis, error = self._send_message(prompt, self.examiner_personality)

        if analysis:
            # Extract document type
            type_match = re.search(r'\*\*Type:\*\*\s*(\w+)', analysis, re.IGNORECASE)
            if type_match:
                self.state.document_type = type_match.group(1).lower()

            # Generate focus areas based on document
            self.state.focus_areas = self._generate_focus_areas()
            self.state.document_analysis = analysis

        return analysis, error

    def _generate_focus_areas(self) -> List[str]:
        """Generate dynamic focus areas based on document type and content using RAG."""
        # Use RAG to get relevant context
        focus_context = self.state.pdf_handler.retrieve_relevant_chunks(
            f"main topics concepts themes methodology objectives {self.state.document_type}",
            n_results=5
        ) if self.state.pdf_handler else self.state.document_text[:2500]

        prompt = f"""You are preparing examination questions for a student who has READ this document.

Document Type: {self.state.document_type}
Document Content (relevant excerpts):
{focus_context}...

Generate EXACTLY 5 focus areas that examination questions should cover.

CRITICAL: Focus areas must be about the SUBJECT MATTER/CONTENT, NOT about:
- Document formatting or structure
- Author/submitter details
- Page numbers or layout
- Metadata or administrative information

Instead, focus on:
- The main concepts, ideas, or arguments
- The methodology, approach, or techniques
- The objectives, goals, or purpose
- The results, findings, or outcomes
- The implementation details or design

Format as a numbered list:
1. [Content aspect to examine]
2. [Content aspect to examine]
3. [Content aspect to examine]
4. [Content aspect to examine]
5. [Content aspect to examine]

Focus on understanding the CONTENT, not analyzing the document structure."""

        response, error = self._send_message(prompt)

        if error or not response:
            return self._get_generic_focus_areas()

        # Parse the numbered list
        lines = response.strip().split('\n')
        focus_areas = []

        for line in lines:
            match = re.match(r'^\d+\.\s*(.+)$', line.strip())
            if match:
                focus_areas.append(match.group(1))

        # If we didn't get 5 areas, use generic ones
        if len(focus_areas) < 5:
            return self._get_generic_focus_areas()

        return focus_areas[:5]

    def generate_next_question(self) -> Tuple[Optional[str], Optional[str]]:
        """Generate the next examination question using RAG to avoid repetition."""
        if self.state.current_question_index >= self.state.total_questions:
            return None, "Examination complete"

        # Use focus areas
        if not self.state.focus_areas:
            self.state.focus_areas = self._get_generic_focus_areas()

        focus_index = min(self.state.current_question_index, len(self.state.focus_areas) - 1)
        current_focus = self.state.focus_areas[focus_index]

        # Check if this is a lifeline request
        if self.state.awaiting_lifeline_response and self.state.last_lifeline_type:
            return self._handle_lifeline_question()

        # Retrieve relevant context using RAG
        relevant_context = self.state.pdf_handler.retrieve_relevant_chunks(
            f"{current_focus} {self.state.document_type}",
            n_results=3
        ) if self.state.pdf_handler else self.state.document_text[:2000]

        # Build list of recent questions to avoid repetition (sliding window)
        # Only include last 5-7 questions to keep token usage bounded
        recent_questions = self.state.questions_asked[-7:]
        previous_questions = "\n".join([f"- {q}" for q in recent_questions])

        prompt = f"""Generate examination question #{self.state.current_question_index + 1} of {self.state.total_questions}.

Document Type: {self.state.document_type}
Document Title: {self.state.document_title}

Focus Area: {current_focus}

Relevant Content:
{relevant_context}

Recent questions to avoid (also check our chat history for more context):
{previous_questions if previous_questions else "None"}

Generate ONE clear, specific question that tests understanding of this focus area.
Requirements:
- Question should be about the CONTENT they read
- Should require understanding, not just recall
- Must be answerable from the document
- Keep it concise and clear
- MUST be completely different from recent questions and our conversation history

Respond with ONLY the question text, no preamble."""

        question, error = self._send_message(prompt)

        if not error:
            self.state.questions_asked.append(question)
            self.state.current_question_index += 1

        return question, error

    def _handle_lifeline_question(self) -> Tuple[Optional[str], Optional[str]]:
        """Handle lifeline question generation using RAG."""
        last_question = self.state.questions_asked[-1] if self.state.questions_asked else ""
        lifeline_type = self.state.last_lifeline_type

        if lifeline_type == "rephrase":
            # Get context for the question being rephrased
            relevant_context = self.state.pdf_handler.retrieve_relevant_chunks(
                f"{last_question}",
                n_results=2
            ) if self.state.pdf_handler else self.state.document_text[:1500]

            prompt = f"""Rephrase this question in a simpler, clearer way while testing the same concept:

Original Question: {last_question}

Relevant Context:
{relevant_context}

Provide ONLY the rephrased question, no explanation."""
        else:  # new question
            focus_index = min(self.state.current_question_index - 1, len(self.state.focus_areas) - 1)
            current_focus = self.state.focus_areas[focus_index]

            # Get context for new question
            relevant_context = self.state.pdf_handler.retrieve_relevant_chunks(
                f"{current_focus} {self.state.document_type}",
                n_results=3
            ) if self.state.pdf_handler else self.state.document_text[:2000]

            prompt = f"""Generate a DIFFERENT question about the same focus area:

Focus Area: {current_focus}
Previous Question (avoid similar): {last_question}

Relevant Context:
{relevant_context}

Provide ONLY the new question, no explanation."""

        question, error = self._send_message(prompt)

        if not error:
            # Replace the last question
            if self.state.questions_asked:
                self.state.questions_asked[-1] = question

        self.state.awaiting_lifeline_response = False
        self.state.last_lifeline_type = ""

        return question, error

    def evaluate_answer(self, user_answer: str) -> Tuple[str, Optional[str]]:
        """Evaluate the user's answer using RAG for context."""
        current_q_idx = self.state.current_question_index - 1
        current_question = self.state.questions_asked[current_q_idx]

        # Retrieve relevant context for evaluation using RAG
        relevant_context = self.state.pdf_handler.retrieve_relevant_chunks(
            f"{current_question} {user_answer}",
            n_results=3
        ) if self.state.pdf_handler else ""

        prompt = f"""Evaluate this answer to the examination question.

Question: {current_question}

Student's Answer: {user_answer}

Relevant Document Context:
{relevant_context}

Provide:
1. Score out of 10
2. Brief evaluation (2-3 sentences)
3. What was good
4. What could be improved (if applicable)

Format:
**Score:** X/10
**Evaluation:** [Your evaluation]"""

        evaluation, error = self._send_message(prompt)

        if not error:
            # Extract score
            score_match = re.search(r'(\d+)/10', evaluation)
            score = int(score_match.group(1)) if score_match else 5

            self.state.answers_given.append(user_answer)
            self.state.evaluations.append(evaluation)
            self.state.marks.append(score)

        return evaluation, error

    def generate_final_summary(self) -> Tuple[str, Optional[str]]:
        """Generate final examination summary using RAG for document overview."""
        total_marks = sum(self.state.marks)
        max_marks = self.state.total_questions * 10
        percentage = (total_marks / max_marks * 100) if max_marks > 0 else 0

        # Build Q&A summary
        qa_summary = "\n\n".join([
            f"**Q{i+1}:** {q}\n**Answer:** {a}\n{e}"
            for i, (q, a, e) in enumerate(zip(
                self.state.questions_asked,
                self.state.answers_given,
                self.state.evaluations
            ))
        ])

        # Get comprehensive document overview using RAG
        document_overview = self.state.pdf_handler.retrieve_relevant_chunks(
            f"main topics summary key concepts {self.state.document_title}",
            n_results=5
        ) if self.state.pdf_handler else self.state.document_text[:3000]

        prompt = f"""Generate a final examination summary and feedback.

Document: {self.state.document_title}
Total Score: {total_marks}/{max_marks} ({percentage:.1f}%)
Questions: {self.state.total_questions}

Document Overview:
{document_overview}

Question-Answer Summary:
{qa_summary}

Provide:
1. Overall Performance Assessment
2. Key Strengths
3. Areas for Improvement
4. Recommendations

Keep it concise and encouraging."""

        summary, error = self._send_message(prompt)

        if not error:
            self.state.final_evaluation = summary

        return summary, error

    def reset_state(self):
        """Reset the examination state."""
        self.state = ConversationState()

    def get_progress(self) -> Tuple[int, int]:
        """Get current progress."""
        return (self.state.current_question_index, self.state.total_questions)

    def get_session_data(self) -> Dict:
        """Get complete session data for export."""
        return {
            'document_title': self.state.document_title,
            'document_type': self.state.document_type,
            'total_questions': self.state.total_questions,
            'questions': self.state.questions_asked,
            'answers': self.state.answers_given,
            'evaluations': self.state.evaluations,
            'marks': self.state.marks,
            'total_marks': sum(self.state.marks),
            'max_marks': self.state.total_questions * 10,
            'percentage': (sum(self.state.marks) / (self.state.total_questions * 10) * 100) if self.state.total_questions > 0 else 0,
            'lifelines_used': len(self.state.lifelines_used),
            'final_evaluation': self.state.final_evaluation
        }

print("✅ Mumtahin GPT with Gemini chat context created")

"""# 📊 PDF Export Functionality"""

# 📊 PDF Export Functionality
def export_report(examiner: MumtahinGPT) -> Tuple[str, Optional[str]]:
    """Export the examination session as a PDF report."""
    if not examiner.state.questions_asked:
        return "", "No examination data to export"

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"mumtahingpt_report_{timestamp}.pdf"
        filepath = os.path.abspath(filename)

        # Custom footer function
        def add_footer(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 9)
            canvas.setFillColor(colors.grey)
            canvas.drawString(0.75*inch, 0.5*inch, "Generated by MumtahinGPT")
            canvas.restoreState()

        doc = SimpleDocTemplate(filepath, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.75*inch)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#667eea'),
            spaceAfter=30, alignment=TA_CENTER, fontName='Helvetica-Bold'
        )
        story.append(Paragraph("MumtahinGPT Report", title_style))
        story.append(Spacer(1, 0.3*inch))

        # Session info
        session_data = examiner.get_session_data()

        info_data = [
            ['Document:', session_data['document_title']],
            ['Type:', session_data['document_type'].replace('_', ' ').title()],
            ['Date:', datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ['Questions:', str(session_data['total_questions'])],
            ['Score:', f"{session_data['total_marks']}/{session_data['max_marks']} ({session_data['percentage']:.1f}%)"],
            ['Lifelines Used:', str(session_data['lifelines_used'])]
        ]

        info_table = Table(info_data, colWidths=[1.5*inch, 5*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))

        story.append(info_table)
        story.append(Spacer(1, 0.3*inch))

        # Questions and Answers
        qa_title_style = ParagraphStyle(
            'QATitle', parent=styles['Heading2'], fontSize=16, textColor=colors.HexColor('#667eea'),
            spaceAfter=15, fontName='Helvetica-Bold'
        )
        story.append(Paragraph("Questions & Answers", qa_title_style))
        story.append(Spacer(1, 0.2*inch))

        for i, (q, a, e, m) in enumerate(zip(
            session_data['questions'],
            session_data['answers'],
            session_data['evaluations'],
            session_data['marks']
        )):
            # Question
            q_style = ParagraphStyle('Question', parent=styles['Normal'], fontSize=11,
                                    textColor=colors.HexColor('#1a237e'), fontName='Helvetica-Bold',
                                    spaceAfter=8, leftIndent=10)
            story.append(Paragraph(f"<b>Q{i+1}:</b> {q}", q_style))

            # Answer
            a_style = ParagraphStyle('Answer', parent=styles['Normal'], fontSize=10,
                                    leftIndent=20, spaceAfter=8)
            story.append(Paragraph(f"<b>Your Answer:</b> {a}", a_style))

            # Evaluation
            e_formatted = e.replace('**', '<b>', 1).replace('**', '</b>', 1)
            while '**' in e_formatted:
                e_formatted = e_formatted.replace('**', '<b>', 1).replace('**', '</b>', 1)
            e_formatted = e_formatted.replace('\n', '<br/>')

            e_style = ParagraphStyle('Eval', parent=styles['Normal'], fontSize=10,
                                    leftIndent=20, spaceAfter=4, textColor=colors.HexColor('#2e7d32'),
                                    leading=14)
            story.append(Paragraph(e_formatted, e_style))

            story.append(Spacer(1, 0.2*inch))

        # Final Summary
        if session_data.get('final_evaluation'):
            story.append(PageBreak())
            story.append(Paragraph("Final Evaluation", qa_title_style))
            story.append(Spacer(1, 0.2*inch))

            final_eval = session_data['final_evaluation']
            final_eval_formatted = final_eval.replace('**', '<b>', 1).replace('**', '</b>', 1)
            while '**' in final_eval_formatted:
                final_eval_formatted = final_eval_formatted.replace('**', '<b>', 1).replace('**', '</b>', 1)
            final_eval_formatted = final_eval_formatted.replace('\n', '<br/>')

            summary_style = ParagraphStyle('Summary', parent=styles['Normal'], fontSize=10,
                                         spaceAfter=6, leading=14)
            story.append(Paragraph(final_eval_formatted, summary_style))

        doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)

        if os.path.exists(filepath):
            print(f"✅ Report generated: {filepath}")
            return filepath, None
        else:
            return "", "Failed to create PDF file"

    except Exception as e:
        return "", f"Error exporting report: {str(e)}"

print("✅ Export functionality ready")

"""# 🎨 Gradio Interface with Application Logic"""

# 🎨 Gradio Interface with Application Logic
# Global state
examiner: Optional[MumtahinGPT] = None
pdf_handler: PDFHandler = PDFHandler()
session_active: bool = False

def initialize_app():
    """Initialize the application."""
    global examiner
    try:
        examiner = MumtahinGPT()
        return "✅ Application initialized successfully!"
    except Exception as e:
        return f"⚠️ Error initializing application: {str(e)}"

def process_pdf(pdf_file, num_questions: int):
    """Process uploaded PDF file and start the examination with RAG."""
    global session_active

    if pdf_file is None:
        return "⚠️ Please upload a PDF file", [], "", "", "", ""

    try:
        pdf_path = pdf_file.name
        document_title = os.path.splitext(os.path.basename(pdf_path))[0]

        # Show initial loading message
        loading_msg = "📄 **Extracting text from PDF...**"
        yield loading_msg, [], "", "", "", "⏳ Processing..."

        extracted_text = pdf_handler.extract_text(pdf_path)

        if not extracted_text or not pdf_handler.validate_content():
            yield "❌ Failed to extract sufficient text from PDF", [], "", "", "", ""
            return

        summary = pdf_handler.get_summary()

        # Show chunking progress
        loading_msg = f"""📄 **PDF Extraction Complete!**

📊 **Document Stats:**
- Pages: {summary.get('pages', 'N/A')}
- Words: {summary.get('word_count', 'N/A')}

🔄 **Processing document with RAG...**
Creating semantic chunks for efficient querying. This may take a moment for large documents."""
        yield loading_msg, [], "", "", "", "⏳ Processing..."

        # Setup RAG collection
        rag_status = pdf_handler.setup_rag_collection(document_title)
        if not rag_status:
            yield "❌ Failed to setup RAG system", [], "", "", "", ""
            return

        summary = pdf_handler.get_summary()

        # Calculate optimal questions based on document size
        optimal_questions = pdf_handler.calculate_optimal_questions()
        actual_questions = min(num_questions, optimal_questions) if num_questions > 0 else optimal_questions

        examiner.state.pdf_handler = pdf_handler
        examiner.set_total_questions(actual_questions)
        lifelines_remaining, lifelines_total = examiner.get_lifelines_status()

        # Show analysis progress
        loading_msg = f"""✅ **RAG Setup Complete!**

📊 **RAG Stats:**
- Chunks Created: {summary.get('chunks', 0)}
- Optimal Questions: {optimal_questions}
- Selected Questions: {actual_questions}

🤖 **Analyzing document...**
AI is examining the content to understand the document type and key topics."""
        yield loading_msg, [], "", "", "", "⏳ Processing..."

        # Analyze document
        analysis, analysis_error = examiner.analyze_document(extracted_text, document_title)
        if analysis_error:
            yield f"❌ Error analyzing document: {analysis_error}", [], "", "", "", ""
            return

        session_active = True

        # Show question generation progress
        doc_type_display = examiner.state.document_type.replace('_', ' ').title()
        loading_msg = f"""✅ **Document Analysis Complete!**

📄 **Document Type:** {doc_type_display}

💭 **Generating first question...**
Using RAG to create a contextual question based on document content."""
        yield loading_msg, [], "", "", "", "⏳ Processing..."

        # Generate first question
        first_question, question_error = examiner.generate_next_question()
        if question_error:
            yield f"❌ Error generating question: {question_error}", [], "", "", "", ""
            return

        # Extract clean summary
        summary_match = re.search(r'\*\*Summary:\*\*\s*(.+?)(?:\n|$)', analysis, re.DOTALL)
        clean_summary = summary_match.group(1).strip() if summary_match else analysis.split('\n')[-1].strip()

        doc_type_display = examiner.state.document_type.replace('_', ' ').title()

        status_msg = f"""✅ **PDF Processed Successfully!**

📄 **Document Info:**
- Title: {document_title}
- Type: {doc_type_display}
- Pages: {summary.get('pages', 'N/A')}
- Words: {summary.get('word_count', 'N/A')}
- Chunks (RAG): {summary.get('chunks', 0)}
- Total Questions: {actual_questions}
- Lifelines: {lifelines_remaining}/{lifelines_total}

📋 **Summary:**
{clean_summary}

---
**The examination will now begin. Please answer each question thoughtfully.**"""

        initial_chat = [[None, f"**Examiner:** {first_question}"]]
        model_info = f"🤖 **Current AI Model:** gemini-2.5-flash"
        lifelines_status = f"🎯 **Lifelines Available:** {lifelines_remaining}/{lifelines_total}"

        yield status_msg, initial_chat, "", model_info, lifelines_status, ""
        return

    except Exception as e:
        return f"❌ Error processing PDF: {str(e)}", [], "", "", "", ""

def chat_with_examiner(message: str, history: List):
    """Handle conversation with the AI examiner."""
    global session_active

    if not session_active:
        error_msg = "⚠️ Please upload and analyze a PDF document first."
        return history, "", error_msg, "", "", False

    if not message.strip():
        lifelines_remaining, lifelines_total = examiner.get_lifelines_status()
        return history, "", "", "🤖 **Current AI Model:** gemini-2.5-flash", f"🎯 **Lifelines:** {lifelines_remaining}/{lifelines_total}", False

    history.append([message, None])

    try:
        evaluation, eval_error = examiner.evaluate_answer(message)

        if eval_error:
            history.pop()
            return history, "", f"❌ Error evaluating answer: {eval_error}", "", "", True

        if examiner.is_examination_complete():
            final_summary, summary_error = examiner.generate_final_summary()
            response = f"{evaluation}\n\n---\n🎉 **Examination Complete!**\n\n{final_summary}"
            history[-1][1] = f"**Examiner:** {response}"
            lifelines_remaining, lifelines_total = examiner.get_lifelines_status()
            return history, "", "", "🤖 **Model:** gemini-2.5-flash", f"🎯 **Lifelines:** {lifelines_remaining}/{lifelines_total}", False

        next_question, question_error = examiner.generate_next_question()

        if question_error:
            history[-1][1] = f"**Examiner:** {evaluation}"
            return history, "", f"⚠️ Error generating next question: {question_error}", "", "", True

        response = f"{evaluation}\n\n---\n**Next Question:**\n{next_question}"
        history[-1][1] = f"**Examiner:** {response}"

        model_info = "🤖 **Current AI Model:** gemini-2.5-flash"
        lifelines_remaining, lifelines_total = examiner.get_lifelines_status()
        lifelines_info = f"🎯 **Lifelines:** {lifelines_remaining}/{lifelines_total}"

        return history, "", "", model_info, lifelines_info, False

    except Exception as e:
        error_msg = f"❌ An unexpected error occurred: {str(e)}"
        history.pop()
        lifelines_remaining, lifelines_total = examiner.get_lifelines_status()
        return history, "", error_msg, "", f"🎯 **Lifelines:** {lifelines_remaining}/{lifelines_total}", True

def use_lifeline(lifeline_type: str, history: List):
    """Handle lifeline usage."""
    if not session_active:
        return history, "⚠️ Please start an examination first", "", ""

    lifelines_remaining, lifelines_total = examiner.get_lifelines_status()

    if lifelines_remaining <= 0:
        return history, "⚠️ No lifelines remaining!", "🤖 **Model:** gemini-2.5-flash", f"🎯 **Lifelines:** 0/{lifelines_total}"

    if not examiner.use_lifeline(lifeline_type):
        return history, "⚠️ Failed to use lifeline", "", ""

    try:
        question, error = examiner.generate_next_question()

        if error:
            return history, f"❌ Error: {error}", "", ""

        lifeline_msg = "🔄 **Rephrased Question**" if lifeline_type == "rephrase" else "✨ **New Question**"
        history.append([None, f"**Examiner:** {lifeline_msg}\n\n{question}"])

        lifelines_remaining, lifelines_total = examiner.get_lifelines_status()
        return history, "", "🤖 **Model:** gemini-2.5-flash", f"🎯 **Lifelines:** {lifelines_remaining}/{lifelines_total}"

    except Exception as e:
        return history, f"❌ Error: {str(e)}", "", ""

def reset_session():
    """Reset the examination session."""
    global session_active
    examiner.reset_state()
    pdf_handler.reset()
    session_active = False
    return "🔄 Session reset. Upload a new PDF to start.", [], "", "", "", "", False

def retry_last_action(message: str, history: List):
    """Retry the last failed action."""
    return chat_with_examiner(message, history)

def export_session():
    """Export the examination session as a PDF report."""
    if not session_active and not examiner.state.questions_asked:
        return None, "⚠️ No examination data to export"

    filename, error = export_report(examiner)

    if error:
        return None, f"❌ {error}"

    return filename, f"✅ Report exported: {filename}"

print("✅ Application logic ready")

"""# 🚀 Launch Gradio Interface"""

# 🚀 Launch Gradio Interface
init_status = initialize_app()
print(init_status)

# e3f2fd

custom_css = """
#chatbot { height: 500px; }
#status_box {
    border-left: 4px solid #2196F3 !important;
    padding: 15px !important;
    background-color: #FFFAF0 !important;
    border-radius: 5px !important;
    color: #1565c0 !important;
}
#error_notification {
    padding: 12px 16px !important;
    margin-bottom: 15px !important;
    border-radius: 8px !important;
    background-color: #ffebee !important;
    border-left: 4px solid #f44336 !important;
    color: #c62828 !important;
}
#model_indicator {
    padding: 10px 16px !important;
    border-radius: 8px !important;
    background-color: #e8eaf6 !important;
    border-left: 4px solid #3f51b5 !important;
    color: #1a237e !important;
}
#lifelines_status {
    padding: 10px 16px !important;
    border-radius: 8px !important;
    background-color: #fff3e0 !important;
    border-left: 4px solid #ff9800 !important;
    color: #e65100 !important;
}
.footer {
    text-align: center;
    padding: 20px;
    margin-top: 20px;
    border-top: 2px solid #667eea;
    color: #666;
    font-size: 16px;
}
"""

with gr.Blocks(css=custom_css, theme=gr.themes.Soft(), title="MumtahinGPT - Gemini") as demo:
    gr.HTML("""
    <div style='text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; border-radius: 10px; margin-bottom: 20px;'>
        <h1 style='margin: 0; font-size: 2.5em; color:white;'>🎓 MumtahinGPT</h1>
        <p style='margin: 10px 0 0 0; font-size: 1.2em; color: white;'>Powered by Google Gemini with RAG - AI Document Examination System</p>
    </div>
    """)

    with gr.Accordion("📖 How to Use Mumtahin GPT (Click to expand)", open=False):
        gr.Markdown("""
        ### Step-by-Step Guide:

        **Step 1: Upload Your Document** 📄
        - Click "Upload PDF" button
        - Select your PDF document
        - Supports documents of any size (10 pages to 1000+ pages)

        **Step 2: Configure Examination** ⚙️
        - System auto-calculates optimal questions based on document size:
          - ≤10 pages: 5 questions
          - ≤50 pages: 10 questions
          - ≤100 pages: 20 questions
          - ≤500 pages: 50 questions
          - >500 pages: 100 questions
        - Or manually select 1-100 questions

        **Step 3: RAG Processing** 🔍
        - Document is chunked into semantic segments
        - Embeddings created for efficient retrieval
        - Only relevant chunks used for each question (saves tokens!)

        **Step 4: Answer Questions** ✍️
        - Type answers in the text box
        - Get instant AI feedback
        - Progress through examination

        **Step 5: Use Lifelines** 🎯
        - Rephrase: Simpler version of current question
        - New Question: Different question on same topic

        **Step 6: Export Results** 📊
        - Complete examination to see final score
        - Download PDF report with detailed analysis

        ### Key Features:
        - **RAG Technology**: Only retrieves relevant document sections
        - **Scalable**: Handles books with 1000+ pages efficiently
        - **Smart Questions**: No repetition (chat context + sliding window)
        - **Dynamic Limits**: Question count adapts to document size
        """)

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 📤 Upload Document")
            pdf_upload = gr.File(label="Upload PDF", file_types=[".pdf"])
            num_questions = gr.Slider(minimum=1, maximum=100, value=5, step=1,
                                     label="Number of Questions (Auto-calculated if set to max)")
            analyze_btn = gr.Button("🔍 Analyze & Start Examination", variant="primary", size="lg")
            processing_indicator = gr.Markdown("")

            gr.Markdown("### 🎯 Lifelines")
            with gr.Row():
                rephrase_btn = gr.Button("🔄 Rephrase", size="sm")
                new_question_btn = gr.Button("✨ New Question", size="sm")

            gr.Markdown("### 📋 Examination Summary")
            status_display = gr.Markdown("", elem_id="status_box")

            gr.Markdown("### 📊 Export")
            export_btn = gr.Button("📥 Export Report", size="sm", variant="primary")
            with gr.Row():
                export_file = gr.File(label="📄 Download", visible=True)
            export_status = gr.Markdown("")

            gr.Markdown("---")
            reset_btn = gr.Button("🔄 Reset Session", size="sm", variant="stop")

        with gr.Column(scale=2):
            model_indicator = gr.Markdown("", elem_id="model_indicator")
            lifelines_status = gr.Markdown("", elem_id="lifelines_status")
            error_display = gr.Markdown("", elem_id="error_notification")

            chatbot = gr.Chatbot(label="Examination Chat", elem_id="chatbot", height=500)

            with gr.Row():
                user_input = gr.Textbox(
                    placeholder="Type your answer here...",
                    label="Your Answer",
                    lines=3,
                    scale=4,
                    show_label=False
                )
                submit_btn = gr.Button("📤 Send", size="lg", scale=1, variant="primary")
                retry_btn = gr.Button("🔁 Retry", size="sm", scale=1, visible=False)

    gr.HTML("""
    <div class='footer'>
        <p style='margin: 0; font-size: 18px;'>
            Developed with ❤️ by <strong>Team MumtahinGPT</strong> | Powered by Google Gemini
        </p>
    </div>
    """)

    # Event handlers
    analyze_btn.click(
        fn=process_pdf,
        inputs=[pdf_upload, num_questions],
        outputs=[status_display, chatbot, error_display, model_indicator, lifelines_status, processing_indicator]
    )

    submit_btn.click(
        fn=chat_with_examiner,
        inputs=[user_input, chatbot],
        outputs=[chatbot, user_input, error_display, model_indicator, lifelines_status, retry_btn]
    )

    user_input.submit(
        fn=chat_with_examiner,
        inputs=[user_input, chatbot],
        outputs=[chatbot, user_input, error_display, model_indicator, lifelines_status, retry_btn]
    )

    rephrase_btn.click(
        fn=lambda hist: use_lifeline("rephrase", hist),
        inputs=[chatbot],
        outputs=[chatbot, error_display, model_indicator, lifelines_status]
    )

    new_question_btn.click(
        fn=lambda hist: use_lifeline("new", hist),
        inputs=[chatbot],
        outputs=[chatbot, error_display, model_indicator, lifelines_status]
    )

    reset_btn.click(
        fn=reset_session,
        outputs=[status_display, chatbot, user_input, error_display, model_indicator, lifelines_status, retry_btn]
    )

    retry_btn.click(
        fn=retry_last_action,
        inputs=[user_input, chatbot],
        outputs=[chatbot, user_input, error_display, model_indicator, lifelines_status, retry_btn]
    )

    export_btn.click(
        fn=export_session,
        outputs=[export_file, export_status]
    )

demo.launch(debug=True, share=True)
