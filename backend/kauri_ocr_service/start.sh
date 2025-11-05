#!/bin/bash
# KAURI OCR Service - Start script

echo "Starting KAURI OCR Service..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Copying from .env.example"
    cp .env.example .env
    echo "Please edit .env with your configuration before running the service."
    exit 1
fi

# Check if using Docker
if [ "$1" == "docker" ]; then
    echo "Starting with Docker Compose..."
    docker-compose up -d
    echo "Services started!"
    echo "API: http://localhost:8003"
    echo "RabbitMQ Management: http://localhost:15673 (kauri/kauri_password)"
    echo "MinIO Console: http://localhost:9091 (minioadmin/minioadmin)"
    docker-compose logs -f
else
    echo "Starting locally..."

    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Install dependencies
    echo "Installing dependencies..."
    pip install -r requirements.txt

    # Download spaCy model if not present
    if ! python -c "import spacy; spacy.load('fr_core_news_md')" 2>/dev/null; then
        echo "Downloading spaCy French model..."
        python -m spacy download fr_core_news_md
    fi

    # Run migrations
    echo "Running database migrations..."
    alembic upgrade head

    # Start application
    echo "Starting application on http://localhost:8003"
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
fi
