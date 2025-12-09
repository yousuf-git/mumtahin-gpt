"""
Examiner Logic Module
=====================
This module contains the core logic for the AI examiner functionality.
It handles question generation, answer evaluation, and conversation management
using Google's Gemini API.

Dependencies:
    - google.generativeai: For AI model interaction
"""

import os
import google.generativeai as genai
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field


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


class ExaminerAI:
    """
    Main class for the AI Examiner functionality.
    
    This class manages the examination process: analyzing documents,
    generating questions, and evaluating answers using Google Gemini.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the ExaminerAI with Gemini API credentials.
        
        Args:
            api_key (str): Google Gemini API key
        """
        genai.configure(api_key=api_key)
        
        # Multiple models for different tasks and fallback
        # Models ordered by rate limits (higher RPM = better for fallback)
        
        # Primary model for quick Q&A (10 RPM)
        self.primary_model = genai.GenerativeModel('gemini-2.5-flash')
        self.primary_model_name = "gemini-2.5-flash"
        
        # Fallback models in order of preference (by RPM)
        self.fallback_models = [
            (genai.GenerativeModel('gemini-2.0-flash-lite'), "gemini-2.0-flash-lite", "30 RPM"),
            (genai.GenerativeModel('gemini-2.5-flash-lite'), "gemini-2.5-flash-lite", "15 RPM"),
            (genai.GenerativeModel('gemini-2.0-flash'), "gemini-2.0-flash", "15 RPM"),
        ]
        
        # Premium model for final evaluation (3 RPM - most powerful)
        self.premium_model = genai.GenerativeModel('gemini-2.5-pro')
        self.premium_model_name = "gemini-2.5-pro"
        
        # Track current model being used
        self.current_model_name = self.primary_model_name
        
        # Conversation state
        self.state = ConversationState()
        
        # System personality
        self.examiner_personality = """You are a professional academic examiner with a friendly yet formal demeanor.
Your role is to:
- Ask insightful questions about documents
- Evaluate answers constructively
- Provide specific, actionable feedback
- Acknowledge good answers without over-praising
- Be encouraging but maintain academic rigor
Keep responses concise and focused."""
    
    def _generate_with_fallback(self, prompt: str, use_premium: bool = False) -> Tuple[str, Optional[str]]:
        """
        Generate content with automatic fallback to alternative models.
        
        Args:
            prompt (str): The prompt to send to the model
            use_premium (bool): Whether to use the premium model first
            
        Returns:
            Tuple[str, Optional[str]]: (generated_text, error_message)
        """
        if use_premium:
            models_to_try = [(self.premium_model, self.premium_model_name, "3 RPM")]
        else:
            models_to_try = [(self.primary_model, self.primary_model_name, "15 RPM")] + self.fallback_models
        
        last_error = None
        for i, (model, model_name, rpm_limit) in enumerate(models_to_try):
            try:
                self.current_model_name = model_name  # Track current model
                response = model.generate_content(prompt)
                return response.text, None
            except Exception as e:
                error_str = str(e)
                last_error = error_str
                
                # Check if it's a rate limit error
                if "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower():
                    if i < len(models_to_try) - 1:
                        # Try next model
                        next_model_name = models_to_try[i + 1][1]
                        continue
                    else:
                        return "", f"⚠️ **Rate Limit Reached** - All available models have hit their rate limits. Please wait a moment and try again.\n\n*Tip: The models have limits of {rpm_limit} requests per minute.*"
                
                # Check if it's a model not found error
                elif "404" in error_str or "not found" in error_str.lower():
                    if i < len(models_to_try) - 1:
                        continue
                    else:
                        return "", "⚠️ **Model Error** - The AI model is temporarily unavailable. Please try again."
                
                # Other errors
                else:
                    if i < len(models_to_try) - 1:
                        continue
                    else:
                        return "", f"⚠️ **AI Error** - An unexpected error occurred: {error_str}"
        
        return "", f"⚠️ **Service Unavailable** - Unable to connect to AI service. Error: {last_error}"
    
    def get_current_model(self) -> str:
        """
        Get the name of the currently active model.
        
        Returns:
            str: Current model name
        """
        return self.current_model_name
    
    def is_examination_complete(self) -> bool:
        """
        Check if all questions have been asked.
        
        Returns:
            bool: True if all questions have been asked
        """
        return self.state.current_question_index >= self.state.total_questions
    
    def set_total_questions(self, total: int):
        """
        Set the total number of questions for the examination.
        
        Args:
            total (int): Number of questions (1-10)
        """
        if 1 <= total <= 10:
            self.state.total_questions = total
            # Calculate lifelines (20% of total questions, minimum 1)
            self.state.lifelines_total = max(1, int(total * 0.2))
            self.state.lifelines_remaining = self.state.lifelines_total
    
    def use_lifeline(self, lifeline_type: str) -> bool:
        """
        Use a lifeline (rephrase or new question).
        
        Args:
            lifeline_type (str): 'rephrase' or 'new'
            
        Returns:
            bool: True if lifeline was used successfully
        """
        if self.state.lifelines_remaining > 0:
            self.state.lifelines_remaining -= 1
            self.state.lifelines_used.append((self.state.current_question_index - 1, lifeline_type))
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
            List[str]: Generic focus areas
        """
        return [
            "the main topic and central purpose — what is this document about and why does it matter?",
            "the scope and boundaries — what is included, what is excluded, and what are the limitations?",
            "the key points, arguments, or findings — what are the main claims, conclusions, or discoveries?",
            "the evidence, methods, or reasoning — how are conclusions supported and validated?",
            "the implications, significance, and future directions — what impact does this have and what comes next?"
        ]
    
    def _generate_focus_areas_from_document(self) -> Tuple[List[str], Optional[str]]:
        """
        Generate dynamic focus areas based on document type and content.
        
        Returns:
            Tuple[List[str], Optional[str]]: (focus_areas, error_message)
        """
        prompt = f"""{self.examiner_personality}

