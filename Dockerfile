# Python version can be changed, e.g.
# FROM python:3.8
# FROM ghcr.io/mamba-org/micromamba:1.5.1-focal-cuda-11.3.1
FROM docker.io/python:3.12.0-slim-bookworm

LABEL org.opencontainers.image.authors="FNNDSC <dev@babyMRI.org>" \
      org.opencontainers.image.title="A ChRIS plugin to send DICOMS" \
      org.opencontainers.image.description="A ChRIS plugin to send DICOMs to a remote PACS store"

ARG SRCDIR=/usr/local/src/pl-dicom_dirSend
WORKDIR ${SRCDIR}

COPY requirements.txt .
RUN pip install -r requirements.txt
RUN apt-get update \
    && apt-get install dcmtk -y

COPY . .
ARG extras_require=none
RUN pip install ".[${extras_require}]" \
    && cd / && rm -rf ${SRCDIR}
WORKDIR /

CMD ["dicom_dirSend"]
