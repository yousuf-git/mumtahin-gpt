"""
Examiner AI - Gradio Application
=================================
Main application file that creates the interactive Gradio interface
for the AI-powered document examiner chatbot.

This module integrates the PDF handler and examiner logic to provide
a seamless user experience.
"""

import os
import gradio as gr
from dotenv import load_dotenv
from backups.pdf_handler import PDFHandler
from backups.examiner_logic import create_examiner, ExaminerAI
from typing import List, Tuple, Optional
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import tempfile

# Load environment variables
load_dotenv()

# Global state
examiner: Optional[ExaminerAI] = None
pdf_handler: PDFHandler = PDFHandler()
session_active: bool = False


def initialize_app() -> str:
    """
    Initialize the application and check for API key.
    
    Returns:
        str: Status message
    """
    try:
        global examiner
        api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            return "⚠️ Error: GEMINI_API_KEY not found. Please set it in your .env file."
        
        examiner = create_examiner(api_key)
        return "✅ Application initialized successfully!"
    except Exception as e:
        return f"⚠️ Error initializing application: {str(e)}"


def process_pdf(pdf_file, num_questions: int) -> Tuple[str, str, str, str, str]:
    """
    Process uploaded PDF file and start the examination.
    
    Args:
        pdf_file: Uploaded PDF file from Gradio
        num_questions: Number of questions for the examination
        
    Returns:
        Tuple[str, str, str, str, str]: (Status message, initial chat message, error notification, model info, lifelines status)
    """
    global session_active
    
    if pdf_file is None:
        return "Please upload a PDF file.", "", "", "", ""
    
    try:
        # Extract text from PDF
        pdf_path = pdf_file.name
        
        # Get filename without extension for document title
        import os
        document_title = os.path.splitext(os.path.basename(pdf_path))[0]
        
        extracted_text = pdf_handler.extract_text(pdf_path)
        
        if not extracted_text or not pdf_handler.validate_content():
            return "❌ Error: Could not extract sufficient text from PDF. Please check if the PDF contains readable text.", "", "", "", ""
        
        # Get document summary
        summary = pdf_handler.get_summary()
        
        # Set total questions
        examiner.set_total_questions(num_questions)
        
        # Get lifelines status
        lifelines_remaining, lifelines_total = examiner.get_lifelines_status()
        
        # Analyze document with AI
        analysis, analysis_error = examiner.analyze_document(extracted_text, document_title)
        
        if analysis_error:
            return "❌ Analysis Failed", "", analysis_error, "", ""
        
        session_active = True
        
        # Generate first question
        first_question, question_error = examiner.generate_next_question()
        
        if question_error:
            session_active = False
            return "❌ Question Generation Failed", "", question_error, "", ""
        
        # Get current model info
        current_model = examiner.get_current_model()
        model_info = f"🤖 **Current AI Model:** {current_model}"
        
        lifelines_status = f"🎯 **Lifelines Available:** {lifelines_remaining}/{lifelines_total}"
        
        # Get document type and format it nicely
        doc_type = examiner.state.document_type
        doc_type_display = doc_type.replace('_', ' ').title()
        
        # Extract just the summary text (remove Type prefix if present)
        import re
        summary_match = re.search(r'\*\*Summary:\*\*\s*(.+?)(?:\n|$)', analysis, re.DOTALL)
        if summary_match:
            clean_summary = summary_match.group(1).strip()
            # Remove any remaining type mentions
            clean_summary = re.sub(r'\*\*Type:\*\*[^\n]+\n?', '', clean_summary).strip()
        else:
            clean_summary = analysis
        
        status_msg = f"""✅ **PDF Processed Successfully!**
        
📄 **Document Info:**
- Title: {document_title}
- Type: {doc_type_display}
- Pages: {summary.get('pages', 'N/A')}
- Words: {summary.get('word_count', 'N/A')}
- Total Questions: {num_questions}
- Lifelines: {lifelines_remaining}/{lifelines_total}

📋 **Summary:**
{clean_summary}

---
**The examination will now begin. Please answer each question thoughtfully.**
"""
        
        # Initial chat message with first question
        initial_chat = f"**Examiner:** {first_question}"
        
        return status_msg, initial_chat, "", model_info, lifelines_status
        
    except Exception as e:
        return f"❌ Error processing PDF: {str(e)}", "", "", "", ""


