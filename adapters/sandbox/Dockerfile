FROM python:3.12-slim

RUN pip install --no-cache-dir pytest==8.3.5

RUN useradd --create-home --uid 1000 runner
WORKDIR /workspace
RUN chown runner:runner /workspace

USER runner
ENV PYTHONDONTWRITEBYTECODE=1

ENTRYPOINT ["pytest", "-q", "-p", "no:cacheprovider"]
