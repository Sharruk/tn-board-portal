# ======================================================================
# TN Board Portal — Frontend Dockerfile (Local Development & Testing)
# ======================================================================
FROM node:20-alpine

WORKDIR /app

# Install dependencies first for layer caching
COPY package*.json ./
RUN npm install

# Copy application source
COPY . .

# Expose Vite dev server port
EXPOSE 5000

# Start Vite dev server with host binding
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5000"]
