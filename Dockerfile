# Build Image
FROM python:3.9-slim as builder

RUN apt-get update && apt-get install -y gnupg2 build-essential
RUN python3.9 -m pip install update

COPY requirements.txt ./

RUN python3.9 -m pip install -r requirements.txt

# Final Image
FROM python:3.9-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.9/ /usr/local/lib/python3.9/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

COPY ./src ./src
COPY ./start.py ./

CMD ["python3.9", "start.py"]