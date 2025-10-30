# 💼 Sample Use Cases

Sample implementations demonstrating practical applications of Agent Framework.

## 🔄 Migration Assistant Agent
**Location:** `agent-framework/examples/code_migration/`

An intelligent agent that helps developers migrate code from other frameworks (AutoGen, Semantic Kernel, LangChain) to Microsoft Agent Framework.

### Features:
- 📚 Indexes and searches 200+ official Agent Framework samples
- 🔍 Semantic search across Python and .NET implementations
- 💡 Provides migration guidance with code examples
- 🔗 Links to official GitHub samples and documentation
- 🤖 Interactive DevUI for testing and exploration

### Key Files:
- `agent.py` - Main migration assistant agent
- `indexer.py` - Sample indexing with LLM-generated metadata
- `index.json` - Pre-indexed sample database

### Generate Index (First Time Setup):
To generate the index for the migration assistant:

1. Clone the agent-framework repository:
   ```powershell
   git clone https://github.com/microsoft/agent-framework.git
   ```

2. Run the indexer with the path to the cloned repo:
   ```powershell
   python agent-framework\examples\code_migration\indexer.py C:\path\to\agent-framework
   ```

3. This will create `index.json` in the `code_migration` directory

### Setup:
```powershell
# Ensure environment variables are configured in agent-framework/.env
# Required variables:
# - AZURE_OPENAI_API_KEY
# - AZURE_OPENAI_ENDPOINT
# - AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
```

### Run the agent:
```powershell
cd agent-framework/examples/code_migration
python agent.py
# Opens at http://localhost:8090
```

### Capabilities:
- Search samples by tags (workflow, middleware, tools, etc.)
- Fetch actual code from GitHub repositories
- Get migration patterns for AutoGen, Semantic Kernel, LangChain
- Interactive chat with context-aware responses

---

## 📚 Kids Educational Book Generator
**Location:** `agent-framework/examples/book_generator/`

A sophisticated multi-agent workflow that generates personalized children's educational books with illustrations, complete with parent discussion guides.

### Features:
- 📖 Structured book generation with Pydantic models
- ⚡ Fan-out/fan-in parallel processing for chapters
- 🎨 AI-generated illustrations using Azure OpenAI (gpt-image-1-mini)
- 🔄 Quality assurance with feedback loops
- 💾 Shared state management for artifacts
- 🌐 Unsplash fallback for images

### Key Components:
- Multi-agent collaboration (Structure Planner, Content Generator, QA Reviewer)
- Parallel page generation with image synthesis
- HTML rendering with embedded images
- Iterative refinement with quality feedback

### Setup:
```powershell
# Ensure environment variables are configured in agent-framework/.env
# Required variables:
# - AZURE_OPENAI_API_KEY
# - AZURE_OPENAI_ENDPOINT
# - AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
# - AZURE_OPENAI_IMAGE_DEPLOYMENT (for image generation)
```

### Run the workflow:
```powershell
cd agent-framework/examples/book_generator
python workflow.py
# Opens at http://localhost:8090
```

### Example Topics:
- "How do airplanes fly?"
- "Why is the sky blue?"
- "How do plants grow?"

### Output:
- Complete HTML book with images
- Age-appropriate content (6-year-olds)
- Parent discussion questions
- Activity suggestions

---

## 📋 Prerequisites

All examples require:
1. **Python Environment**: Activate the virtual environment
   ```powershell
   cd agent-framework
   .venv\Scripts\Activate.ps1
   ```

2. **Environment Variables**: Configure `agent-framework/.env` with:
   - `AZURE_OPENAI_API_KEY` - Your Azure OpenAI API key
   - `AZURE_OPENAI_ENDPOINT` - Your Azure OpenAI endpoint URL
   - `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME` - Chat model deployment (e.g., "gpt-4o")
   - `AZURE_OPENAI_IMAGE_DEPLOYMENT` - Image model deployment (for book generator)

3. **Dependencies**: Install required packages
   ```powershell
   pip install -r requirements.txt
   ```

## 🚀 Getting Started

1. Navigate to the example directory
2. Ensure environment variables are configured
3. Run the Python script
4. Access the DevUI at http://localhost:8090
5. Interact with the agent through the web interface

## 📚 Learn More

- [Agent Framework Documentation](https://learn.microsoft.com/en-us/agent-framework/)
- [GitHub Repository](https://github.com/microsoft/agent-framework)
- [Azure OpenAI Service](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
