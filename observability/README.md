# AI Evaluation with Azure AI Foundry

This directory contains notebooks for evaluating AI models and applications using Azure AI Foundry's evaluation capabilities.

## Prerequisites

Before running the evaluations, you'll need:

1. **Azure AI Services**:
   - An Azure subscription
   - Azure OpenAI Service with a deployed model (gpt-4, gpt-35-turbo, etc.)
   - Azure AI Foundry project (for cloud evaluations)

2. **Environment Setup**:
   - Create a `.env` file in this directory with the following variables:
     ```
     # Azure OpenAI Configuration
     AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
     AZURE_OPENAI_API_KEY=your_api_key
     AZURE_OPENAI_DEPLOYMENT=your_deployment_name

     # Azure AI Foundry Project Endpoint
     AI_FOUNDRY_PROJECT_ENDPOINT=your_ai_foundry_project_endpoint
     ```

3. **Required Python Packages**:
   ```
   pip install azure-ai-evaluation azure-ai-projects azure-identity python-dotenv
   ```

## Notebook Contents

### 1. Evaluation.ipynb

Learn how to evaluate generative AI models using:

- **Local evaluation**: Run evaluations on your local machine using built-in metrics
- **Cloud evaluation**: Submit evaluation jobs to Azure AI Foundry for scalable processing
- **Multiple metrics**: Measure quality aspects like F1 score, relevance, groundedness, coherence
- **Risk & Safety**: Assess potential risks using safety evaluators

## Running the Evaluations

1. **Local Evaluation**:
   - Works without any cloud resources
   - Provides basic metrics like F1 score
   - With Azure OpenAI configuration, enables AI-assisted evaluators

2. **Cloud Evaluation**:
   - Requires a valid Azure AI Foundry project connection string
   - Scales to large datasets
   - Provides visualization in the Azure AI Foundry portal
   - Supports all built-in and custom evaluators

## Key Features

- **Multiple Evaluation Types**: NLP-based and AI-assisted evaluators
- **Robust Error Handling**: Fallback mechanisms when services are unavailable
- **Flexible Authentication**: Supports DefaultAzureCredential and InteractiveBrowserCredential
- **Comprehensive Metrics**: Quality and safety evaluations with detailed results

## Troubleshooting

1. **Missing Packages**:
   - The notebook will attempt to install missing packages
   - If that fails, manually install them using pip

2. **Authentication Issues**:
   - The notebook will try DefaultAzureCredential first
   - If that fails, it will fall back to InteractiveBrowserCredential

3. **Environment Variables**:
   - If environment variables are missing, create or update your .env file
   - Ensure your Azure OpenAI deployment name is correct

## Additional Resources

- [Azure AI Foundry Documentation](https://learn.microsoft.com/azure/ai-foundry/)
- [Azure AI Evaluation SDK](https://learn.microsoft.com/python/api/azure-ai-evaluation/azure.ai.evaluation)
- [Evaluating Generative AI Applications](https://learn.microsoft.com/azure/ai-foundry/how-to/evaluate-generative-ai-app)
