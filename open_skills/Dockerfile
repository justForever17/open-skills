# v8chat Universal Computer Runtime (Polyglot Edition)
# "Batteries Included" - Pre-install common libs to speed up execution time.

FROM python:3.11-slim

# Prevent writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Allow pip to manage system packages (Bypass PEP 668)
ENV PIP_BREAK_SYSTEM_PACKAGES=1

# Install system utilities & Node.js
# We use nodesource to get a modern Node version (v20 LTS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    vim \
    jq \
    ffmpeg \
    ca-certificates \
    gnupg \
    libreoffice \
    poppler-utils \
    pandoc \
    tesseract-ocr \
    qpdf \
    pdftk \
    # System Build Tools (For compiling Python/Node extensions)
    build-essential \
    pkg-config \
    libcairo2-dev \
    libpango1.0-dev \
    libjpeg-dev \
    libgif-dev \
    librsvg2-dev \
    # Chinese Fonts (CRITICAL for PDF/Image rendering)
    fonts-noto-cjk \
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
    fonts-arphic-ukai \
    fonts-arphic-uming \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update && apt-get install -y nodejs \
    && npm install -g npm@latest \
    && npm install -g pptxgenjs playwright react-icons sharp docx canvas typescript ts-node \
    && rm -rf /var/lib/apt/lists/*

# Install Common Python Libs for Agent Skills
RUN pip install --no-cache-dir \
    numpy \
    pandas \
    requests \
    beautifulsoup4 \
    python-dotenv \
    Pillow \
    lxml \
    openpyxl \
    python-docx \
    python-pptx \
    PyPDF2 \
    matplotlib \
    markitdown \
    playwright \
    pdfplumber \
    reportlab \
    pytesseract \
    pdf2image \
    defusedxml \
    anthropic \
    imageio \
    imageio-ffmpeg \
    # Data Science & ML (Hardening)
    scikit-learn \
    seaborn \
    scipy

# Configure Environment for Node.js
# 1. NODE_PATH: Allow scripts to find global modules AND user modules in /share
# 2. NPM_CONFIG_PREFIX: Force 'npm install' to write to /share/.npm-global by default (writable)
# 3. PLAYWRIGHT_BROWSERS_PATH: Install browsers to a global shared location
ENV NODE_PATH="/usr/lib/node_modules:/usr/local/lib/node_modules:/share/node_modules" \
    NPM_CONFIG_PREFIX="/share/.npm-global" \
    PATH="${PATH}:/share/.npm-global/bin" \
    PLAYWRIGHT_BROWSERS_PATH="/ms-playwright" \
    MPLCONFIGDIR="/share/.cache/matplotlib" \
    HF_HOME="/share/.cache/huggingface" \
    TORCH_HOME="/share/.cache/torch"

# Fix Git ownership issue for mounted volumes
RUN git config --system --add safe.directory '*'

# Create global playwright directory with correct permissions

# Create global playwright directory with correct permissions
RUN mkdir -p /ms-playwright && chmod 777 /ms-playwright

# Install Playwright Browsers (Python & Node) into global path
RUN playwright install --with-deps chromium

# Create user 'agent' (uid=1000) and pre-create cache dirs for volume permission inheritance
RUN useradd -m -u 1000 agent \
    && mkdir -p /app/skills /share /home/agent/.npm /home/agent/.cache/pip \
    && chown -R agent:agent /app /share /home/agent

# Set working directory
WORKDIR /share

# Switch to non-root user
USER agent

# Default command
CMD ["/bin/bash"]
