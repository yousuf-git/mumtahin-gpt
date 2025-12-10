"""
MumtahinGPT Examiner Logic Module with RAG
===========================================
This module contains the core logic for the MumtahinGPT functionality with RAG support.
It handles question generation, answer evaluation, and conversation management
using Google's Gemini API with Retrieval-Augmented Generation.

Dependencies:
    - google.generativeai: For AI model interaction
    - chromadb: For vector database operations
"""

import google.generativeai as genai
from typing import List, Dict, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
import re

if TYPE_CHECKING:
    from pdf_handler import PDFHandler


@dataclass
class ConversationState:
    """
    Maintains the state of the examination conversation.
    
    Attributes:
        document_text: The extracted PDF content
        questions_asked: List of questions already asked
        answers_given: List of answers provided by the user
        evaluations: List of evaluations for each answer
        marks: List of marks (out of 10) for each answer
        current_question_index: Index of the current question
        total_questions: Total number of questions to ask
        document_analysis: Initial analysis of the document
        document_title: Title of the document
        document_type: Type of document detected (e.g., 'research', 'proposal', 'thesis', etc.)
        focus_areas: Dynamic focus areas generated based on document type
        lifelines_total: Total lifelines available
        lifelines_remaining: Remaining lifelines
        lifelines_used: List of (question_index, lifeline_type) tuples
        awaiting_lifeline_response: Flag indicating if waiting for lifeline response
        last_lifeline_type: Type of last lifeline used ('rephrase' or 'new')
        final_evaluation: Final evaluation summary
        chat_session: Gemini chat session for context retention
        pdf_handler: Reference to PDF handler for RAG
    """
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
    chat_session: Optional[any] = None
    pdf_handler: Optional['PDFHandler'] = None


class MumtahinGPT:
    """
    Main class for MumtahinGPT functionality using Gemini with chat context and RAG.
    
    This class manages the examination workflow including document analysis,
    question generation, answer evaluation, and final summary generation.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the MumtahinGPT with Gemini API.
        
        Args:
            api_key (str): Google Gemini API key
        """
        genai.configure(api_key=api_key)
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
        
        Args:
            message (str): Message to send
            system_context (str, optional): System context to prepend
            
        Returns:
            Tuple[str, Optional[str]]: (Response text, error message)
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
        """
        Check if all questions have been asked.
        
        Returns:
            bool: True if examination is complete
        """
        return self.state.current_question_index >= self.state.total_questions
    
    def set_total_questions(self, total: int):
        """
        Set the total number of questions for the examination.
        
        Args:
            total (int): Total number of questions (1-100)
        """
        if 1 <= total <= 100:
            self.state.total_questions = total
            self.state.lifelines_total = max(1, total // 3)
            self.state.lifelines_remaining = self.state.lifelines_total
    
    def use_lifeline(self, lifeline_type: str) -> bool:
        """
        Use a lifeline (rephrase or new question).
        
        Args:
            lifeline_type (str): 'rephrase' or 'new'
            
        Returns:
            bool: True if lifeline used successfully
        """
        if self.state.lifelines_remaining > 0:
            self.state.lifelines_remaining -= 1
            self.state.lifelines_used.append((self.state.current_question_index, lifeline_type))
            self.state.awaiting_lifeline_response = True
            self.state.last_lifeline_type = lifeline_type
            return True
        return False
    
    def get_lifelines_status(self) -> Tuple[int, int]:
        """
        Get lifelines status.
        
        Returns:
            Tuple[int, int]: (remaining, total)
        """
        return (self.state.lifelines_remaining, self.state.lifelines_total)
    
    def _get_generic_focus_areas(self) -> List[str]:
        """
        Get generic focus areas that work for any document type.
        
        Returns:
            List[str]: List of generic focus areas
        """
        return [
            "the main topic and central purpose — what is this document about and why does it matter?",
            "the scope and boundaries — what is included, what is excluded, and what are the limitations?",
            "the key points, arguments, or findings — what are the main claims, conclusions, or discoveries?",
            "the evidence, methods, or reasoning — how are conclusions supported and validated?",
            "the implications, significance, and future directions — what impact does this have and what comes next?"
        ]
    
    def analyze_document(self, document_text: str, document_title: str = "Unknown Document") -> Tuple[str, Optional[str]]:
        """
        Analyze the uploaded PDF document using RAG.
        
        Args:
            document_text (str): Extracted document text
            document_title (str): Title of the document
            
        Returns:
            Tuple[str, Optional[str]]: (Analysis text, error message)
        """
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
        """
        Generate dynamic focus areas based on document type and content using RAG.
        
        Returns:
            List[str]: List of focus areas for questions
        """
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
        """
        Generate the next examination question using RAG to avoid repetition.
        
        Returns:
            Tuple[Optional[str], Optional[str]]: (Question text, error message)
        """
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
        """
        Handle lifeline question generation using RAG.
        
        Returns:
            Tuple[Optional[str], Optional[str]]: (Question text, error message)
        """
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
        """
        Evaluate the user's answer using RAG for context.
        
        Args:
            user_answer (str): User's answer text
            
        Returns:
            Tuple[str, Optional[str]]: (Evaluation text, error message)
        """
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
        """
        Generate final examination summary using RAG for document overview.
        
        Returns:
            Tuple[str, Optional[str]]: (Summary text, error message)
        """
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
        """
        Get current progress.
        
        Returns:
            Tuple[int, int]: (current_question, total_questions)
        """
        return (self.state.current_question_index, self.state.total_questions)
    
    def get_session_data(self) -> Dict:
        """
        Get complete session data for export.
        
        Returns:
            Dict: Session data including questions, answers, marks, etc.
        """
        total_marks = sum(self.state.marks)
        max_marks = self.state.total_questions * 10
        percentage = (total_marks / max_marks * 100) if max_marks > 0 else 0
        
        return {
            'document_title': self.state.document_title,
            'document_type': self.state.document_type,
            'total_questions': self.state.total_questions,
            'questions': self.state.questions_asked,
            'answers': self.state.answers_given,
            'evaluations': self.state.evaluations,
            'marks': self.state.marks,
            'total_marks': total_marks,
            'max_marks': max_marks,
            'percentage': percentage,
            'status': 'PASS' if percentage >= 50 else 'FAIL',
            'lifelines_used': len(self.state.lifelines_used),
            'lifelines_total': self.state.lifelines_total,
            'final_evaluation': self.state.final_evaluation
        }


def create_examiner(api_key: str) -> MumtahinGPT:
    """
    Factory function to create a MumtahinGPT instance.
    
    Args:
        api_key (str): Google Gemini API key
        
    Returns:
        MumtahinGPT: Configured examiner instance
    """
    return MumtahinGPT(api_key)
