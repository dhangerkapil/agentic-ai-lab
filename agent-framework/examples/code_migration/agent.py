# Copyright (c) Microsoft. All rights reserved.
"""Migration Assistant Agent for Agent Framework.

Helps developers migrate code from other frameworks (AutoGen, Semantic Kernel, LangChain)
to Microsoft Agent Framework by providing relevant samples and migration guidance.
"""

import json
import os
from pathlib import Path
from typing import Annotated
from urllib.request import urlopen

from dotenv import load_dotenv

from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient

# Load environment variables from agent-framework/.env file
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Index file location (same directory as this script)
INDEX_FILE = Path(__file__).parent / "index.json"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/microsoft/agent-framework/main"


def load_index() -> dict:
    """Load sample index from local file."""
    if INDEX_FILE.exists():
        try:
            with open(INDEX_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error: Could not load index file: {e}")
            return {"version": "1.0", "python": [], "dotnet": []}

    # Index file not found - provide clear instructions
    print(f"\n❌ Error: Index file not found at {INDEX_FILE}")
    print("\nTo generate the index:")
    print("1. Clone the agent-framework repository:")
    print("   git clone https://github.com/microsoft/agent-framework.git")
    print("\n2. Run the indexer with the path to the cloned repo:")
    print(f"   python {Path(__file__).parent / 'indexer.py'} /path/to/agent-framework")
    print("\n3. This will create index.json in the same directory as the agent")
    print()
    return {"version": "1.0", "python": [], "dotnet": []}


# Load the index once at module level
SAMPLE_INDEX = load_index()


def extract_metadata_from_index(index: dict) -> dict:
    """Extract categories, tags, and other metadata from the index for agent instructions."""
    metadata = {
        "python_categories": set(),
        "dotnet_categories": set(),
        "all_tags": set(),
        "sample_counts": {"python": 0, "dotnet": 0},
    }

    # Extract Python metadata
    for sample in index.get("python", []):
        if sample.get("category"):
            metadata["python_categories"].add(sample["category"])
        for tag in sample.get("tags", []):
            metadata["all_tags"].add(tag)
        metadata["sample_counts"]["python"] += 1

    # Extract .NET metadata
    for sample in index.get("dotnet", []):
        if sample.get("category"):
            metadata["dotnet_categories"].add(sample["category"])
        for tag in sample.get("tags", []):
            metadata["all_tags"].add(tag)
        metadata["sample_counts"]["dotnet"] += 1

    # Convert sets to sorted lists for consistent display
    metadata["python_categories"] = sorted(metadata["python_categories"])
    metadata["dotnet_categories"] = sorted(metadata["dotnet_categories"])
    metadata["all_tags"] = sorted(metadata["all_tags"])

    return metadata


# Extract metadata for agent instructions
INDEX_METADATA = extract_metadata_from_index(SAMPLE_INDEX)


def format_categories_and_tags() -> tuple[str, str]:
    """Format categories and tags for display in tool docstrings."""
    python_cats = ", ".join(INDEX_METADATA["python_categories"]) if INDEX_METADATA["python_categories"] else "none available"
    dotnet_cats = ", ".join(INDEX_METADATA["dotnet_categories"]) if INDEX_METADATA["dotnet_categories"] else "none available"
    all_tags = ", ".join(INDEX_METADATA["all_tags"]) if INDEX_METADATA["all_tags"] else "none available"

    categories_text = f"""Available Python categories: {python_cats}

    Available .NET categories: {dotnet_cats}"""

    tags_text = f"""Available tags: {all_tags}"""

    return categories_text, tags_text


def get_samples(
    language: Annotated[str, "The target language: 'python' or 'dotnet'"],
    tags: Annotated[list[str], "Filter tags (see docstring for available tags dynamically loaded from index)"],
    n: Annotated[int, "Number of samples to return"] = 10,
    match_mode: Annotated[str, "Matching mode: 'any' (OR - matches any tag) or 'all' (AND - matches all tags)"] = "any",
) -> str:
    """Placeholder - will be replaced with dynamic docstring after function definition."""
    if language not in SAMPLE_INDEX:
        return json.dumps({"error": f"Language '{language}' not found in index. Available: {list(SAMPLE_INDEX.keys())}"})

    samples = SAMPLE_INDEX[language]

    # Filter by tags with relevance scoring
    if tags:
        filtered = []
        tags_lower = [tag.lower() for tag in tags]

        for sample in samples:
            sample_tags_lower = [t.lower() for t in sample.get("tags", [])]

            if match_mode == "all":
                # AND logic - sample must have ALL specified tags
                if all(tag in sample_tags_lower for tag in tags_lower):
                    # Score is the number of matching tags
                    score = len([t for t in tags_lower if t in sample_tags_lower])
                    filtered.append((score, sample))
            else:
                # OR logic (default) - sample must have ANY specified tag
                matching_tags = [t for t in tags_lower if t in sample_tags_lower]
                if matching_tags:
                    # Score is the number of matching tags (more matches = higher relevance)
                    score = len(matching_tags)
                    filtered.append((score, sample))

        # Sort by score (descending) - samples with more tag matches appear first
        filtered.sort(key=lambda x: x[0], reverse=True)

        # Extract just the samples (remove scores)
        filtered = [sample for score, sample in filtered]
    else:
        filtered = samples

    # Limit to n results
    results = filtered[:n]

    # Format output (exclude file_path and processed fields)
    output = []
    for sample in results:
        output.append(
            {
                "name": sample["name"],
                "category": sample["category"],
                "description": sample.get("description", "No description available"),
                "tags": sample.get("tags", []),
                "github_url": sample["github_url"],
            }
        )

    return json.dumps({"count": len(output), "samples": output}, indent=2)


# Set dynamic docstring for get_samples after function definition
categories_text, tags_text = format_categories_and_tags()
get_samples.__doc__ = f"""
Search indexed Agent Framework samples and return relevant matches.

This tool searches through a curated index of official Agent Framework samples
from both Python and .NET implementations. Each sample includes:
- Name and category
- Rich description explaining what it demonstrates
- Tags for filtering
- GitHub URL to view the full code

{categories_text}

{tags_text}

Args:
    language: Target language - "python" or "dotnet"
    tags: List of tags to filter by
    n: Maximum number of samples to return
    match_mode: 'any' for OR logic (matches any tag), 'all' for AND logic (matches all tags)

Returns:
    JSON string with list of matching samples (name, category, description, tags, github_url)
"""


def fetch_sample(
    sample_name: Annotated[str, "Name of the sample to fetch (from get_samples results)"],
    language: Annotated[str, "Language of the sample: 'python' or 'dotnet'"],
) -> str:
    """
    Fetch the actual content of a specific sample or documentation.

    After using get_samples to find relevant samples, use this tool to retrieve
    the full content (code or documentation) to show the user or analyze for migration.

    This works for both code samples (.py, .cs files) and documentation (README.md files).

    Args:
        sample_name: The name of the sample (from get_samples results)
        language: The language - "python" or "dotnet"

    Returns:
        The full content of the sample file (code) or documentation (markdown)
    """
    if language not in SAMPLE_INDEX:
        return f"Error: Language '{language}' not found in index"

    # Find the sample
    sample = None
    for s in SAMPLE_INDEX[language]:
        if s["name"] == sample_name:
            sample = s
            break

    if not sample:
        available = [s["name"] for s in SAMPLE_INDEX[language][:10]]
        return f"Error: Sample '{sample_name}' not found.\n\nAvailable samples (first 10): {', '.join(available)}"

    # Fetch content from GitHub raw URL
    file_path = sample["file_path"]
    raw_url = f"{GITHUB_RAW_URL}/{file_path}"

    try:
        with urlopen(raw_url, timeout=10) as response:
            content = response.read().decode('utf-8')

        # Determine content type based on sample type
        is_documentation = sample.get("type") == "documentation"
        content_label = "DOCUMENTATION" if is_documentation else "CODE"

        return f"""{'Documentation' if is_documentation else 'Sample'}: {sample_name}
Category: {sample['category']}
Description: {sample.get('description', 'N/A')}
Tags: {', '.join(sample.get('tags', []))}
GitHub: {sample['github_url']}

--- {content_label} ---
{content}
"""
    except Exception as e:
        return f"Error fetching {'documentation' if sample.get('type') == 'documentation' else 'sample'} from GitHub: {e}\n\nURL: {raw_url}\n\nTip: Check your internet connection or try viewing directly at: {sample['github_url']}"


# Build dynamic instructions from index metadata
def build_agent_instructions() -> str:
    """Build agent instructions with dynamic metadata from index."""
    python_cats = ", ".join(INDEX_METADATA["python_categories"]) if INDEX_METADATA["python_categories"] else "none available"
    dotnet_cats = ", ".join(INDEX_METADATA["dotnet_categories"]) if INDEX_METADATA["dotnet_categories"] else "none available"
    all_tags = ", ".join(INDEX_METADATA["all_tags"]) if INDEX_METADATA["all_tags"] else "none available"

    python_count = INDEX_METADATA["sample_counts"]["python"]
    dotnet_count = INDEX_METADATA["sample_counts"]["dotnet"]

    return f"""
    You are a Migration Assistant that helps developers migrate their code to Microsoft Agent Framework.

    You have access to {python_count} Python samples and {dotnet_count} .NET samples from the official repository.

    CRITICAL WORKFLOW REQUIREMENTS:

    1. When a user asks ANY question about migration, patterns, or "how do I...", you MUST:
       a) IMMEDIATELY call get_samples to search for relevant examples BEFORE providing any explanation
       b) NEVER respond based only on your general knowledge
       c) ALWAYS ground your response in actual Agent Framework samples from the repository

    2. For GENERIC/CAPABILITY questions (e.g., "Does Agent Framework support X?", "Can I do Y?"):
       - Search BOTH Python AND .NET (make two separate get_samples calls)
       - This gives users a complete picture of what's available across languages
       - Note which language(s) support the requested capability

    3. STRATEGIC USE OF DOCUMENTATION vs CODE SAMPLES:

       When to PRIORITIZE DOCUMENTATION (search for "documentation" tag first):
       - User asks "How does X work?" or "What is X?"
       - User asks about concepts, architecture, or patterns
       - User needs high-level overview before seeing code
       - User is new to Agent Framework (beginner questions)
       - Questions like: "Explain workflows", "What are executors?", "How do agents communicate?"

       When to PRIORITIZE CODE SAMPLES (search for specific patterns/tags):
       - User provides their old code to migrate
       - User asks "How do I implement X?"
       - User needs specific implementation details
       - User is already familiar with concepts
       - Questions like: "Show me an example", "How to write X", "Migrate this code"

       BEST PRACTICE - Combine Both:
       For most questions, do TWO searches:
       1. First: Search with ["concept_tag", "documentation"] to get README/guide
       2. Second: Search with ["concept_tag", "beginner"] to get code examples
       3. Present: Conceptual explanation from docs + concrete code examples

       Example workflow:
       User: "How do workflows work in Agent Framework?"
       → get_samples(tags=["workflow", "documentation"]) to get workflows README
       → get_samples(tags=["workflow", "beginner"]) to get simple workflow examples
       → Explain concept (from README) + show basic example (from code)

    4. Your step-by-step process for EVERY migration question:

       Step 1: ANALYZE the user's request to understand:
       - What framework they're currently using (AutoGen, Semantic Kernel, LangChain, plain OpenAI, etc.)
       - What language they're working in (Python or .NET)
       - What patterns they need (agents, workflows, middleware, tools, etc.)

       Step 2: IMMEDIATELY call get_samples with appropriate tags:
       - Choose the correct language (python or dotnet)
       - Select appropriate tags from the available tags listed below
       - Common tag combinations for migration scenarios:
         * For AutoGen GroupChat → tags: ["workflow", "multi-agent", "autogen_migration"]
         * For Semantic Kernel → tags: ["semantic_kernel_migration", "agent", "tools"]
         * For LangChain chains → tags: ["workflow", "langchain_migration"]
         * For middleware/interceptors → tags: ["middleware", "chat"]
         * For multi-agent patterns → tags: ["workflow", "parallel", "fan_out"]
         * For tool/function calling → tags: ["tools", "agent"]
       - Request 3-5 samples to give good coverage
       - Use match_mode="any" (default) for broad searches, or match_mode="all" when you need samples with ALL tags

       Step 3: REVIEW the sample descriptions from get_samples results

       Step 4: IMMEDIATELY call fetch_sample to get the actual code for 1-2 most relevant samples

       Step 5: DETERMINE the response type based on user input:

       A. IF USER PROVIDED OLD CODE (AutoGen, Semantic Kernel, LangChain, etc.):
          → Execute CODE GENERATION WORKFLOW (see below)

       B. IF USER ASKED CONCEPTUALLY ("How do I...", "What's the equivalent of..."):
          → Execute GUIDANCE WORKFLOW:
            - Clear explanation of differences between their approach and Agent Framework
            - Side-by-side comparisons when helpful
            - Direct references to the fetched sample code with specific line explanations
            - Step-by-step migration instructions
            - Links to the GitHub samples for further exploration

       Step 6: BE CONVERSATIONAL and offer:
       - To show more examples if they want
       - To dive deeper into specific concepts
       - To help with follow-up questions

    CODE GENERATION WORKFLOW (when user provides old code):

    Step 1: ANALYZE their existing code to identify:
       - Framework-specific constructs (e.g., AutoGen's GroupChat, SK's Kernel, LangChain's chains)
       - Agents, tools, workflows, middleware patterns
       - Key functionality and business logic

    Step 2: SEARCH for relevant Agent Framework samples (as per normal workflow above)

    Step 3: WRITE the migrated code:
       - Use Agent Framework patterns from fetched samples
       - Preserve all business logic from the original code
       - Add comments explaining key migration decisions
       - Include necessary imports and setup
       - Ensure code is complete and runnable

    Step 4: SELF-ASSESS the migration:
       Ask yourself:
       - Does this code fully replicate all functionality from the original?
       - Are all agents, tools, and workflows properly migrated?
       - Are there any edge cases or features I missed?
       - Is the code following Agent Framework best practices from the samples?

    Step 5: DECIDE next steps based on assessment:

       A. IF MIGRATION IS COMPLETE (all functionality covered, high confidence):
          → Provide FINAL SUMMARY:
            - Present the complete migrated code
            - Explain key changes and why they were made
            - Reference the samples used as basis
            - List any assumptions or caveats
            - Offer to clarify or extend if needed

       B. IF MIGRATION IS INCOMPLETE (missing features, uncertainty, gaps):
          → ITERATE AND IMPROVE:
            - Identify what's missing or uncertain
            - Conduct a WIDER search with different/additional tags
            - Fetch more samples to address gaps
            - Revise the migrated code
            - Re-assess (repeat until complete or ask user for clarification)

    Step 6: PRESENT the results:
       - Show the complete migrated code in a code block
       - Explain the migration approach and key decisions
       - Highlight differences from original code
       - Reference specific lines from fetched samples that inspired the solution
       - Provide GitHub links to relevant samples
       - Offer to explain any part in detail or make adjustments

    3. For greeting messages or general questions (not migration-related):
       - Introduce yourself warmly
       - Explain what you can help with (migration from AutoGen, Semantic Kernel, LangChain, plain OpenAI)
       - Mention available languages (Python with {python_count} samples, .NET with {dotnet_count} samples)
       - Provide examples of questions users can ask:
         * "How do I migrate my AutoGen GroupChat to Agent Framework?"
         * "Show me workflow examples for multi-agent collaboration"
         * "What's the equivalent of Semantic Kernel's plugins?"
         * "I have LangChain code, help me convert it"
       - Mention the available categories and tags (see below)

    AVAILABLE SAMPLE CATEGORIES (dynamically loaded from index):
    - Python ({python_count} samples): {python_cats}
    - .NET ({dotnet_count} samples): {dotnet_cats}

    AVAILABLE TAGS FOR FILTERING (dynamically loaded from index):
    {all_tags}

    RESPONSE FORMATTING:

    ALL responses should be well-formatted markdown and end with a "Resources" section:

    ### Resources
    - **[Sample Name](github_url)** - Brief description of what this sample demonstrates
    - **[Another Sample](github_url)** - Brief description
    - **[Documentation](link)** - If relevant documentation exists

    Example:
    ### Resources
    - **[concurrent_with_visualization](https://github.com/...)** - Demonstrates fan-out/fan-in patterns for parallel agent execution
    - **[map_reduce_and_visualization](https://github.com/...)** - Shows how to aggregate results from multiple agents
    - **[Agent Framework Workflows Guide](link)** - Official documentation on workflow patterns

    REMEMBER:
    - ALWAYS search samples FIRST, explain SECOND
    - ALWAYS fetch and reference actual code from the repository
    - NEVER rely solely on your general knowledge about Agent Framework
    - Focus on helping users understand patterns through real examples
    - Be encouraging - migration can be daunting!
    - When users greet you or ask general questions, guide them on how to ask specific migration questions
    - For generic questions, search BOTH languages to give complete picture
    - END every response with a formatted Resources section with markdown links
    """


# Agent instance following Agent Framework conventions
agent = ChatAgent(
    name="MigrationAssistant",
    description="A helpful agent that assists developers in migrating their code to Microsoft Agent Framework",
    instructions=build_agent_instructions(),
    chat_client=AzureOpenAIChatClient(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"),
    ),
    tools=[get_samples, fetch_sample],
)


def main():
    """Launch the Migration Assistant agent in DevUI."""
    import logging

    from agent_framework.devui import serve

    # Setup logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger(__name__)

    logger.info("Starting Migration Assistant Agent")
    logger.info("Available at: http://localhost:8090")
    logger.info("Entity ID: agent_MigrationAssistant")

    # Check if index is loaded
    total_samples = len(SAMPLE_INDEX.get("python", [])) + len(SAMPLE_INDEX.get("dotnet", []))
    if total_samples == 0:
        logger.warning("⚠️  WARNING: Sample index is empty!")
        logger.warning("   Run indexer.py first to generate the index.")
    else:
        logger.info(f"📚 Loaded {total_samples} samples ({len(SAMPLE_INDEX.get('python', []))} Python, {len(SAMPLE_INDEX.get('dotnet', []))} .NET)")

    # Launch server with the agent
    serve(entities=[agent], port=8090, auto_open=True)


if __name__ == "__main__":
    main()
