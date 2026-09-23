# Backend image, built for Hugging Face Spaces (Docker SDK).
#
# Spaces run the container as uid 1000 and expect the app on port 7860, so both
# are set explicitly rather than relying on defaults.
#
# The models are baked in at build time. Downloading spaCy and the
# sentence-transformer on first request would make a cold start take minutes
# and, on a container with an ephemeral filesystem, happen again after a
# restart.

FROM python:3.11-slim

# WeasyPrint needs these native libraries; without them PDF export returns 503.
# Installed before the user switch because apt needs root.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libcairo2 \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libglib2.0-0 \
        libffi8 \
        shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Spaces execute as uid 1000; running as root means the app can't write its caches.
RUN useradd --create-home --uid 1000 user
USER user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR $HOME/app

COPY --chown=user backend/requirements.txt ./backend/requirements.txt

# The default torch wheel bundles CUDA and runs to several GB. Nothing here
# uses a GPU, so the CPU build is installed first and satisfies the dependency
# before sentence-transformers can pull the large one in.
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir \
        torch --index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install --no-cache-dir -r backend/requirements.txt \
    && python -m spacy download en_core_web_md

# Warm the transformer cache so the first request doesn't pay for the download.
RUN python -c "from sentence_transformers import SentenceTransformer; \
SentenceTransformer('all-MiniLM-L6-v2')"

COPY --chown=user backend ./backend

EXPOSE 7860

# Single worker on purpose: each one loads its own copy of spaCy and the
# transformer, so a second worker doubles the memory for no throughput gain on
# a 2-vCPU box.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
