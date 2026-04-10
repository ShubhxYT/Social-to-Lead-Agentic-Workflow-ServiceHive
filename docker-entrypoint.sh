#!/bin/bash
set -e

echo "🚀 Starting AutoStream AI Assistant..."

# Check if knowledge base exists, if not ingest it
if [ ! -d "chroma_db" ] || [ -z "$(ls -A chroma_db 2>/dev/null)" ]; then
    echo "📚 Knowledge base not found. Ingesting..."
    python knowledge_base/ingest.py
    echo "✅ Knowledge base ingestion complete!"
else
    echo "✅ Knowledge base already exists, skipping ingestion."
fi

# Start Streamlit app
echo "🎬 Launching Streamlit app..."
exec streamlit run main.py
