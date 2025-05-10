# syntax=docker/dockerfile:1

FROM python:3.12.3

# Install dependencies (wget) and clean up to reduce image size
# RUN apt-get update && apt-get install -y wget && rm -rf /var/lib/apt/lists/*

# Set working directory inside the container
WORKDIR /app

# Copy project files into container
COPY . .

# Download the GGUF model (if using Phi-3-mini-4k-instruct), exclude otherwise
# RUN wget https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf

# Install Python dependencies
RUN python -m pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

# Run the app with Phi-3-mini-4k-instruct model: app2.py
# CMD ["python", "app2.py"]

# For the Gemini API app: app.py
# Run the following in CLI to set API_KEY:
# docker run -e GOOGLE_API_KEY=your-secret-key my-image
CMD ["python", "app.py"]