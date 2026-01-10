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
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update && apt-get install -y nodejs \
    && npm install -g npm@latest \
    && rm -rf /var/lib/apt/lists/*

# Install Common Python Libs for Agent Skills (with optimized cache)
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
    playwright

# Install Playwright Browsers
RUN playwright install --with-deps chromium

# Create user 'guest' (uid=1000) to match standard host user
RUN useradd -m -u 1000 guest \
    && mkdir -p /app/skills /share \
    && chown -R guest:guest /app /share

# Set working directory to /share
WORKDIR /share

# Switch to non-root user
USER guest

# Default command
CMD ["/bin/bash"]
