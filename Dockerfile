FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    FASTEMBED_CACHE_PATH=/home/user/.cache/fastembed \
    MPLCONFIGDIR=/tmp/matplotlib \
    OMP_NUM_THREADS=1

WORKDIR /app

# Install OpenMP runtime (libgomp1) required by XGBoost & scikit-learn
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (UID 1000 required by Hugging Face Spaces) & writable cache directories
RUN useradd -m -u 1000 user && \
    mkdir -p /app /home/user/.cache/huggingface /home/user/.cache/fastembed && \
    chown -R user:user /app /home/user

# Install Python dependencies first for optimal Docker layer caching
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Switch to non-root user (UID 1000) before pre-downloading models so cache permissions match runtime
USER user

# Pre-download FastEmbed ONNX models during image build for fast startup & zero runtime PermissionError
RUN python -c "from fastembed import TextEmbedding, SparseTextEmbedding; \
    TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'); \
    SparseTextEmbedding('Qdrant/bm25')"

# Copy application source code, curated datasets & trained ML artifacts with UID 1000 ownership
COPY --chown=user:user . .

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]