FROM python:3.13-slim

WORKDIR /app

# System packages required by OCR/document processing
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from project root
COPY requirements.txt .

# Install CPU-only PyTorch
RUN pip install --no-cache-dir \
    torch==2.14.0 \
    --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
RUN pip install --no-cache-dir -r requirements.txt

# The retrieval pipeline uses text models only; avoid an incompatible optional
# torchvision install from triggering Transformers' vision imports.
RUN pip uninstall -y torchvision

# Download SpaCy English model
RUN python -m spacy download en_core_web_sm

# Copy backend source
COPY backend/ .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]