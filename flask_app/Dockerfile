# syntax=docker/dockerfile:1

FROM python:3.12.3-slim-bullseye

# make the working directory
WORKDIR /app

# copy all files
COPY . .

CMD ["wget", "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"]

RUN python -m pip install --no-cache-dir -r requirements.txt

RUN python app2.py
