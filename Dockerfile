FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive
ARG HTTP_PROXY=""
ARG HTTPS_PROXY=""
ARG NO_PROXY=""

# expose proxy args as both upper/lowercase envs so curl/conda/apt pick them up
ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV NO_PROXY=${NO_PROXY}
ENV http_proxy=${HTTP_PROXY}
ENV https_proxy=${HTTPS_PROXY}
ENV no_proxy=${NO_PROXY}

# configure apt to use proxy if provided
RUN if [ -n "${HTTP_PROXY}" ] || [ -n "${HTTPS_PROXY}" ]; then \
    echo "Acquire::http::Proxy \"${HTTP_PROXY}\";" > /etc/apt/apt.conf.d/01proxy || true; \
    echo "Acquire::https::Proxy \"${HTTPS_PROXY}\";" >> /etc/apt/apt.conf.d/01proxy || true; \
  fi; \
  apt-get update \
  && apt-get install -y --no-install-recommends \
    bash \
    python3 \
    python3-pip \
    python3-venv \
    python3-distutils \
    bzip2 \
    ca-certificates \
    curl \
    git \
    vim \
    build-essential \
    libglib2.0-0 \
    libxext6 \
    libsm6 \
    libxrender1 \
    libxml2 \
    libssl3 \
    libcurl4 \
    libharfbuzz0b \
    libfribidi0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libtiff5 \
    libjpeg-turbo8 \
    libpng16-16 \
    libfreetype6 \
  && rm -rf /var/lib/apt/lists/*

ENV CONDA_DIR=/opt/conda
ENV PATH=$CONDA_DIR/bin:$PATH

# Install Miniforge (small); then install mamba
RUN curl -fsSLo /tmp/miniforge.sh https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh \
  && bash /tmp/miniforge.sh -b -p $CONDA_DIR \
  && rm -f /tmp/miniforge.sh \
  && conda --version \
  && conda install -n base -c conda-forge mamba -y \
  && mamba --version

WORKDIR /opt/biomni

ENV NON_INTERACTIVE=1
ENV BIOMNI_TOOLS_DIR=/opt/biomni/biomni_tools

COPY biomni_env/bio_env.yml /opt/biomni/biomni_env/bio_env.yml

# Create conda environment from YAML using mamba with retries
RUN set -eux; \
  for i in 1 2; do \
    mamba env create -n biomni_e1 -f /opt/biomni/biomni_env/bio_env.yml && break || { echo "mamba env create failed (attempt $i)"; sleep $((i*2)); }; \
  done; \
  conda clean -a -y

COPY . /opt/biomni

RUN mamba run -n biomni_e1 pip install --upgrade pip \
  && mamba run -n biomni_e1 pip install -e /opt/biomni

ENV BIOMNI_DATA_PATH=/opt/biomni/data
EXPOSE 7860

COPY docker/entrypoint.sh /usr/local/bin/biomni-entrypoint
RUN chmod +x /usr/local/bin/biomni-entrypoint

ENTRYPOINT ["/usr/local/bin/biomni-entrypoint"]
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860", "--reload"]