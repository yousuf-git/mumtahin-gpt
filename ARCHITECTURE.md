# 🏗️ MumtahinGPT - Architecture & Deployment Guide

## 📐 System Architecture

### Overview
MumtahinGPT is a modular, AI-powered document examination system with intelligent scoring, lifeline support, RAG (Retrieval-Augmented Generation) capabilities, and comprehensive reporting. The architecture follows clean separation of concerns with multiple components and robust error handling.

**Two Versions Available:**
- **v1_basic**: Basic version without RAG (simpler, faster for small documents)
- **v2_rag**: RAG-based version with ChromaDB (recommended for comprehensive document analysis)

```
┌─────────────────────────────────────────────────────────────┐
│                        User Interface                        │
│                  (Gradio Web App + PDF Export)               │
│  • Question Selector (1-10)                                  │
│  • Lifeline Buttons (Rephrase/New)                          │
│  • Retry Button (Auto-shown on errors)                      │
│  • Model Display (Real-time)                                │
│  • PDF Report Export (ReportLab)                            │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
│                    (v2_rag/app.py)                          │
│  • Session Management                                        │
│  • RAG System Initialization (ChromaDB)                     │
│  • UI Event Handling                                         │
│  • State Coordination                                        │
│  • Error Display & Retry Logic                              │
│  • PDF Report Generation (ReportLab)                        │
│  • Lifeline Management                                       │
└──────────────┬────────────────────────┬─────────────────────┘
               │                        │
               ▼                        ▼
┌──────────────────────────┐  ┌──────────────────────────────┐
│  PDF Handler + RAG       │  │   Examiner Logic Module      │
│  (v2_rag/pdf_handler.py) │  │  (v2_rag/examiner_logic.py)  │
│                          │  │                              │
│  • Text Extraction       │  │  • Document Analysis         │
│  • Metadata Parsing      │  │  • Question Generation       │
│  • Content Validation    │  │  • Answer Evaluation (Marks) │
│  • Filename Extraction   │  │  • Multi-Model Fallback      │
│  • RAG Collection Setup  │  │  • Lifeline Handling         │
│  • Semantic Chunking     │  │  • RAG-based Context         │
│  • Vector Storage        │  │  • Final Evaluation (50%)    │
│  • Chunk Retrieval       │  │                              │
│                          │  │  AI Models (5 models):       │
│  Libraries:              │  │  - gemini-2.5-flash (10 RPM) │
│  - PyMuPDF (primary)     │  │  - gemini-2.0-flash-lite (30)│
│  - pdfplumber (fallback) │  │  - gemini-2.5-flash-lite (15)│
│  - ChromaDB (v2_rag)     │  │  - gemini-2.0-flash (15 RPM) │
│  - sentence-transformers │  │  - gemini-2.5-pro (3 RPM)    │
└──────────────────────────┘  └──────────────────────────────┘
```

## 🔧 Component Breakdown

### **Version Structure:**