You are preparing examination questions for a student who has READ this document.

Document Type: {self.state.document_type}
Document Content (excerpt):
{self.state.document_text[:2500]}...

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

Examples by document type:
- Research paper: "the research methodology and experimental design", "the results and their interpretation"
- Proposal: "the problem being addressed and its significance", "the proposed solution and approach"
- Tutorial: "the step-by-step implementation process", "the practical applications and use cases"
- Topic: "the fundamental concepts and definitions", "the real-world examples and applications"

Format as a numbered list:
1. [Content aspect to examine]
2. [Content aspect to examine]
3. [Content aspect to examine]
4. [Content aspect to examine]
5. [Content aspect to examine]

Focus on understanding the CONTENT, not analyzing the document structure."""

        response, error = self._generate_with_fallback(prompt)
        
        if error or not response:
            # Fallback to generic areas
            return self._get_generic_focus_areas(), error
        
        # Parse the numbered list
        import re
        lines = response.strip().split('\n')
        focus_areas = []
        
        for line in lines:
            # Match patterns like "1.", "1)", "1 -", etc.
            match = re.match(r'^\d+[\.\)\-\:]\s*(.+)$', line.strip())
            if match:
                focus_areas.append(match.group(1).strip())
        
        # If we didn't get 5 areas, use generic ones
        if len(focus_areas) < 5:
            return self._get_generic_focus_areas(), None
        
        return focus_areas[:5], None  # Take first 5 if more than 5
    
    def analyze_document(self, document_text: str, document_title: str = "Unknown Document") -> Tuple[str, Optional[str]]:
        """
        Analyze the uploaded PDF document to understand its content and determine focus areas.
        
        Args:
            document_text (str): Extracted text from the PDF
            document_title (str): Title of the document
            
        Returns:
            Tuple[str, Optional[str]]: (analysis_summary, error_message)
        """
        self.state.document_text = document_text
        self.state.document_title = document_title
        
        # First, analyze and classify the document
        prompt = f"""{self.examiner_personality}

You are analyzing a document to prepare for an examination. Identify the document type and provide a brief summary.

