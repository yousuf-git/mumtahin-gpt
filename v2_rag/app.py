"""
MumtahinGPT - Gradio Application with RAG
==========================================
Main application file that creates the interactive Gradio interface
for the AI-powered document examiner chatbot with Retrieval-Augmented Generation.

This module integrates the PDF handler and examiner logic to provide
a seamless user experience with RAG support for efficient large document processing.
"""

import os
import gradio as gr
from dotenv import load_dotenv
from pdf_handler import PDFHandler
from examiner_logic import create_examiner, MumtahinGPT
from typing import List, Tuple, Optional
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

# Load environment variables
load_dotenv()

# Initialize ChromaDB for RAG
chroma_client = chromadb.Client()
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# Global state
examiner: Optional[MumtahinGPT] = None
pdf_handler: PDFHandler = None
session_active: bool = False


def initialize_app() -> str:
    """
    Initialize the application and check for API key.
    
    Returns:
        str: Status message
    """
    try:
        global examiner, pdf_handler
        api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            return "⚠️ Error: GEMINI_API_KEY not found. Please set it in your .env file."
        
        examiner = create_examiner(api_key)
        pdf_handler = PDFHandler(chroma_client, embedding_function)
        return "✅ Application initialized successfully with RAG support!"
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
        model_info = f"🤖 **Current AI Model:** gemini-2.0-flash-exp"
        lifelines_status = f"🎯 **Lifelines Available:** {lifelines_remaining}/{lifelines_total}"
        
        yield status_msg, initial_chat, "", model_info, lifelines_status, ""
        return
        
    except Exception as e:
        return f"❌ Error processing PDF: {str(e)}", [], "", "", "", ""


def chat_with_examiner(message: str, history: List):
    """Handle conversation with the AI examiner."""
    if not session_active:
        error_msg = "⚠️ Please upload and analyze a PDF document first."
        return history, "", error_msg, "", "", False
    
    if not message.strip():
        lifelines_remaining, lifelines_total = examiner.get_lifelines_status()
        return history, "", "", "🤖 **Current AI Model:** gemini-2.0-flash-exp", f"🎯 **Lifelines:** {lifelines_remaining}/{lifelines_total}", False
    
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
            return history, "", "", "🤖 **Model:** gemini-2.0-flash-exp", f"🎯 **Lifelines:** {lifelines_remaining}/{lifelines_total}", False
        
        next_question, question_error = examiner.generate_next_question()
        
        if question_error:
            history[-1][1] = f"**Examiner:** {evaluation}"
            return history, "", f"⚠️ Error generating next question: {question_error}", "", "", True
        
        response = f"{evaluation}\n\n---\n**Next Question:**\n{next_question}"
        history[-1][1] = f"**Examiner:** {response}"
        
        model_info = "🤖 **Current AI Model:** gemini-2.0-flash-exp"
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
        return history, "⚠️ No lifelines remaining!", "🤖 **Model:** gemini-2.0-flash-exp", f"🎯 **Lifelines:** 0/{lifelines_total}"
    
    if not examiner.use_lifeline(lifeline_type):
        return history, "⚠️ Failed to use lifeline", "", ""
    
    try:
        question, error = examiner.generate_next_question()
        
        if error:
            return history, f"❌ Error: {error}", "", ""
        
        lifeline_msg = "🔄 **Rephrased Question**" if lifeline_type == "rephrase" else "✨ **New Question**"
        history.append([None, f"**Examiner:** {lifeline_msg}\n\n{question}"])
        
        lifelines_remaining, lifelines_total = examiner.get_lifelines_status()
        return history, "", "🤖 **Model:** gemini-2.0-flash-exp", f"🎯 **Lifelines:** {lifelines_remaining}/{lifelines_total}"
        
    except Exception as e:
        return history, f"❌ Error: {str(e)}", "", ""


def reset_session():
    """Reset the examination session."""
    global session_active
    session_active = False
    examiner.reset_state()
    pdf_handler.reset()
    return "🔄 Session reset. Upload a new PDF to start.", [], "", "", "", "", False


def retry_last_action(message: str, history: List):
    """Retry the last failed action."""
    return chat_with_examiner(message, history)


def export_session():
    """Export the examination session as a PDF report."""
    if not session_active and not examiner.state.questions_asked:
        return None, "⚠️ No examination data to export"
    
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


# Custom CSS
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
    
    # Create Gradio interface
    with gr.Blocks(title="MumtahinGPT - Gemini with RAG") as demo:
        gr.HTML("""
        <div style='text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; border-radius: 10px; margin-bottom: 20px;'>
            <h1 style='margin: 0; font-size: 2.5em; color:white;'>🎓 MumtahinGPT</h1>
            <p style='margin: 10px 0 0 0; font-size: 1.2em; color: white;'>Powered by Google Gemini with RAG - AI Document Examination System</p>
        </div>
        """)
        
        with gr.Accordion("📖 How to Use MumtahinGPT (Click to expand)", open=False):
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
            <p style='margin: 10px 0 0 0; font-size: 14px;'>
                <a href='https://github.com/yousuf-git' target='_blank' style='color: #667eea; text-decoration: none; margin: 0 10px;'>
                    🔗 GitHub
                </a> | 
                <a href='https://yousuf-dev.com' target='_blank' style='color: #667eea; text-decoration: none; margin: 0 10px;'>
                    🌐 Portfolio
                </a>
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
        
        # Apply custom CSS for Gradio 6.x compatibility
        demo.load(js=f"""
        function() {{
            const style = document.createElement('style');
            style.innerHTML = `{custom_css}`;
            document.head.appendChild(style);
        }}
        """)
    
    # Launch the interface
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
