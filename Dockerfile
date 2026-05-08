# 1. Use a lightweight Python base image
FROM python:3.11-slim

# 2. Install system tools and Node.js (v20)
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    bash \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 3. Set the working directory inside the container
WORKDIR /app

# 4. Create the exact Python virtual environment that your run.sh script expects
RUN python -m venv .venv
ENV PATH="/app/.venv/bin:$PATH"

# 5. Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy frontend package files and install Node dependencies
COPY src/frontend_validation/stepsis.ai/package*.json ./src/frontend_validation/stepsis.ai/
RUN cd src/frontend_validation/stepsis.ai && npm install

# 7. Copy the entire project into the container
COPY . .

# 8. Ensure bash scripts are executable
RUN chmod +x run.sh
RUN chmod +x src/ingestion/run.sh

# 9. Build the Next.js optimized production app
RUN cd src/frontend_validation/stepsis.ai && npm run build

# 10. Expose Port 3000 for the web server
EXPOSE 3000

# 11. Command to start the application
CMD ["npm", "start", "--prefix", "src/frontend_validation/stepsis.ai"]