**v1_basic/** - Basic version without RAG
- `app.py` - Gradio interface
- `examiner_logic.py` - Core examination logic
- `pdf_handler.py` - PDF extraction only

**v2_rag/** - RAG-based version (RECOMMENDED)
- `app.py` - Gradio interface with RAG initialization
- `examiner_logic.py` - RAG-enhanced examination logic
- `pdf_handler.py` - PDF extraction + ChromaDB integration

### 1. **PDF Handler (`pdf_handler.py`)**

**v1_basic version:**
- Basic PDF text extraction
- Metadata extraction
- Content validation

**v2_rag version (Enhanced with RAG):**

**Purpose:** Handles PDF operations + RAG collection management

**Key Features:**
- Dual extraction strategy (PyMuPDF + pdfplumber fallback)
- Metadata extraction (page count, title, author)
- Content validation and text quality assessment
- **RAG Collection Setup** (ChromaDB)
- **Semantic Text Chunking** (1000 chars with 200 overlap)
- **Vector Storage** (sentence-transformers embeddings)
- **Relevant Chunk Retrieval** (top 3 most relevant)

**Class: `PDFHandler`**
```python
Methods:
# Basic operations
- extract_text(pdf_path) → str
- get_summary() → Dict
- validate_content() → bool

# RAG operations (v2_rag only)
- setup_rag_collection(text, doc_title) → bool
- retrieve_relevant_chunks(query, n_results=3) → List[str]
- chunk_text(text, chunk_size=1000, overlap=200) → List[str]
```

**How it works (v2_rag):**
1. Receives PDF file path from UI
2. Extracts text with PyMuPDF (fallback to pdfplumber)
3. Validates content length and quality
4. Chunks text into semantic segments (1000 chars, 200 overlap)
5. Creates ChromaDB collection with document title
6. Generates embeddings using sentence-transformers
7. Stores chunks with metadata in vector database
8. Enables semantic retrieval for question/answer context

### 2. **Examiner Logic (`examiner_logic.py`)**

**v1_basic version:**
- Basic document analysis
- Question generation from full document
- Answer evaluation
- State management

**v2_rag version (RAG-Enhanced):**

**Purpose:** Core AI examination functionality with RAG integration

**Key Features:**
- Document analysis using Gemini AI
- **RAG-based question generation** (uses relevant chunks)
- **Context-aware answer evaluation** (retrieves related content)
- Intelligent lifeline handling with RAG
- Conversation state management
- **Semantic search** for relevant document sections
- Final summary generation with complete context

**Class: `ExaminerAI`**
```python
Methods:
- analyze_document(text, title) → (str, error)
- generate_next_question() → (str, error)
- evaluate_answer(answer) → (str, error)
- generate_final_summary() → (str, error)
- set_total_questions(total: int)
- use_lifeline(type: str) → bool
- get_lifelines_status() → (remaining, total)
- get_current_model() → str
- is_examination_complete() → bool
- reset_state()
```

**Class: `ConversationState`**
```python
Attributes:
- document_text
- document_title
- questions_asked
- answers_given
- evaluations
- marks (out of 10)
- current_question_index
- total_questions (customizable: 1-10)
- lifelines_total (20% of questions)
- lifelines_remaining
- lifelines_used
- awaiting_lifeline_response
- final_evaluation
```

**Multi-Model System:**
```python
Primary Model: gemini-2.5-flash (10 RPM)
Fallbacks:
  1. gemini-2.0-flash-lite (30 RPM - fastest)
  2. gemini-2.5-flash-lite (15 RPM)
  3. gemini-2.0-flash (15 RPM)
Premium Model: gemini-2.5-pro (3 RPM - for final evaluation)
```

**How it works:**
1. Analyzes uploaded document to understand context
2. Generates questions focusing on:
   - Problem statement and motivation
   - Scope and boundaries
   - Objectives and expected outcomes
   - Methodology and approach
   - Innovation, feasibility, and impact
3. Evaluates each answer with marks out of 10 based on:
   - Relevance (3 points)
   - Depth (3 points)
   - Document usage (2 points)
   - Clarity (2 points)
4. Handles lifeline requests:
   - Rephrase: Simplifies current question
   - New: Generates different question on different topic
5. Automatic model fallback on rate limits
6. Maintains conversation context
7. Produces final evaluation with 50% passing threshold using premium model

### 3. **Application Layer (`app.py`)**

**v2_rag version (RAG-Enhanced):**

**Purpose:** User interface and RAG system orchestration

**Key Features:**
- Gradio-based web interface
- **ChromaDB client initialization**
- **Embedding function setup** (sentence-transformers)
- Session management with RAG state
- Event handling with chunking progress
- Chat history management
- Beautiful, responsive UI
- Real-time model display
- Lifelines counter display
- Error notification with retry button
- PDF report generation (ReportLab)

**Main Functions:**
```python
# Initialization
- initialize_app() → str  # Sets up ChromaDB + embeddings

# RAG-aware operations
- process_pdf(file, num_questions) → (status, chat, error, model, lifelines)
  # Now includes RAG collection setup with progress tracking

- chat_with_examiner(msg, history) → (history, input, error, model, lifelines, show_retry)
  # Uses RAG for context retrieval

- use_lifeline(type, history) → (history, error, model, lifelines)
  # RAG-enhanced question rephrasing

- retry_last_action(msg, history) → (history, input, error, model, lifelines, show_retry)
- reset_session() → (status, history, input, error, model, lifelines, show_retry)
  # Cleans up ChromaDB collection

- export_report() → (file_path, error)
```

**RAG System Setup (v2_rag):**
```python
# ChromaDB initialization
chroma_client = chromadb.Client()

# Embedding function (sentence-transformers)
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# Pass to PDFHandler and Examiner
pdf_handler = PDFHandler(chroma_client, embedding_function)
examiner = MumtahinGPT(pdf_handler)
```

**UI Components:**
- PDF upload area
- Number of questions slider (1-10)
- Status display with document info
- Model indicator (real-time)
- Lifelines status display
- Error notification banner
- Retry button (auto-shown on errors)
- Interactive chatbot
- Lifeline buttons (Rephrase/New)
- Progress tracking
- Export report button
- Reset functionality

**PDF Report Features (ReportLab):**
- Meaningful filename: `Examination_Report_{DocName}_{Timestamp}.pdf`
- Document information table
- Results summary with Pass/Fail status
- Overall evaluation section
- Question-wise performance breakdown
- Professional formatting with colors and tables

**How it works:**
1. Loads environment variables (.env)
2. Initializes Gemini API with multiple models
3. Sets up Gradio interface with custom theme and CSS
4. Handles file uploads and processing
5. Extracts filename for document title
6. Manages chat interactions with error handling
7. Tracks examination progress and lifelines
8. Displays current model being used
9. Shows retry button on errors
10. Generates PDF reports with ReportLab
11. Provides session reset capability

## 🔄 Data Flow

### Examination Flow (v2_rag with RAG):

```
1. User uploads PDF + selects questions (1-10)
        ↓
2. PDF Handler extracts text and filename
        ↓
3. RAG Collection Setup:
   - Chunk text (1000 chars, 200 overlap)
   - Generate embeddings (sentence-transformers)
   - Store in ChromaDB with metadata
   - Display chunking progress to user
        ↓
4. Examiner analyzes document (gemini-2.5-flash)
   - Uses first 3000 chars for overview
        ↓
5. Lifelines calculated (20% of questions, min 1)
        ↓
6. First question generated:
   - Retrieve relevant chunks from ChromaDB
   - Pass context to AI for question generation
        ↓
7. User answers question
        ↓
8. Answer evaluated with marks out of 10:
   - Retrieve relevant chunks for answer context
   - AI evaluates with document context
        ↓
9. Check if examination complete
        ↓
10. If not complete: Next question generated
    - Semantic search for different topic
    - RAG ensures diverse question coverage
        ↓
11. If rate limit: Auto-fallback to next model
        ↓
12. If error: Show retry button
        ↓
13. Repeat steps 7-12 until all questions answered
        ↓
14. Final summary with gemini-2.5-pro (premium)
    - Retrieve comprehensive context from RAG
        ↓
15. Calculate total marks and Pass/Fail (50%)
        ↓
16. User exports PDF report
        ↓
17. Cleanup ChromaDB collection
        ↓
18. Session complete
```

### RAG Workflow (v2_rag specific):

```
Document Upload
        ↓
Text Extraction (PyMuPDF/pdfplumber)
        ↓
Semantic Chunking:
- Split into 1000-char segments
- 200-char overlap for context continuity
- Preserve sentence boundaries
        ↓
Embedding Generation:
- sentence-transformers: all-MiniLM-L6-v2
- 384-dimensional vectors
- Semantic meaning capture
        ↓
Vector Storage (ChromaDB):
- Collection: doc_title + timestamp
- Metadata: chunk_id, page_info
- Efficient similarity search
        ↓
Question Generation:
Query: "Generate question about X"
        ↓
Semantic Search:
- Retrieve top 3 relevant chunks
- Cosine similarity matching
        ↓
Context-Aware Generation:
- AI receives relevant excerpts
- Focused on specific document sections
        ↓
Answer Evaluation:
Query: User's answer
        ↓
Retrieve Related Content:
- Top 3 chunks relevant to answer
- Cross-reference with document
        ↓
Context-Aware Evaluation:
- AI compares answer with actual content
- More accurate scoring
```

### Lifeline Flow:

```
User clicks Rephrase/New button
        ↓
Check lifelines_remaining > 0
        ↓
If yes: Decrement lifelines_remaining
        ↓
Set awaiting_lifeline_response = True
        ↓
If "rephrase": Simplify last question
        ↓
If "new": Generate different question
        ↓
Update lifelines counter display
        ↓
Continue examination
```

### Error & Retry Flow:

```
API call fails (rate limit/error)
        ↓
Return error message to UI
        ↓
Show retry button (auto-visible)
        ↓
Display error in notification banner
        ↓
User clicks Retry
        ↓
Re-attempt last action with same input
        ↓
If success: Hide retry button
        ↓
If failure: Keep retry button visible
```

### State Management:

```python
Session State:
├── PDF Content (extracted text)
├── Document Title (from filename)
├── Document Analysis (AI summary)
├── Question History (list)
├── Answer History (list)
├── Evaluation History (list with marks)
├── Marks List (list of integers 0-10)
├── Current Question Index (int)
├── Total Questions (int: 1-10)
├── Lifelines Total (int: 20% of questions)
├── Lifelines Remaining (int)
├── Lifelines Used (list of tuples)
├── Current Model Name (string)
├── Final Evaluation (string)
├── Awaiting Lifeline Response (bool)
└── Session Active (bool)
```

## 🚀 Deployment Guide

### **Option 1: Local Development**

#### Prerequisites:
- Python 3.9 or higher
- Gemini API key

#### Steps:

1. **Clone/Download the project:**
```bash
git clone https://github.com/yousuf-git/mumtahin-gpt.git
cd mumtahin-gpt
```

2. **Choose version:**
```bash
# For RAG-based version (RECOMMENDED):
cd v2_rag

# OR for basic version:
# cd v1_basic
```

3. **Create virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

4. **Install dependencies:**
```bash
cd ..  # Go back to root
pip install -r requirements.txt
# For v2_rag, this includes:
# - chromadb==0.4.24
# - sentence-transformers==2.3.1
# Plus all standard dependencies
```

5. **Configure API key:**
```bash
# In the version directory (v2_rag or v1_basic)
cd v2_rag  # or v1_basic
nano .env
# Add: GOOGLE_API_KEY=your_actual_api_key_here
```

6. **Run the application:**
```bash
# Make sure you're in the version directory
python3 app.py

# For v2_rag, you'll see:
# ✅ Application initialized successfully with RAG support!
# 🔍 RAG system initialized with ChromaDB
```

7. **Access the interface:**
Open your browser at `http://localhost:7860`

### **Option 2: Docker Deployment**

#### Prerequisites:
- Docker installed
- Gemini API key

#### Steps:

1. **Build the Docker image:**
```bash
# Dockerfile is configured for v2_rag by default
docker build -t mumtahin-gpt .

# For v1_basic, edit Dockerfile:
# Uncomment v1_basic lines and comment v2_rag lines
```

2. **Run the container:**
```bash
# v2_rag (default)
docker run -p 7860:7860 \
  -e GOOGLE_API_KEY=your_api_key_here \
  mumtahin-gpt

# Or use .env file:
docker run -p 7860:7860 --env-file v2_rag/.env mumtahin-gpt
```

3. **Access the interface:**
Open `http://localhost:7860`

**Note:** v2_rag Docker image is ~500MB larger due to ChromaDB and sentence-transformers dependencies.

### **Option 3: Hugging Face Spaces (Recommended for Production)**

#### Prerequisites:
- Hugging Face account
- Git installed
- Gemini API key

#### Steps:

1. **Create a new Space:**
   - Go to https://huggingface.co/spaces
   - Click "Create new Space"
   - Name it (e.g., "mumtahin-gpt")
   - Select "Docker" as the SDK
   - Choose "Public" or "Private"
   - Click "Create Space"

2. **Clone your Space repository:**
```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/mumtahin-gpt
cd mumtahin-gpt
```

3. **Copy all project files to the Space:**
```bash
cp /path/to/mumtahin-gpt/* .
```

Files to include:
- `app.py`
- `pdf_handler.py`
- `examiner_logic.py`
- `requirements.txt`
- `Dockerfile`
- `README.md`

4. **Add your API key as a Space Secret:**
   - Go to your Space settings on Hugging Face
   - Navigate to "Settings" → "Variables and secrets"
   - Add a new secret:
     - Name: `GEMINI_API_KEY`
     - Value: Your actual Gemini API key
   - This is more secure than hardcoding in .env

5. **Commit and push:**
```bash
git add .
git commit -m "Initial commit: Examiner AI application"
git push
```

6. **Wait for build:**
   - Hugging Face will automatically build your Docker image
   - Monitor the build logs in the Space interface
   - Build typically takes 2-5 minutes

7. **Access your deployed app:**
   - Your app will be available at:
   - `https://huggingface.co/spaces/YOUR_USERNAME/mumtahin-gpt`

#### **Hugging Face Spaces Configuration:**

The app is pre-configured for Spaces with:
- Port 7860 (Spaces default)
- Server name 0.0.0.0 (required for Spaces)
- Proper health checks
- Optimized Docker layers

#### **Environment Variables in Spaces:**

Set these in Space Settings → Variables and secrets:
- `GEMINI_API_KEY` (required) - Your Google Gemini API key

## 🔐 Security Best Practices

1. **Never commit API keys** to version control
2. **Use environment variables** for sensitive data
3. **Use Spaces Secrets** for production deployment
4. **Run container as non-root user** (already configured)
5. **Keep dependencies updated** regularly

## 📊 Performance Optimization

### Current Optimizations:

**v1_basic:**
- **Multi-model fallback** system for high availability (5 models)
- **Gemini 2.5 Flash** model for faster Q&A responses (10 RPM)
- **Gemini 2.0 Flash Lite** for high-volume fallback (30 RPM)
- **Gemini 2.5 Pro** for premium final evaluation (3 RPM)
- **Text limiting** in prompts (first 2-3k chars for analysis)
- **Dual PDF extraction** with fallback strategy
- **ReportLab PDF generation** for efficient report creation
- **Automatic retry mechanism** for transient failures

**v2_rag (Additional RAG Optimizations):**
- **Semantic chunking** (1000 chars, 200 overlap) for optimal context
- **Efficient embedding model** (all-MiniLM-L6-v2, 384-dim vectors)
- **ChromaDB in-memory** mode for fast vector search
- **Top-3 chunk retrieval** balances context quality and speed
- **Lazy RAG initialization** (only on document upload)
- **Collection cleanup** after session to free memory
- **Batch embedding generation** for multiple chunks
- **Cosine similarity** for fast semantic search
- **Sentence boundary preservation** in chunks

### RAG Performance Metrics:
- **Chunking:** ~2-3 seconds for 50-page document
- **Embedding:** ~1-2 seconds for 100 chunks
- **Retrieval:** <100ms for top-3 chunks
- **Memory:** ~50-100MB per document collection
- **Total overhead:** ~3-5 seconds per document (one-time)

### Recommendations:

**v1_basic:**
- Best for documents < 20 pages
- Faster initial response (no RAG setup)
- Lower memory footprint

**v2_rag:**
- Best for documents > 20 pages
- More accurate with large documents
- Better context awareness
- Slightly higher latency (RAG setup)
- Requires ~100MB extra memory

**General:**
- For very large PDFs (>200 pages), increase chunk size to 2000
- Implement response caching for repeated questions
- Monitor model performance and adjust priorities
- Consider GPU for sentence-transformers (optional)
- Use persistent ChromaDB for production (optional)

## 🐛 Troubleshooting

### Common Issues:

**1. API Key Error:**
```
Solution: Ensure GEMINI_API_KEY is set correctly in .env or Spaces Secrets
```

**2. Rate Limit Errors:**
```
Solution: System automatically falls back to alternative models
- Try clicking the Retry button that appears
- Wait a moment for rate limits to reset
- System uses 30 RPM fallback model automatically
```

**3. PDF Extraction Fails:**
```
Solution: Check if PDF has selectable text (not scanned images)
Consider adding OCR support for scanned documents
Ensure PDF is not password-protected
```

**4. Marks Not Showing:**
```
Solution: Evaluation uses specific format "**Marks: X/10**"
- Check examiner_logic.py evaluate_answer() method
- Regex extracts marks from AI response
- Default to 5/10 if format not found
```

**5. Lifelines Not Working:**
```
Solution: Check lifelines_remaining > 0
- Lifelines calculated as 20% of total questions
- Minimum 1 lifeline always available
- UI shows remaining/total count
```

**6. PDF Report Export Fails:**
```
Solution: Ensure reportlab is installed
- Check requirements.txt includes reportlab==4.0.7
- Verify temp directory is writable
- Check session has completed examination
```

**7. Docker Build Fails:**
```
Solution: Ensure all files are present
Check Docker daemon is running
Verify internet connection for dependency downloads
```

**8. Gradio Port Already in Use:**
```
Solution: Change port in app.py or kill process using port 7860
pkill -f "python.*app.py"
```

## 📈 Future Enhancements

Potential improvements:
- [ ] OCR support for scanned PDFs
- [ ] Multi-document comparison
- [✅] Export evaluation reports to PDF (COMPLETED)
- [✅] Custom question count selector (COMPLETED)
- [✅] Marks out of 10 system (COMPLETED)
- [✅] Lifeline system (COMPLETED)
- [✅] Retry mechanism (COMPLETED)
- [✅] Multi-model fallback (COMPLETED)
- [ ] Custom question templates
- [ ] Multi-language support
- [ ] Voice input/output
- [ ] Integration with learning management systems
- [ ] Historical performance tracking
- [ ] Answer comparison with reference answers
- [ ] Plagiarism detection
- [ ] Collaborative examination mode

## 📚 Dependencies Explained

- **gradio==4.19.2**: Web UI framework (intentionally older version for HuggingFace Hub compatibility)
- **google-generativeai==0.8.2**: Gemini AI SDK for multiple model support
- **PyMuPDF==1.24.10**: Fast PDF text extraction (primary)
- **pdfplumber==0.11.4**: Robust PDF parsing (fallback)
- **python-dotenv==1.0.1**: Environment variable management
- **reportlab==4.0.7**: PDF report generation for examination results

## 📞 Support

For issues or questions:
- Check the README.md for quick start guide
- Review IMPROVEMENTS.md for feature changelog
- Review error messages in logs and UI
- Verify API key is valid
- Ensure Python version is 3.9+
- Check that all dependencies are installed
- Use the retry button for transient errors
- Monitor model display for fallback information

---

**Built with ❤️ using Gradio and Google Gemini AI**
**Latest Update: Multi-model system with 5 Gemini models, scoring system, lifelines, retry mechanism, and PDF export**
