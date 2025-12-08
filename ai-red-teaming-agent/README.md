# AI Red Teaming Agent for Generative AI Applications

This sample demonstrates how to use Azure AI Evaluation's RedTeam functionality to assess the safety and resilience of AI systems against adversarial prompt attacks.

## Objective

AI Red Teaming Agent leverages Risk and Safety Evaluations to help identify potential safety issues across different risk categories (violence, hate/unfairness, sexual content, self-harm) combined with attack strategies of varying complexity levels from PyRIT, Microsoft AI Red Teaming team's open framework for automated AI red teaming.

## Time

You should expect to spend about 30-45 minutes running the notebook. Execution time will vary based on the number of risk categories, attack strategies, and complexity levels you choose to evaluate.

## Prerequisites

- Azure subscription
- Azure AI Foundry project with Azure OpenAI model deployment
- Storage account with Microsoft Entra ID authentication enabled
- Storage Blob Data Contributor role for both the AI Foundry project and your user account
- Python 3.10+ environment

## Setup

1. Install the required packages:

   ```bash
   pip install azure-ai-evaluation[redteam] 
   ```

   > **⚠️ Important Dependency Conflict:** The `azure-ai-evaluation[redteam]` package depends on `pyrit` which requires `aiofiles==23.2.1`, but `agent-framework-core` requires `aiofiles>=24.1.0`. This means:
   > - Installing red teaming packages will **downgrade** `aiofiles` to version 23.2.1
   > - This may **break agent-framework notebooks** that depend on the newer version
   > - **Recommendation**: Complete agent-framework labs before installing red teaming dependencies, or use a separate virtual environment for this lab

2. Set up your environment variables in a .env file:

   ```env
   # Azure AI Project Connection String
   AZURE_AI_PROJECT_ENDPOINT="https://your-aifoundry-endpoint-name.services.ai.azure.com/"
   MODEL_DEPLOYMENT_NAME="gpt-4o-mini"
   MODEL_API_VERSION="2024-12-01-preview"
   TENANT_ID="your-tenant-id"
   ```

3. Authenticate to Azure using `az login` in your terminal before running the notebook.

## Key Concepts

The AI Red Teaming Agent assesses AI systems across multiple dimensions:

### Risk Categories

- **Violence**: Content that describes or promotes violence
- **Hate and Unfairness**: Content containing hate speech or unfair bias
- **Sexual**: Inappropriate sexual content
- **Self-Harm**: Content related to self-harm behaviors

### Attack Strategies

- **Text Transformation**: Base64, ROT13, Binary, Morse code, etc.
- **Character Manipulation**: Character spacing, swapping, Leetspeak
- **Encoding Techniques**: ASCII art, Unicode confusables
- **Jailbreak Attempts**: Special prompts designed to bypass AI safeguards

### Complexity Levels

- **Baseline**: Standard attacks without any transformation strategy
- **Easy**: Simple attack patterns
- **Moderate**: More sophisticated attacks
- **Difficult**: Complex, layered attack strategies

## Using the Notebook

The notebook provides three main examples:

1. **Basic Example**: A simple demonstration using a fixed response callback
2. **Intermediary Example**: Testing a model configuration with Azure OpenAI model
3. **Advanced Example**: Using a callback function that wraps Azure OpenAI API calls to evaluate against multiple attack strategies

The notebook uses the Azure AI Projects SDK to securely access Azure OpenAI models through the project connection string, eliminating the need for direct API key management.

### Analysis Features

- **Attack Success Rate (ASR)**: Measures the percentage of attacks that successfully elicit harmful content
- **Risk Category Analysis**: Shows which content categories are most vulnerable
- **Attack Strategy Assessment**: Identifies which techniques are most effective
- **Detailed Conversation Inspection**: Examines specific conversations including prompts and responses

## Troubleshooting

### Common Issues

- **Content harm capability not supported**: This error may occur in certain Azure regions. The scan will still complete but some evaluations may be skipped.
- **Authentication errors**: Ensure you have completed `az login` and have the necessary permissions in your Azure AI Foundry project.
- **Missing environment variables**: Verify that all required environment variables are set in your .env file.

## Next Steps

After running the AI red teaming scan:

1. **Mitigation**: Strengthen your model's guardrails against identified attack strategies
2. **Continuous Testing**: Implement regular AI red teaming scans as part of your development lifecycle
3. **Custom Strategies**: Develop custom attack strategies for your specific use cases
4. **Safety Layers**: Consider adding additional safety layers like Azure AI Content Safety filters or safety system messages

## Additional Resources

- Learn more about Azure AI Foundry Evaluations
- Learn more about how to run an automated AI red teaming scan in Azure documentation
- Learn more about how the AI Red Teaming Agent works and what it covers in the concept documentation