def chat_with_examiner(message: str, history: List) -> Tuple[List, str, str, str, str, bool]:
    """
    Handle conversation with the AI examiner.
    
    Args:
        message: User's answer/message
        history: Chat history as list of [user, assistant] pairs
        
    Returns:
        Tuple[List, str, str, str, str, bool]: (Updated history, cleared input, error notification, model info, lifelines status, show_retry)
    """
    global session_active
    
    if not session_active:
        error_msg = "⚠️ Please upload and analyze a PDF document first."
        return history, message, error_msg, "", "", False
    
    if not message.strip():
        current_model = examiner.get_current_model()
        lifelines_remaining, lifelines_total = examiner.get_lifelines_status()
        return history, message, "", f"🤖 **Current AI Model:** {current_model}", f"🎯 **Lifelines:** {lifelines_remaining}/{lifelines_total}", False
    
    # Add user message to history
    history.append([message, None])
    
    try:
        # First, always evaluate the current answer
        evaluation, eval_error = examiner.evaluate_answer(message)
        
        if eval_error:
            lifelines_remaining, lifelines_total = examiner.get_lifelines_status()
            # Remove the user message from history since we got an error
            history.pop()
            return history, message, eval_error, f"🤖 **Current AI Model:** {examiner.get_current_model()}", f"🎯 **Lifelines:** {lifelines_remaining}/{lifelines_total}", True
        
        # Check if this was the last question (after evaluation)
        if examiner.is_examination_complete():
            # Generate final summary
            final_summary, summary_error = examiner.generate_final_summary()
            
            if summary_error:
                lifelines_remaining, lifelines_total = examiner.get_lifelines_status()
                return history, "", summary_error, f"🤖 **Current AI Model:** {examiner.get_current_model()}", f"🎯 **Lifelines:** {lifelines_remaining}/{lifelines_total}", True
            
            session_active = False
            # Show evaluation of last answer, then final summary
            response = f"{evaluation}\n\n---\n\n{final_summary}\n\n---\n✅ **Examination Complete!** You can now export the report or upload a new PDF to start another session."
            history[-1][1] = f"**Examiner:** {response}"
            lifelines_remaining, lifelines_total = examiner.get_lifelines_status()
            return history, "", "", f"🤖 **Final Evaluation Model:** {examiner.get_current_model()}", f"🎯 **Lifelines Used:** {lifelines_total - lifelines_remaining}/{lifelines_total}", False
        
        # Generate next question (only if not complete)
        next_question, question_error = examiner.generate_next_question()
        
        if question_error:
            lifelines_remaining, lifelines_total = examiner.get_lifelines_status()
            return history, "", question_error, f"🤖 **Current AI Model:** {examiner.get_current_model()}", f"🎯 **Lifelines:** {lifelines_remaining}/{lifelines_total}", True
        
        # Combine evaluation and next question
        response = f"{evaluation}\n\n---\n**Next Question:**\n{next_question}"
        history[-1][1] = f"**Examiner:** {response}"
        
        # Get current model info and lifelines
        current_model = examiner.get_current_model()
        model_info = f"🤖 **Current AI Model:** {current_model}"
        lifelines_remaining, lifelines_total = examiner.get_lifelines_status()
        lifelines_info = f"🎯 **Lifelines:** {lifelines_remaining}/{lifelines_total}"
        
        return history, "", "", model_info, lifelines_info, False
        
    except Exception as e:
        error_msg = f"❌ An unexpected error occurred: {str(e)}"
        lifelines_remaining, lifelines_total = examiner.get_lifelines_status()
        # Remove the user message from history since we got an error
        history.pop()
        return history, message, error_msg, f"🤖 **Current AI Model:** {examiner.get_current_model()}", f"🎯 **Lifelines:** {lifelines_remaining}/{lifelines_total}", True


