FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY yaml_key_remover.py ./
COPY removed_values_mapper.py ./

ENTRYPOINT ["python", "/app/yaml_key_remover.py"]
