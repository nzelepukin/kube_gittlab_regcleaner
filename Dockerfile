FROM python:3.9-slim as builder
WORKDIR /app
COPY . .
RUN apt-get update \
    && apt-get install -y gnupg2 build-essential
RUN python3.9 -m pip install update \
    && python3.9 -m pip install -r requirements.txt

FROM python:3.9-slim
COPY --from=builder /usr/local/lib/python3.9/ /usr/local/lib/python3.9/
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY . .
CMD ["python3.9", "start.py"]