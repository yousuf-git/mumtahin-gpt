# MumtahinGPT Dockerfile
# ======================
# This Dockerfile is configured for v2_rag (RAG-based version) by default
# For v1_basic deployment, change COPY commands to use v1_basic/ instead of v2_rag/

# Use Python 3.9 slim image for smaller size
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=7860

# Install system dependencies required for PDF processing
RUN apt-get update && apt-get install -y \
    libmupdf-dev \
    mupdf-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ========================================
# MAIN VERSION: v2_rag (RAG-based)
# ========================================
# Copy v2_rag application files (RAG version with ChromaDB)
COPY v2_rag/pdf_handler.py .
COPY v2_rag/examiner_logic.py .
COPY v2_rag/app.py .

# ========================================
# ALTERNATIVE: v1_basic (Basic version without RAG)
# ========================================
# To deploy v1_basic instead, comment out the v2_rag lines above
# and uncomment these lines:
# COPY v1_basic/pdf_handler.py .
# COPY v1_basic/examiner_logic.py .
# COPY v1_basic/app.py .

# COPY .env.example .env

# Create a non-root user for security
RUN useradd -m -u 1000 mumtahin && \
    chown -R mumtahin:mumtahin /app

USER mumtahin

# Expose Gradio port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:7860')" || exit 1

# Run the application
CMD ["python", "app.py"]
