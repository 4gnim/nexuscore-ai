FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    FASTEMBED_CACHE_PATH=/home/user/.cache/fastembed

WORKDIR /app

# Install OpenMP runtime (libgomp1) required by XGBoost & scikit-learn
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (UID 1000) & cache directories
RUN useradd -m -u 1000 user && \
    mkdir -p /home/user/.cache/huggingface /home/user/.cache/fastembed && \
    chown -R user:user /app /home/user

COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

USER user

# Pre-download FastEmbed ONNX models during image build for instant container startup
RUN python -c "from fastembed import TextEmbedding, SparseTextEmbedding; \
    TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'); \
    SparseTextEmbedding('Qdrant/bm25')"

COPY --chown=user:user . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]