def use_lifeline(lifeline_type: str, history: List) -> Tuple[List, str, str, str]:
    """
    Handle lifeline usage (rephrase or new question).
    
    Args:
        lifeline_type: 'rephrase' or 'new'
        history: Chat history
        
    Returns:
        Tuple[List, str, str, str]: (Updated history, error, model info, lifelines status)
    """
    if not session_active:
        return history, "⚠️ Please start an examination first.", "", ""
    
    # Check if lifelines are available
    lifelines_remaining, lifelines_total = examiner.get_lifelines_status()
    
    if lifelines_remaining <= 0:
        return history, "⚠️ No lifelines remaining!", f"🤖 **Current AI Model:** {examiner.get_current_model()}", f"🎯 **Lifelines:** 0/{lifelines_total}"
    
    # Use the lifeline
    if not examiner.use_lifeline(lifeline_type):
        return history, "⚠️ Failed to use lifeline.", f"🤖 **Current AI Model:** {examiner.get_current_model()}", f"🎯 **Lifelines:** {lifelines_remaining}/{lifelines_total}"
    
    try:
        # Generate new/rephrased question
        question, error = examiner.generate_next_question()
        
        if error:
            return history, error, f"🤖 **Current AI Model:** {examiner.get_current_model()}", f"🎯 **Lifelines:** {lifelines_remaining-1}/{lifelines_total}"
        
        # Add to history
        lifeline_msg = "🔄 **Rephrased Question**" if lifeline_type == "rephrase" else "🆕 **New Question**"
        history.append([None, f"**Examiner:** {lifeline_msg}\n\n{question}"])
        
        # Update lifelines status
        lifelines_remaining, lifelines_total = examiner.get_lifelines_status()
        
        return history, "", f"🤖 **Current AI Model:** {examiner.get_current_model()}", f"🎯 **Lifelines:** {lifelines_remaining}/{lifelines_total}"
        
    except Exception as e:
        lifelines_remaining, lifelines_total = examiner.get_lifelines_status()
        return history, f"❌ Error: {str(e)}", f"🤖 **Current AI Model:** {examiner.get_current_model()}", f"🎯 **Lifelines:** {lifelines_remaining}/{lifelines_total}"


def reset_session() -> Tuple[str, List, str, str, str, str, bool]:
    """
    Reset the examination session.
    
    Returns:
        Tuple[str, List, str, str, str, str, bool]: (Status message, empty history, cleared input, cleared error, cleared model info, cleared lifelines, hide_retry)
    """
    global session_active
    
    examiner.reset_state()
    pdf_handler.reset()
    session_active = False
    
    return "✅ Session reset successfully. Upload a new PDF to begin.", [], "", "", "", "", False


def retry_last_action(message: str, history: List) -> Tuple[List, str, str, str, str, bool]:
    """
    Retry the last failed action.
    
    Args:
        message: The last user message that failed
        history: Current chat history
        
    Returns:
        Tuple[List, str, str, str, str, bool]: (Updated history, cleared input, error notification, model info, lifelines status, show_retry)
    """
    # Simply call chat_with_examiner again with the same message
    return chat_with_examiner(message, history)


def export_report() -> Tuple[str, Optional[str]]:
    """
    Export the examination session as a PDF report.
    
    Returns:
        Tuple[str, Optional[str]]: (file_path, error_message)
    """
    if not session_active and not examiner.state.questions_asked:
        return None, "⚠️ No session data available. Complete an examination first."
    
    try:
        # Get session data
        session_data = examiner.get_session_data()
        
        # Create meaningful filename
        doc_title = session_data['document_title'].replace(' ', '_')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"Examination_Report_{doc_title}_{timestamp}.pdf"
        
        # Create temporary PDF file with meaningful name
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, filename)
        
        # Create PDF document
        doc = SimpleDocTemplate(temp_path, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        story = []
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2196F3'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1976D2'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )
        
        normal_style = styles['Normal']
        normal_style.fontSize = 10
        normal_style.leading = 14
        
        # Title
        story.append(Paragraph("🎓 EXAMINATION REPORT", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Document Information
        story.append(Paragraph("📄 Document Information", heading_style))
        doc_info = [
            ['Document Title:', session_data['document_title']],
            ['Examination Date:', datetime.now().strftime('%B %d, %Y at %H:%M')],
            ['Total Questions:', str(session_data['total_questions'])],
        ]
        doc_table = Table(doc_info, colWidths=[2*inch, 4*inch])
        doc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E3F2FD')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        story.append(doc_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Results Summary
        story.append(Paragraph("📊 Results Summary", heading_style))
        percentage = session_data['percentage']
        status = session_data['status']
        status_color = colors.green if status == 'PASS' else colors.red
        
        results = [
            ['Total Marks:', f"{session_data['total_marks']}/{session_data['max_marks']}"],
            ['Percentage:', f"{percentage:.1f}%"],
            ['Status:', status],
            ['Lifelines Used:', f"{session_data['lifelines_used']}/{session_data['lifelines_total']}"],
        ]
        results_table = Table(results, colWidths=[2*inch, 4*inch])
        results_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F5E9' if status == 'PASS' else '#FFEBEE')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('TEXTCOLOR', (1, 2), (1, 2), status_color),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 2), (1, 2), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        story.append(results_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Overall Evaluation
        if session_data.get('final_evaluation'):
            story.append(Paragraph("🎓 Overall Evaluation", heading_style))
            eval_text = session_data['final_evaluation'].replace('**', '')
            story.append(Paragraph(eval_text, normal_style))
            story.append(Spacer(1, 0.3*inch))
        
        # Question-wise Breakdown
        story.append(Paragraph("📝 Question-wise Performance", heading_style))
        
        for i, (question, answer, evaluation, mark) in enumerate(zip(
            session_data['questions'],
            session_data['answers'],
            session_data['evaluations'],
            session_data['marks']
        ), 1):
            # Question
            story.append(Paragraph(f"<b>Question {i}:</b>", normal_style))
            story.append(Paragraph(question, normal_style))
            story.append(Spacer(1, 0.1*inch))
            
            # Answer
            story.append(Paragraph(f"<b>Your Answer:</b>", normal_style))
            story.append(Paragraph(answer, normal_style))
            story.append(Spacer(1, 0.1*inch))
            
            # Evaluation and Marks
            story.append(Paragraph(f"<b>Evaluation:</b>", normal_style))
            eval_clean = evaluation.replace('**', '')
            story.append(Paragraph(eval_clean, normal_style))
            
            # Marks box
            mark_color = colors.green if mark >= 7 else colors.orange if mark >= 4 else colors.red
            marks_table = Table([[f"Marks: {mark}/10"]], colWidths=[6*inch])
            marks_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), mark_color),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(marks_table)
            story.append(Spacer(1, 0.2*inch))
            
            if i < len(session_data['questions']):
                story.append(Spacer(1, 0.1*inch))
        
        # Build PDF
        doc.build(story)
        
        return temp_path, None
        
    except Exception as e:
        return None, f"⚠️ Error generating report: {str(e)}"


