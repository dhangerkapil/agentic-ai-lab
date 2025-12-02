### 🎯 PRIORITIZE MICROSOFT OFFICIAL DOCUMENTATION - MANDATORY
 
**🔍 ALWAYS consult Microsoft Learn first for Azure AI Foundry and Python guidance:**
 
- **🚨 BEFORE generating Azure AI code**: Use `mcp_microsoft_doc_microsoft_docs_search` to find current best practices
- **🚨 BEFORE implementing AI agents**: Search Microsoft Learn for official Azure AI Agent Service patterns
- **🚨 BEFORE using Azure AI SDKs**: Verify API usage, authentication methods, and SDK version compatibility
- **🚨 BEFORE troubleshooting authentication issues**: Check Microsoft Learn for Azure AD/credential chain patterns
- **🚨 BEFORE working with Azure OpenAI**: Verify endpoint formats, API versions, and authentication scopes
- **🚨 BEFORE using Azure CLI**: Verify command syntax, parameters, and examples in Microsoft documentation
- **🚨 BEFORE implementing RAG patterns**: Check Microsoft Learn for Azure AI Search and vector store integration

**🚫 NEVER use AzureOpenAI client directly**:
- **ALWAYS use** `AIProjectClient.get_openai_client()` instead of importing `AzureOpenAI`
- The `AIProjectClient` method handles authentication, endpoints, and API versions automatically
- This is the official recommended pattern for Azure AI Foundry projects
- Direct `AzureOpenAI` usage bypasses AI Foundry's built-in capabilities and authentication
 
**Examples of when to search Microsoft Learn:**
- Azure AI Foundry project setup and configuration
- Azure AI Agent Service with code interpreter and file search tools
- AIProjectClient.get_openai_client() usage patterns
- Python SDK usage for azure-ai-projects, azure-ai-inference, azure-ai-agents
- Azure AI Search integration patterns
- Cognitive Services authentication and endpoint configuration
- Observability and evaluation with Azure Application Insights
- Azure CLI commands for AI services provisioning
- Terraform/Bicep for Azure AI infrastructure
 
**Search Query Examples:**
```
"Azure AI Foundry Python SDK authentication"
"Azure AI Agent Service code interpreter best practices"
"AIProjectClient get_openai_client usage"
"Azure AI projects AIProjectClient usage"
"Azure AD authentication for Cognitive Services"
"Azure AI Search vector store integration"
"Azure Application Insights Python telemetry"
"Azure CLI ai commands reference"
"Terraform Azure AI Foundry resources"
```
 
**Benefits:**
- ✅ **Current information**: Always get the latest Azure AI SDK versions and API patterns
- ✅ **Official guidance**: Use AIProjectClient instead of direct AzureOpenAI client
- ✅ **Security focus**: Follow Microsoft's authentication best practices (Azure AD over API keys)
- ✅ **Performance optimization**: Use recommended patterns for agents, RAG, and inference
- ✅ **Compatibility**: Ensure SDK versions work with Azure AI Foundry (e.g., azure-ai-projects >=2.0.0b2)
- ✅ **Accurate syntax**: Use verified Python SDK methods and parameters
- ✅ **Best practices**: Follow Microsoft's recommended patterns for AI workloads