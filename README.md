# 🎓 MumtahinGPT - Intelligent PDF Document Examination System

An AI-powered examination system that acts as an intelligent examiner for your PDF documents. Upload a project proposal, research paper, or any document, and the AI will ask intelligent questions about it, evaluate your answers with marks out of 10, and provide constructive feedback with a comprehensive report.

## 📦 Project Versions

This project includes **two versions**:

### 🔹 **v1_basic** - Basic Version (Without RAG)
- Traditional document processing
- Suitable for smaller documents (< 50 pages)
- Lower resource requirements
- Single-pass document analysis

### 🔸 **v2_rag** - RAG-Based Version (Recommended) ⭐
- **Retrieval-Augmented Generation** (RAG) with ChromaDB
- Scalable for large documents (1000+ pages)
- Semantic chunking and vector search
- Efficient token usage
- Context-aware question generation
- **Default deployment version**

## ✨ Features

- **📄 PDF Analysis**: Upload and analyze PDF documents automatically
- **🔍 RAG Technology** (v2): Semantic chunking for efficient large document processing
- **🎯 Dynamic Question Calculation**: Auto-scales questions based on document size (5-100 questions)
- **🤖 AI-Powered**: Google Gemini 2.0 Flash Exp for intelligent examination
- **📊 Scoring System**: Each answer is marked out of 10 with detailed feedback
- **🎓 Pass/Fail Grading**: Automatic evaluation with 50% passing threshold
- **💡 Lifeline System**: Use lifelines to rephrase or replace difficult questions
- **📑 PDF Export**: Generate comprehensive examination reports with meaningful filenames
- **🎨 Beautiful Interface**: Clean Gradio-based chat interface
- **⚡ Chat Context**: Maintains conversation history for better evaluation

## 🚀 Quick Start

### Version Selection

**Choose v2_rag (RAG-based)** for:
- ✅ Documents > 50 pages
- ✅ Books and large technical documents
- ✅ Better token efficiency
- ✅ Scalable to 1000+ pages

**Choose v1_basic** for:
- ✅ Smaller documents (< 50 pages)
- ✅ Lower resource requirements
- ✅ Simpler deployment

### Local Development

#### For v2_rag (Recommended):

1. **Clone the repository**
   ```bash
   git clone https://github.com/yousuf-git/mumtahin-gpt.git
   cd mumtahin-gpt/v2_rag
   ```

2. **Set up environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   cd ..
   pip install -r requirements.txt
   ```

3. **Configure API Key**
   ```bash
   cp .env.example .env
   # Edit .env and add your Gemini API key
   ```

4. **Run the application**
   ```bash
   cd v2_rag
   python app.py
   ```

5. **Open your browser** at `http://localhost:7860`

#### For v1_basic:

```bash
git clone https://github.com/yousuf-git/mumtahin-gpt.git
cd mumtahin-gpt/v1_basic
python -m venv venv
source venv/bin/activate
cd ..
pip install -r requirements.txt
cd v1_basic
python app.py
```

### Docker Deployment

The Dockerfile is configured for v2_rag by default:

```bash
docker build -t mumtahingpt .
docker run -p 7860:7860 --env-file .env mumtahingpt
```

For v1_basic deployment, see comments in the Dockerfile.

## 🌐 Deploy to Hugging Face Spaces

1. Create a new Space on [Hugging Face](https://huggingface.co/spaces)
2. Select "Docker" as the SDK
3. Clone your Space repository
4. Copy all files to the Space repository
5. Add your `GEMINI_API_KEY` as a Space secret
6. Push to the repository:
   ```bash
   git add .
   git commit -m "Initial commit"
   git push
   ```

## 📋 Requirements

- Python 3.9+
- Google Gemini API Key ([Get it here](https://makersuite.google.com/app/apikey))

## 🏗️ Project Structure

```
mumtahin-gpt/
├── v1_basic/                  # Basic version without RAG
│   ├── app.py                # Main Gradio application
│   ├── examiner_logic.py     # AI logic and evaluation
│   └── pdf_handler.py        # PDF extraction
│
├── v2_rag/                   # RAG-based version (MAIN) ⭐
│   ├── app.py                # Main Gradio application with RAG
│   ├── examiner_logic.py     # AI logic with RAG support
│   └── pdf_handler.py        # PDF extraction with ChromaDB
│
├── requirements.txt          # Python dependencies (includes chromadb)
├── Dockerfile               # Docker config (v2_rag by default)
├── .env.example             # Environment template
├── README.md                # This file
├── AWS_EC2_DEPLOYMENT.md    # EC2 deployment guide
├── APP_SYSTEMD_SERVICE_EC2.md  # Systemd service setup
└── ARCHITECTURE.md          # Architecture documentation
```

## 🎨 UI Features

- **Real-time Model Display**: Shows which Gemini model is currently active
- **Lifelines Counter**: Live tracking of remaining/total lifelines
- **Question Progress**: Track current question out of total
- **Export Button**: One-click PDF report generation
- **Responsive Design**: Clean, professional interface
- **RAG Stats** (v2): Shows document chunks and processing info

## 🔄 Version Differences

### v1_basic
- ✅ Simple and lightweight
- ✅ Good for documents < 50 pages
- ✅ Lower memory usage
- ❌ May hit token limits on large documents

### v2_rag (Recommended)
- ✅ Handles 1000+ page documents
- ✅ Efficient token usage via chunking
- ✅ Semantic search for relevant content
- ✅ Better question generation
- ⚠️ Requires ChromaDB (included in requirements.txt)

## 🎯 How It Works

1. **Upload PDF**: User uploads a document (any size)
2. **RAG Processing** (v2): Document is chunked and indexed for semantic search
3. **Select Questions**: System calculates optimal questions (5-100) based on document size
4. **Analysis**: AI analyzes the document content using Gemini 2.0 Flash Exp
5. **Interactive Q&A**: AI asks questions using relevant document chunks
6. **Lifelines Available**: Use lifelines to:
   - 🔄 Rephrase unclear questions
   - ✨ Get completely different questions
7. **Scoring**: Each answer receives:
   - Marks out of 10
   - Detailed feedback with scoring criteria
   - Constructive suggestions for improvement
8. **Final Results**: 
   - Overall evaluation with comprehensive feedback
   - Total marks and percentage
   - Pass/Fail status (50% threshold)
9. **Export Report**: Download comprehensive PDF report

## 🏆 Grading System

- **Each Question**: Marked out of 10 based on:
  - Relevance to question (3 points)
  - Depth of understanding (3 points)
  - Use of document content (2 points)
  - Clarity of expression (2 points)

- **Final Grade**:
  - **50%+ = PASS ✅**
  - **Below 50% = FAIL ❌**

- **Lifelines**: 20% of total questions (minimum 1)
  - Rephrase difficult questions
  - Request completely new questions

## 🤖 AI Model Used

The system uses **Google Gemini 2.0 Flash Exp** for:
- Document analysis
- Question generation
- Answer evaluation
- Final summary

**Why Gemini 2.0 Flash Exp?**
- Fast response times
- High-quality outputs
- Excellent reasoning capabilities
- Cost-effective for production use

## 📝 License

MIT License - Feel free to use and modify!

## 👥 Developed By

**Team MumtahinGPT**

## 🚀 Deployment

For production deployment on AWS EC2, see:
- [AWS EC2 Deployment Guide](AWS_EC2_DEPLOYMENT.md)
- [Systemd Service Setup](APP_SYSTEMD_SERVICE_EC2.md)

Both guides are configured for v2_rag by default with instructions for v1_basic deployment.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