# Custom CSS for better appearance
custom_css = """
#main_container {
    max-width: 1200px;
    margin: auto;
}

.gradio-container {
    font-family: 'Inter', sans-serif;
}

#chatbot {
    height: 500px;
}

/* Status box styling with dark background */
#status_box {
    border-left: 4px solid #2196F3 !important;
    padding: 15px !important;
    background-color: #1e3a5f !important;
    border-radius: 5px !important;
    color: #e3f2fd !important;
}

#status_box * {
    color: #e3f2fd !important;
    background-color: transparent !important;
}

/* Error notification styling */
#error_notification {
    padding: 12px 16px !important;
    margin-bottom: 15px !important;
    border-radius: 8px !important;
    font-size: 14px !important;
    line-height: 1.5 !important;
    background-color: #ffebee !important;
    border-left: 4px solid #f44336 !important;
    color: #c62828 !important;
    display: block !important;
}

#error_notification:empty {
    display: none !important;
    padding: 0 !important;
    margin: 0 !important;
}

#error_notification * {
    color: #c62828 !important;
    background-color: transparent !important;
}

/* Model indicator styling */
#model_indicator {
    padding: 10px 16px !important;
    margin-bottom: 15px !important;
    border-radius: 8px !important;
    font-size: 14px !important;
    background-color: #1a237e !important;
    border-left: 4px solid #2196f3 !important;
    color: #bbdefb !important;
    font-weight: 500 !important;
}

#model_indicator:empty {
    display: none !important;
    padding: 0 !important;
    margin: 0 !important;
}

#model_indicator * {
    color: #bbdefb !important;
    background-color: transparent !important;
}

/* Lifelines status styling */
#lifelines_status {
    padding: 10px 16px !important;
    margin-bottom: 15px !important;
    border-radius: 8px !important;
    font-size: 14px !important;
    background-color: #4a2c2a !important;
    border-left: 4px solid #ff9800 !important;
    color: #ffe0b2 !important;
    font-weight: 500 !important;
}

#lifelines_status:empty {
    display: none !important;
    padding: 0 !important;
    margin: 0 !important;
}

#lifelines_status * {
    color: #ffe0b2 !important;
    background-color: transparent !important;
}

.header {
    text-align: center;
    padding: 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 10px;
    margin-bottom: 20px;
}

/* Completely hide all pending/loading states from status components */
#status_box .pending,
#model_indicator .pending,
#lifelines_status .pending,
#error_notification .pending,
#status_box .wrap.pending,
#model_indicator .wrap.pending,
#lifelines_status .wrap.pending,
#error_notification .wrap.pending {
    display: none !important;
}
"""