Document Title: {document_title}
Document Content:
{document_text[:3000]}...

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

        analysis, error = self._generate_with_fallback(prompt)
        
        if analysis:
            self.state.document_analysis = analysis
            
            # Extract document type from analysis
            import re
            type_match = re.search(r'\*\*Type:\*\*\s*(\w+)', analysis)
            if type_match:
                self.state.document_type = type_match.group(1).lower()
            else:
                self.state.document_type = "general"
            
            # Generate dynamic focus areas based on document type
            focus_areas, focus_error = self._generate_focus_areas_from_document()
            self.state.focus_areas = focus_areas
            
            # If focus area generation failed but document analysis succeeded, 
            # don't return the error (we have fallback areas)
            if not error:
                error = None
        
        return analysis, error
    
    def generate_next_question(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate the next examination question based on the document.
        
        Returns:
            Tuple[Optional[str], Optional[str]]: (question, error_message)
        """
        if self.state.current_question_index >= self.state.total_questions:
            return None, None
        
        # Check if this is a lifeline request
        if self.state.awaiting_lifeline_response and self.state.last_lifeline_type:
            return self._handle_lifeline_question()
        
        # Use dynamically generated focus areas, or fallback to generic ones
        if not self.state.focus_areas:
            self.state.focus_areas = self._get_generic_focus_areas()
        
        # Select focus area for current question
        # If more questions than focus areas, cycle through or use the last one
        focus_index = min(self.state.current_question_index, len(self.state.focus_areas) - 1)
        current_focus = self.state.focus_areas[focus_index]
        
        # Build context from previous Q&A
        previous_context = ""
        if self.state.questions_asked:
            previous_context = "\n\nPrevious Q&A:\n"
            for i, (q, a) in enumerate(zip(self.state.questions_asked, self.state.answers_given)):
                previous_context += f"Q{i+1}: {q}\nA{i+1}: {a}\n\n"
        
        prompt = f"""{self.examiner_personality}

Document Type: {self.state.document_type}

Document Content:
{self.state.document_text[:2000]}...

{previous_context}

Generate ONE examination question that tests the student's understanding of {current_focus}

IMPORTANT RULES:
- Ask about the PROJECT/TOPIC content, NOT about document formatting or metadata
- Do NOT ask about student names, IDs, submission details, or page layout
- Focus on the SUBJECT MATTER: concepts, methodology, design, implementation, etc.
- The student should demonstrate they READ and UNDERSTOOD the content
- Be clear and direct
- Require thoughtful analysis based on the content

Example GOOD questions:
- "Explain the main objectives of the proposed system"
- "What methodology is used and why is it appropriate?"
- "Describe the key features and their benefits"

Example BAD questions (NEVER ask these):
- "What is the project ID?"
- "Who submitted this document?"
- "Analyze the adequacy of identifying information on Page 1"

Respond with ONLY the question, no additional text."""

        question, error = self._generate_with_fallback(prompt)
        if question:
            self.state.questions_asked.append(question.strip())
            self.state.current_question_index += 1
        
        return question.strip() if question else None, error
    
    def _handle_lifeline_question(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Handle lifeline request (rephrase or new question).
        
        Returns:
            Tuple[Optional[str], Optional[str]]: (question, error_message)
        """
        self.state.awaiting_lifeline_response = False
        
        if self.state.last_lifeline_type == "rephrase":
            # Rephrase the last question
            last_question = self.state.questions_asked[-1] if self.state.questions_asked else ""
            
            prompt = f"""{self.examiner_personality}

Original question: {last_question}

Document excerpt:
{self.state.document_text[:2000]}...

Rephrase this question to make it clearer and easier to understand while maintaining the same focus.
Keep it simple and direct.

Respond with ONLY the rephrased question, no additional text."""

            question, error = self._generate_with_fallback(prompt)
            if question:
                # Replace the last question with rephrased one
                self.state.questions_asked[-1] = question.strip()
            
            self.state.last_lifeline_type = ""
            return question.strip() if question else None, error
            
        elif self.state.last_lifeline_type == "new":
            # Generate a completely new question on a different topic
            # Decrement question index since we're replacing the current question
            if self.state.current_question_index > 0:
                self.state.current_question_index -= 1
            
            # Remove the last question
            if self.state.questions_asked:
                self.state.questions_asked.pop()
            
            # Generate new question
            self.state.last_lifeline_type = ""
            return self.generate_next_question()
        
        return None, None
    
    def evaluate_answer(self, user_answer: str) -> Tuple[str, Optional[str]]:
        """
        Evaluate the user's answer and provide constructive feedback with marks.
        
        Args:
            user_answer (str): The user's answer to the current question
            
        Returns:
            Tuple[str, Optional[str]]: (evaluation_with_marks, error_message)
        """
        if not self.state.questions_asked:
            return "No question has been asked yet.", None
        
        current_question = self.state.questions_asked[-1]
        self.state.answers_given.append(user_answer)
        
        # Build context
        document_excerpt = self.state.document_text[:2000]
        
        prompt = f"""{self.examiner_personality}

Document excerpt:
{document_excerpt}...

Question asked: {current_question}

Student's answer: {user_answer}

Evaluate this answer and provide:
1. A score out of 10 based on:
   - Relevance to the question (3 points)
   - Depth of understanding (3 points)
   - Use of document content (2 points)
   - Clarity of expression (2 points)

2. Brief feedback (2-3 sentences):
   - If score is 7+: Acknowledge strengths
   - If score is 4-6: Point out what's good and what needs improvement
   - If score is 0-3: Provide specific guidance for improvement

Format your response EXACTLY as:
**Marks: X/10**

[Your feedback here]

Be fair and constructive. Keep feedback concise."""

        evaluation, error = self._generate_with_fallback(prompt)
        if evaluation:
            # Extract marks from evaluation
            import re
            marks_match = re.search(r'\*\*Marks:\s*(\d+)/10\*\*', evaluation)
            if marks_match:
                marks = int(marks_match.group(1))
                self.state.marks.append(marks)
            else:
                # Default to 5 if marks not found
                self.state.marks.append(5)
                evaluation = "**Marks: 5/10**\n\n" + evaluation
            
            self.state.evaluations.append(evaluation.strip())
        
        return evaluation.strip() if evaluation else "", error
    
    def generate_final_summary(self) -> Tuple[str, Optional[str]]:
        """
        Generate a final overall evaluation summary using the premium model.
        
        Returns:
            Tuple[str, Optional[str]]: (summary_with_total_marks, error_message)
        """
        if not self.state.questions_asked:
            return "No questions were asked during this session.", None
        
        # Calculate total marks and percentage
        total_marks = sum(self.state.marks)
        max_marks = len(self.state.marks) * 10
        percentage = (total_marks / max_marks * 100) if max_marks > 0 else 0
        status = "PASS ✅" if percentage >= 50 else "FAIL ❌"
        
        qa_summary = ""
        for i, (q, a, e, m) in enumerate(zip(
            self.state.questions_asked,
            self.state.answers_given,
            self.state.evaluations,
            self.state.marks
        ), 1):
            qa_summary += f"\n**Q{i}:** {q}\n**A{i}:** {a[:100]}...\n**Evaluation:** {e}\n**Marks:** {m}/10\n"
        
        prompt = f"""{self.examiner_personality}

Document: {self.state.document_analysis}

Complete Q&A Session:
{qa_summary}

Total Score: {total_marks}/{max_marks} ({percentage:.1f}%)

Provide a final overall evaluation (4-5 sentences) covering:
- Overall understanding demonstrated
- Strengths shown
- Areas for improvement
- Final assessment

Be constructive and encouraging while maintaining academic standards."""

        # Use premium model for final summary
        summary, error = self._generate_with_fallback(prompt, use_premium=True)
        
        if summary:
            # Store final evaluation
            self.state.final_evaluation = summary.strip()
            
            # Add marks summary at the beginning
            marks_summary = f"""**📊 EXAMINATION RESULTS**

**Total Marks:** {total_marks}/{max_marks} ({percentage:.1f}%)
**Status:** {status}

---

**Final Evaluation:**

{summary}"""
            return marks_summary, error
        
        return "", error
    
    def reset(self):
        """Reset the conversation state for a new document."""
        self.state = ConversationState()
    
    def reset_state(self):
        """Alias for reset() method for backward compatibility."""
        self.reset()
    
    def get_progress(self) -> Tuple[int, int]:
        """
        Get the current progress of the examination.
        
        Returns:
            Tuple[int, int]: (current_question, total_questions)
        """
        return (self.state.current_question_index, self.state.total_questions)
    
    def get_session_data(self) -> Dict:
        """
        Get complete session data for report generation.
        
        Returns:
            Dict: Session data including all Q&A, marks, and metadata
        """
        total_marks = sum(self.state.marks)
        max_marks = len(self.state.marks) * 10
        percentage = (total_marks / max_marks * 100) if max_marks > 0 else 0
        status = "PASS" if percentage >= 50 else "FAIL"
        
        return {
            'document_title': self.state.document_title,
            'document_analysis': self.state.document_analysis,
            'total_questions': self.state.total_questions,
            'questions': self.state.questions_asked,
            'answers': self.state.answers_given,
            'evaluations': self.state.evaluations,
            'marks': self.state.marks,
            'total_marks': total_marks,
            'max_marks': max_marks,
            'percentage': percentage,
            'status': status,
            'final_evaluation': self.state.final_evaluation,
            'lifelines_used': len(self.state.lifelines_used),
            'lifelines_total': self.state.lifelines_total
        }


# Utility function for easy initialization
def create_examiner(api_key: Optional[str] = None) -> ExaminerAI:
    """
    Create an ExaminerAI instance with API key from environment or parameter.
    
    Args:
        api_key (Optional[str]): API key, or None to use environment variable
        
    Returns:
        ExaminerAI: Initialized examiner instance
    """
    if api_key is None:
        api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        raise ValueError("Gemini API key not found. Set GEMINI_API_KEY environment variable.")
    
    return ExaminerAI(api_key)
