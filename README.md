# AutoStream Social-to-Lead Agent

A LangGraph-powered conversational AI agent for **AutoStream**, a fictional SaaS video editing platform for content creators. The agent classifies user intent, answers product questions via RAG, and captures qualified leads only after collecting all required information.

---

## Setup & Run

### Prerequisites
- Python 3.12+
- A free Groq API key from [console.groq.com](https://console.groq.com)

### Installation

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd <repo-dir>

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Open .env and set GROQ_API_KEY=<your key>

# 5. Ingest the knowledge base (one-time step)
python knowledge_base/ingest.py

# 6. Launch the app
streamlit run main.py
```

The Streamlit UI opens at `http://localhost:8501`.

---

## Docker Deployment

### Local Testing

```bash
# 1. Build and run with Docker Compose
docker-compose up -d

# 2. Access the app at http://localhost:8501

# 3. View logs
docker logs -f servicehive-app

# 4. Stop the container
docker-compose down
```

**Note:** The first run automatically ingests the knowledge base. This may take a few minutes.

### Deploy to Coolify

1. **Push to Git:**
   ```bash
   git add .
   git commit -m "Docker configuration"
   git push
   ```

2. **In Coolify Dashboard:**
   - Click "Create New Service" → "Docker Compose"
   - Connect your Git repository
   - Coolify auto-detects `docker-compose.yml`
   - Add environment variable: `GROQ_API_KEY=<your-key>`
   - Deploy!

3. **Access:** Coolify provides a public URL to your app

**For detailed deployment guidance**, see [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Architecture

The agent is built on **LangGraph**, a stateful graph execution framework from LangChain. LangGraph was chosen because it supports directed, conditional, and cyclical workflows — essential for multi-turn lead collection where the agent must loop back when user data is incomplete. A simple chain or basic prompt loop cannot cleanly model this branching logic.

**State management** uses a custom `AgentState` TypedDict holding the full message history, detected intent, lead fields (`lead_name`, `lead_email`, `lead_platform`), and a `lead_captured` flag. LangGraph's `add_messages` reducer safely accumulates messages across turns without overwriting history.

**Intent Classification** routes each user message to one of two paths: `rag_respond` for greetings and product inquiries, or `lead_collect` for high-intent users. Once collection begins, the in-progress lead fields act as a sticky signal — any subsequent short reply is routed back to `lead_collect` rather than being misclassified.

**RAG** uses a local Chroma vector store populated by `knowledge_base/ingest.py`. Documents are embedded with HuggingFace `all-MiniLM-L6-v2` and retrieved by cosine similarity at query time. Retrieved context is injected into the LLM system prompt.

**Lead Capture** is strictly gated: `mock_lead_capture()` is called only once all three fields (name, email, platform) are confirmed. The LLM acts as a structured extractor across turns, and the routing function guards the `capture_lead` node.

---

## WhatsApp Webhook Integration

To deploy this agent on WhatsApp:

1. **Register a WhatsApp Business App** via [Meta for Developers](https://developers.facebook.com). Obtain a phone number ID and access token.

2. **Build a webhook endpoint** using FastAPI or Flask. Meta will `POST` incoming messages as JSON payloads to this URL.

3. **Verify the webhook** by handling the `GET /webhook` challenge-response that Meta sends during setup (return the `hub.challenge` value).

4. **Route messages to the agent**: Extract the user's text from `payload["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]`, append it as a `HumanMessage` to the persisted `AgentState` (keyed by `wa_id`), call `graph.invoke(state)`, and send the last `AIMessage` back via the WhatsApp Cloud API.

5. **Persist state** between webhook calls using Redis or a relational database keyed by the user's WhatsApp phone number (`wa_id`).

```python
# Pseudocode — FastAPI webhook handler
@app.post("/webhook")
async def webhook(payload: dict):
    wa_id   = payload["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    text    = payload["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]

    state = load_state(wa_id)               # deserialise from Redis/DB
    state["messages"].append(HumanMessage(content=text))
    new_state = graph.invoke(state)
    save_state(wa_id, new_state)            # persist updated state

    reply = new_state["messages"][-1].content
    send_whatsapp_message(wa_id, reply)     # WhatsApp Cloud API call
```