# Build the Gradio interface
def create_interface():
    """Create and configure the Gradio interface."""
    
    with gr.Blocks(
        css=custom_css, 
        theme=gr.themes.Soft(), 
        title="Examiner AI",
        head="""
        <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><defs><linearGradient id='grad' x1='0%25' y1='0%25' x2='100%25' y2='100%25'><stop offset='0%25' style='stop-color:%23667eea;stop-opacity:1' /><stop offset='100%25' style='stop-color:%23764ba2;stop-opacity:1' /></linearGradient></defs><circle cx='50' cy='50' r='48' fill='url(%23grad)'/><g transform='translate(50, 50)'><polygon points='-25,-10 25,-10 30,-5 -30,-5' fill='%23ffffff'/><rect x='-15' y='-5' width='30' height='8' fill='%23ffffff'/><line x1='25' y1='-10' x2='30' y2='-20' stroke='%23ffd700' stroke-width='2'/><circle cx='30' cy='-22' r='3' fill='%23ffd700'/><rect x='-12' y='5' width='24' height='18' rx='2' fill='%23ffffff'/><line x1='-8' y1='10' x2='8' y2='10' stroke='%23667eea' stroke-width='2'/><line x1='-8' y1='14' x2='8' y2='14' stroke='%23667eea' stroke-width='2'/><line x1='-8' y1='18' x2='5' y2='18' stroke='%23667eea' stroke-width='2'/></g></svg>">
        """
    ) as demo:
        
        # Header
        gr.HTML("""
            <div class="header">
                <h1>🎓 Examiner AI</h1>
                <p>Upload your document and answer questions from your AI examiner</p>
            </div>
        """)
        
        with gr.Row():
            # Left column - PDF upload and info
            with gr.Column(scale=1):
                gr.Markdown("## 📤 Upload Document")
                
                pdf_input = gr.File(
                    label="Upload PDF Document",
                    file_types=[".pdf"],
                    type="filepath"
                )
                
                # Number of questions selector
                num_questions = gr.Slider(
                    minimum=1,
                    maximum=10,
                    value=5,
                    step=1,
                    label="Number of Questions",
                    info="Select how many questions you want (1-10)"
                )
                
                process_btn = gr.Button("📊 Analyze & Start Examination", variant="primary", size="lg")
                
                status_output = gr.Markdown(
                    "👋 Welcome! Upload a PDF document to begin the examination.",
                    elem_id="status_box"
                )
                
                gr.Markdown("---")
                
                # Export and Reset buttons
                with gr.Row():
                    export_btn = gr.Button("📄 Export Report", variant="secondary", size="sm")
                    reset_btn = gr.Button("🔄 Reset Session", variant="secondary", size="sm")
                
                # Hidden file output for download
                report_file = gr.File(label="Download Report", visible=False)
                
                gr.Markdown("""
                ### 📋 How it works:
                1. **Upload** your PDF document
                2. **Select** number of questions (1-10)
                3. **Answer** questions asked by the AI
                4. **Receive** feedback with marks (out of 10)
                5. **Export** final report with results
                
                ### 💡 Grading:
                - **50%+ = PASS ✅**
                - **Below 50% = FAIL ❌**
                - Each question is marked out of 10
                """)
            
            # Right column - Chat interface
            with gr.Column(scale=2):
                gr.Markdown("## 💬 Examination Chat")
                
                # Model indicator area
                model_indicator = gr.Markdown(
                    "",
                    visible=True,
                    elem_id="model_indicator"
                )
                
                # Lifelines status
                lifelines_status = gr.Markdown(
                    "",
                    visible=True,
                    elem_id="lifelines_status"
                )
                
                # Error notification area
                error_notification = gr.Markdown(
                    "",
                    visible=True,
                    elem_id="error_notification"
                )
                
                # Retry button (hidden by default)
                retry_btn = gr.Button("🔄 Retry", variant="stop", visible=False, size="sm")
                
                chatbot = gr.Chatbot(
                    label="Conversation with Examiner",
                    height=500,
                    bubble_full_width=False,
                    elem_id="chatbot"
                )
                
                # Lifeline buttons
                with gr.Row():
                    rephrase_btn = gr.Button("🔄 Rephrase Question", variant="secondary", size="sm")
                    new_question_btn = gr.Button("🆕 New Question", variant="secondary", size="sm")
                
                with gr.Row():
                    msg_input = gr.Textbox(
                        label="Your Answer",
                        placeholder="Type your answer here and press Enter...",
                        lines=3,
                        scale=4
                    )
                    submit_btn = gr.Button("Send", variant="primary", scale=1)
        
        # Footer
        gr.Markdown("""
        ---
        <div style="text-align: center; color: #666;">
            <p>Powered by Google Gemini AI | Built with Gradio</p>
            <p>⚡ Provide meaningful answers to receive constructive feedback</p>
            <p>Developed by <a href="https://github.com/yousuf-git" target="_blank" style="color: #2196F3; text-decoration: none; font-weight: 500;">M. Yousuf</a></p>
        </div>
        """)
        
        # Event handlers
        def process_and_update(pdf_file, num_q):
            status, initial_msg, error, model_info, lifelines_info = process_pdf(pdf_file, num_q)
            if initial_msg:
                return status, [[None, initial_msg]], error, model_info, lifelines_info
            return status, [], error, model_info, lifelines_info
        
        def export_and_download():
            file_path, error = export_report()
            if error:
                return None, error
            return file_path, ""
        
        # Process PDF - only update outputs that change, keeping others static
        process_btn.click(
            fn=process_and_update,
            inputs=[pdf_input, num_questions],
            outputs=[status_output, chatbot, error_notification, model_indicator, lifelines_status],
            show_progress="minimal"
        )
        
        export_btn.click(
            fn=export_and_download,
            outputs=[report_file, error_notification],
            show_progress="minimal"
        ).then(
            fn=lambda: gr.File(visible=True),
            outputs=[report_file]
        )
        
        # Lifeline buttons - show loading only in chatbot
        rephrase_btn.click(
            fn=lambda h: use_lifeline("rephrase", h),
            inputs=[chatbot],
            outputs=[chatbot, error_notification, model_indicator, lifelines_status],
            show_progress="minimal"
        )
        
        new_question_btn.click(
            fn=lambda h: use_lifeline("new", h),
            inputs=[chatbot],
            outputs=[chatbot, error_notification, model_indicator, lifelines_status],
            show_progress="minimal"
        )
        
        # Submit answer - immediate user message, then loading in chatbot only
        msg_input.submit(
            fn=chat_with_examiner,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input, error_notification, model_indicator, lifelines_status, retry_btn],
            show_progress="minimal"
        ).then(
            fn=lambda show_retry: gr.Button(visible=show_retry),
            inputs=[retry_btn],
            outputs=[retry_btn]
        )
        
        submit_btn.click(
            fn=chat_with_examiner,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input, error_notification, model_indicator, lifelines_status, retry_btn],
            show_progress="minimal"
        ).then(
            fn=lambda show_retry: gr.Button(visible=show_retry),
            inputs=[retry_btn],
            outputs=[retry_btn]
        )
        
        retry_btn.click(
            fn=retry_last_action,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input, error_notification, model_indicator, lifelines_status, retry_btn],
            show_progress="minimal"
        ).then(
            fn=lambda show_retry: gr.Button(visible=show_retry),
            inputs=[retry_btn],
            outputs=[retry_btn]
        )
        
        reset_btn.click(
            fn=reset_session,
            outputs=[status_output, chatbot, msg_input, error_notification, model_indicator, lifelines_status, retry_btn],
            show_progress="minimal"
        ).then(
            fn=lambda show_retry: gr.Button(visible=show_retry),
            inputs=[retry_btn],
            outputs=[retry_btn]
        )
    
    return demo


# Main execution
if __name__ == "__main__":
    # Initialize the app
    init_status = initialize_app()
    print(init_status)
    
    if "Error" in init_status:
        print("\n" + "="*50)
        print("⚠️  SETUP REQUIRED")
        print("="*50)
        print("\nPlease create a .env file with your Gemini API key:")
        print("GEMINI_API_KEY=your_api_key_here")
        print("\nGet your API key at: https://makersuite.google.com/app/apikey")
        print("="*50 + "\n")
    
    # Create and launch the interface
    demo = create_interface()
    
    # Launch with configuration suitable for Hugging Face Spaces
    demo.launch(
        server_name="0.0.0.0",  # Listen on all interfaces (required for Docker/HF Spaces)
        server_port=7860,        # Default port for Gradio/HF Spaces
        share=False,             # Don't create a public link (HF Spaces handles this)
        show_error=True          # Show detailed errors
    )
