FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    bash \
    bzip2 \
    ca-certificates \
    curl \
    git \
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

ENV MAMBA_ROOT_PREFIX=/opt/conda
ENV PATH=/opt/conda/bin:$PATH

RUN curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest \
  | tar -xvj -C /usr/local/bin/ --strip-components=1 bin/micromamba

WORKDIR /opt/biomni
COPY . /opt/biomni

ARG BIOMNI_ENV=base

ENV NON_INTERACTIVE=1
ENV BIOMNI_TOOLS_DIR=/opt/biomni/biomni_tools

RUN chmod +x /opt/biomni/biomni_env/setup.sh \
  && bash -lc "cd /opt/biomni/biomni_env \
    && if [ \"${BIOMNI_ENV}\" = \"full\" ]; then ./setup.sh; \
       else micromamba create -y -n biomni_e1 -f environment.yml; \
       fi"

RUN micromamba run -n biomni_e1 pip install --upgrade pip \
  && micromamba run -n biomni_e1 pip install -e /opt/biomni

ENV BIOMNI_DATA_PATH=/opt/biomni/data
EXPOSE 7860

COPY docker/entrypoint.sh /usr/local/bin/biomni-entrypoint
RUN chmod +x /usr/local/bin/biomni-entrypoint

ENTRYPOINT ["/usr/local/bin/biomni-entrypoint"]
CMD ["bash"]
