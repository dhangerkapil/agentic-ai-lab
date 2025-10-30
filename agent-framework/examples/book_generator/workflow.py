# built with microsoft/agent-framework 

"""Kids Educational Book Generator Workflow.

This workflow demonstrates:
- Structured outputs with Pydantic models
- Fan-out/fan-in parallel processing
- Shared state for artifact storage
- Multi-agent collaboration for educational content creation

Use case: Generate personalized children's educational books based on topics of interest.
A parent enters a topic (e.g., "How do airplanes fly?"), and the workflow creates a complete
children's book with age-appropriate content, parent discussion guides, and images.
"""

import asyncio
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from agent_framework import WorkflowBuilder, WorkflowContext, executor
from agent_framework.azure import AzureOpenAIChatClient
from pydantic import BaseModel, Field
from typing_extensions import Never

# Load environment variables from agent-framework/.env file
load_dotenv(Path(__file__).parent.parent.parent / ".env")


# ============================================================================
# Pydantic Models for Structured Outputs
# ============================================================================


class PagePlan(BaseModel):
    """Structure planner output for a single page."""

    page_number: int
    title: str = Field(description="Catchy title for this page")
    concept: str = Field(description="Main learning concept for this page")
    story_element: str = Field(description="Story/narrative element to make it engaging")
    image_prompt: str = Field(description="Description for image generation (keywords)")


class BookStructure(BaseModel):
    """Complete book structure from planner."""

    book_title: str = Field(description="Overall book title")
    target_age: int = Field(default=6, description="Target age for the book")
    learning_objectives: list[str] = Field(description="What the child will learn")
    pages: list[PagePlan] = Field(description="5-6 pages for the book")


class PageContent(BaseModel):
    """Content generator output for a single page."""

    page_number: int
    kid_text: str = Field(description="2-3 simple sentences for 6-year-old to read/hear")
    parent_guide: str = Field(
        description="Detailed discussion points, questions to ask, and deeper explanations for parent"
    )
    key_vocabulary: list[str] = Field(description="Important words to explain to the child")


class AllPagesContent(BaseModel):
    """Content for all pages in the book."""

    pages: list[PageContent]


class QAResult(BaseModel):
    """Book QA validation result."""

    approved: bool
    overall_score: int = Field(ge=0, le=100, description="Quality score 0-100")
    issues: list[str] = Field(default_factory=list, description="Issues found")
    strengths: list[str] = Field(default_factory=list, description="What works well")
    recommendations: list[str] = Field(default_factory=list, description="Improvement suggestions")


class CompletePage(BaseModel):
    """A complete page with all content."""

    page_number: int
    title: str
    concept: str
    kid_text: str
    parent_guide: str
    key_vocabulary: list[str]
    image_url: str


class FinalBook(BaseModel):
    """Final compiled book."""

    title: str
    topic: str
    target_age: int
    learning_objectives: list[str]
    pages: list[CompletePage]
    qa_score: int


# ============================================================================
# Message Types for Workflow Communication
# ============================================================================


@dataclass
class ContentGeneratorInput:
    """Input message for content generator."""

    structure: BookStructure


@dataclass
class ImageGeneratorInput:
    """Input message for image generator."""

    structure: BookStructure


@dataclass
class AllPagesContentResult:
    """Result from content generator with all page content."""

    pages_content: dict[int, PageContent]  # page_number -> PageContent


@dataclass
class AllImagesResult:
    """Result from image generator with all images."""

    page_images: dict[int, str]  # page_number -> image_url


@dataclass
class BookQAInput:
    """Input for book QA - aggregated from fan-in."""

    structure: BookStructure
    pages_content: dict[int, PageContent]
    page_images: dict[int, str]


# ============================================================================
# Executor: Extract BookStructure from Agent Response
# ============================================================================


@executor(id="extract_structure")
async def extract_structure(response: Any, ctx: WorkflowContext[BookStructure]) -> None:
    """Extract BookStructure from agent response and store in shared state."""
    from agent_framework import AgentExecutorResponse

    # Extract text from AgentExecutorResponse
    if isinstance(response, AgentExecutorResponse):
        text = response.agent_run_response.text
    else:
        raise TypeError(f"Expected AgentExecutorResponse, got {type(response)}")

    # Parse the structured output
    structure = BookStructure.model_validate_json(text)

    # Store in shared state
    await ctx.set_shared_state("book:structure", structure)

    # Send to next executors
    await ctx.send_message(structure)


# ============================================================================
# Executor: Content Generator (processes all pages internally)
# ============================================================================


@executor(id="content_generator")
async def content_generator(
    structure: BookStructure, ctx: WorkflowContext[AllPagesContentResult]
) -> None:
    """Generate educational content for all pages in parallel.

    Internally uses asyncio.gather to process all pages simultaneously.
    On retry (if QA feedback exists), incorporates QA recommendations.
    """
    # Check if this is a retry (QA feedback exists)
    qa_feedback: QAResult | None = None
    try:
        qa_feedback = await ctx.get_shared_state("book:qa_feedback")
    except KeyError:
        pass  # First run, no feedback yet

    iterations = await ctx.get_shared_state("qa_iterations") or 0

    if qa_feedback and iterations > 1:
        print(f"\n🔄 Retry attempt {iterations - 1}: Incorporating QA feedback...")
        print(f"   Issues: {', '.join(qa_feedback.issues[:2])}")  # Show first 2 issues

    # Create content generator agent with structured output
    chat_client = AzureOpenAIChatClient(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "gpt-4o"),
    )

    content_gen_agent = chat_client.create_agent(
        name="ContentGenerator",
        instructions="""You are a children's book writer specializing in educational content for 6-year-olds.

Kid Text (2-3 simple sentences):
- Maximum 10 words per sentence
- Use story/narrative format with engaging characters
- Avoid complex words (or explain them simply inline)
- Make it fun and memorable!

Parent Guide:
- Provide 3-5 detailed discussion points
- Suggest open-ended questions to ask the child
- Give deeper explanations of the concept with examples
- Include real-world connections and activities to try together
- Reference additional learning resources (books, videos, experiments)

Key Vocabulary:
- List 2-4 important words from this page
- These will be highlighted for parents to explain""",
        response_format=PageContent,
    )

    async def generate_page_content(page_plan: PagePlan) -> PageContent:
        """Generate content for a single page."""
        prompt = f"""Create content for page {page_plan.page_number}:

Title: {page_plan.title}
Concept: {page_plan.concept}
Story Element: {page_plan.story_element}

Generate engaging kid-friendly text and a helpful parent guide."""

        # Add QA feedback if this is a retry
        if qa_feedback and not qa_feedback.approved:
            prompt += f"""

IMPORTANT - Previous version had issues. Please address this feedback:
Issues: {'; '.join(qa_feedback.issues)}
Recommendations: {'; '.join(qa_feedback.recommendations)}
"""

        result = await content_gen_agent.run(prompt)
        content = PageContent.model_validate_json(result.text)
        # Ensure page number matches
        content.page_number = page_plan.page_number
        return content

    # Process all pages in parallel using asyncio.gather
    page_contents = await asyncio.gather(*[generate_page_content(page) for page in structure.pages])

    # Create dictionary of page_number -> PageContent
    pages_content_dict = {content.page_number: content for content in page_contents}

    # Store in shared state for QA
    await ctx.set_shared_state("book:pages_content", pages_content_dict)

    # Send result to fan-in
    await ctx.send_message(AllPagesContentResult(pages_content=pages_content_dict))


# ============================================================================
# Image Generation: Azure OpenAI gpt-image-1-mini with Unsplash Fallback
# ============================================================================


async def generate_ai_image(prompt: str, page_number: int) -> str | None:
    """Generate an image using Azure OpenAI gpt-image-1-mini model (async).

    Args:
        prompt: Image description/prompt
        page_number: Page number for file naming

    Returns:
        File path to generated image, or None if generation failed
    """
    try:
        from openai import AzureOpenAI
        import requests

        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = os.getenv("AZURE_OPENAI_IMAGE_DEPLOYMENT", "gpt-image-1-mini")
        
        if not api_key or not endpoint:
            print("⚠️  Azure OpenAI credentials not set, skipping AI image generation")
            return None

        # Run the Azure OpenAI API call in a thread pool
        def _sync_generate() -> str | None:
            # Initialize Azure OpenAI client
            client = AzureOpenAI(
                api_version="2024-02-01",
                azure_endpoint=endpoint,
                api_key=api_key,
            )

            # Generate image with gpt-image-1-mini
            enhanced_prompt = f"Create a colorful, kid-friendly illustration for a children's book: {prompt}"
            
            print(f"🎨 Calling Azure OpenAI image generation for page {page_number}...")
            result = client.images.generate(
                model=deployment,
                prompt=enhanced_prompt,
                n=1,
                size="1024x1024",  # Supported sizes: 1024x1024, 1792x1024, 1024x1792
            )

            # Debug: Check the result structure
            print(f"   Result type: {type(result)}")
            print(f"   Result data: {result.data if hasattr(result, 'data') else 'No data attribute'}")
            
            # Get the generated image URL
            if not result.data or len(result.data) == 0:
                print(f"⚠️  No image data received from Azure OpenAI for page {page_number}")
                return None
                
            image_url = result.data[0].url if hasattr(result.data[0], 'url') else None
            
            # Also check for b64_json format
            if not image_url and hasattr(result.data[0], 'b64_json'):
                # Image is returned as base64
                import base64
                b64_data = result.data[0].b64_json
                image_data = base64.b64decode(b64_data)
                
                # Save image file directly
                file_name = f"generated_page_{page_number}.png"
                file_path = os.path.join(os.path.dirname(__file__), file_name)

                with open(file_path, "wb") as f:
                    f.write(image_data)

                print(f"✅ AI image generated (base64): {file_name}")
                return file_path
            
            if not image_url:
                print(f"⚠️  No image URL received from Azure OpenAI for page {page_number}")
                print(f"   Available attributes: {dir(result.data[0])}")
                return None

            # Download the image from URL
            print(f"   Downloading image from URL...")
            response = requests.get(image_url)
            response.raise_for_status()

            # Save image file
            file_name = f"generated_page_{page_number}.png"
            file_path = os.path.join(os.path.dirname(__file__), file_name)

            with open(file_path, "wb") as f:
                f.write(response.content)

            print(f"✅ AI image generated: {file_name}")
            return file_path

        # Run in thread pool to avoid blocking the event loop
        return await asyncio.to_thread(_sync_generate)

    except ImportError as e:
        print(f"⚠️  Required package not installed: {e}")
        print("   Install with: pip install openai requests")
        return None
    except Exception as e:
        print(f"❌ Error generating AI image for page {page_number}: {type(e).__name__}: {e}")
        return None


def extract_keywords(image_prompt: str) -> list[str]:
    """Extract meaningful keywords from image prompt."""
    stop_words = {"a", "an", "the", "is", "are", "in", "on", "at", "for", "with", "of"}
    words = image_prompt.lower().replace(",", " ").split()
    keywords = [w for w in words if w not in stop_words and len(w) > 2]
    return keywords[:3]  # Limit to 3 keywords


def generate_unsplash_image(image_prompt: str) -> str:
    """Generate Unsplash URL as fallback."""
    keywords = extract_keywords(image_prompt)
    seed = random.randint(1, 1000)
    return f"https://source.unsplash.com/800x600/?{','.join(keywords)}&sig={seed}"


# ============================================================================
# Executor: Image Generator (processes all pages internally)
# ============================================================================


@executor(id="image_generator")
async def image_generator(structure: BookStructure, ctx: WorkflowContext[AllImagesResult]) -> None:
    """Generate images for all pages in parallel.

    Tries Azure OpenAI gpt-image-1-mini first, falls back to Unsplash if unavailable.
    """

    async def generate_page_image(page_plan: PagePlan) -> tuple[int, str]:
        """Generate image for a single page with AI or fallback."""

        # Try AI image generation first (now async)
        print(f"🎨 Generating image for page {page_plan.page_number}...")
        ai_image_path = await generate_ai_image(page_plan.image_prompt, page_plan.page_number)

        if ai_image_path:
            # Use local file path (will be embedded in HTML or can be referenced)
            image_url = f"file://{os.path.abspath(ai_image_path)}"
        else:
            # Fallback to Unsplash
            print(f"📸 Using Unsplash fallback for page {page_plan.page_number}")
            image_url = generate_unsplash_image(page_plan.image_prompt)

        # Simulate API delay for Unsplash
        if not ai_image_path:
            await asyncio.sleep(0.5)

        return page_plan.page_number, image_url

    # Process all pages in parallel using asyncio.gather
    image_results = await asyncio.gather(*[generate_page_image(page) for page in structure.pages])

    # Create dictionary of page_number -> image_url
    page_images_dict = {page_num: url for page_num, url in image_results}

    # Store in shared state for QA
    await ctx.set_shared_state("book:page_images", page_images_dict)

    # Send result to fan-in
    await ctx.send_message(AllImagesResult(page_images=page_images_dict))


# ============================================================================
# Executor: Fan-in Aggregator (prepares data for QA)
# ============================================================================


@executor(id="qa_aggregator")
async def qa_aggregator(
    messages: list[AllPagesContentResult | AllImagesResult], ctx: WorkflowContext[Any]
) -> None:
    """Aggregate content and images from fan-in for QA review."""
    from agent_framework import AgentExecutorRequest, ChatMessage, Role

    # Extract from aggregated messages
    content_result = next(m for m in messages if isinstance(m, AllPagesContentResult))
    images_result = next(m for m in messages if isinstance(m, AllImagesResult))

    # Get structure from shared state
    structure: BookStructure = await ctx.get_shared_state("book:structure")

    # Build a comprehensive prompt for the QA agent
    qa_prompt = f"""Review this complete children's educational book:

**Book Title:** {structure.book_title}
**Target Age:** {structure.target_age}
**Learning Objectives:**
{chr(10).join(f"- {obj}" for obj in structure.learning_objectives)}

**Pages:**
"""

    for page_plan in structure.pages:
        page_num = page_plan.page_number
        content = content_result.pages_content[page_num]
        image_url = images_result.page_images[page_num]

        qa_prompt += f"""

--- Page {page_num}: {page_plan.title} ---
Concept: {page_plan.concept}
Story Element: {page_plan.story_element}

Kid Text:
{content.kid_text}

Parent Guide:
{content.parent_guide}

Key Vocabulary: {', '.join(content.key_vocabulary)}
Image: {image_url}
"""

    # Send as AgentExecutorRequest for the QA agent
    await ctx.send_message(
        AgentExecutorRequest(messages=[ChatMessage(Role.USER, text=qa_prompt)], should_respond=True)
    )


# ============================================================================
# Executor: Extract QA Result from Agent Response
# ============================================================================


@executor(id="extract_qa_result")
async def extract_qa_result(response: Any, ctx: WorkflowContext[QAResult | BookStructure]) -> None:
    """Extract QAResult from book QA agent response and handle retry logic."""
    from agent_framework import AgentExecutorResponse

    # Extract text from AgentExecutorResponse
    if isinstance(response, AgentExecutorResponse):
        text = response.agent_run_response.text
    else:
        raise TypeError(f"Expected AgentExecutorResponse, got {type(response)}")

    # Parse the structured output
    qa_result = QAResult.model_validate_json(text)

    # Store QA feedback in shared state for potential retry
    await ctx.set_shared_state("book:qa_feedback", qa_result)

    # Track iteration count
    iterations = await ctx.get_shared_state("qa_iterations") or 0
    await ctx.set_shared_state("qa_iterations", iterations + 1)

    max_iterations = 3

    # Decision logic: approved OR max iterations reached → compile
    if qa_result.approved or iterations >= max_iterations:
        if iterations >= max_iterations and not qa_result.approved:
            print(f"\n⚠️  Max retry attempts ({max_iterations}) reached. Proceeding with current version.")
        # Send to compiler
        await ctx.send_message(qa_result, target_id="book_compiler")
    else:
        # Not approved and retries remaining → trigger regeneration
        print(f"\n🔄 QA not approved (score: {qa_result.overall_score}/100). Retrying... (attempt {iterations}/{max_iterations})")
        structure: BookStructure = await ctx.get_shared_state("book:structure")
        # Send structure to generators (will loop back through fan-in to QA)
        await ctx.send_message(structure, target_id="content_generator")
        await ctx.send_message(structure, target_id="image_generator")


# ============================================================================
# Executor: Book Compiler (final output)
# ============================================================================


def generate_html_book(book: FinalBook) -> str:
    """Generate a beautiful, interactive HTML book."""

    def image_to_data_url(image_path: str) -> str:
        """Convert local image file to data URL for embedding in HTML."""
        if not image_path.startswith("file://"):
            return image_path  # Already a URL (e.g., Unsplash)

        # Remove file:// prefix
        local_path = image_path.replace("file://", "")

        try:
            import base64
            import mimetypes

            with open(local_path, "rb") as f:
                image_data = f.read()

            mime_type = mimetypes.guess_type(local_path)[0] or "image/png"
            encoded = base64.b64encode(image_data).decode("utf-8")
            return f"data:{mime_type};base64,{encoded}"
        except Exception as e:
            print(f"⚠️  Failed to embed image {local_path}: {e}")
            return image_path  # Return original path as fallback

    # Build vocabulary tooltips
    vocab_highlights = ""
    all_vocab = set()
    for page in book.pages:
        all_vocab.update(page.key_vocabulary)

    # Build pages HTML
    pages_html = ""
    for i, page in enumerate(book.pages):
        # Highlight vocabulary in kid text
        kid_text_highlighted = page.kid_text
        for vocab in page.key_vocabulary:
            kid_text_highlighted = kid_text_highlighted.replace(
                vocab,
                f'<span class="vocab" title="Key word!">{vocab}</span>'
            )

        # Convert image to data URL if it's a local file
        image_src = image_to_data_url(page.image_url)

        pages_html += f"""
        <section class="page" id="page-{page.page_number}">
            <div class="page-content">
                <div class="page-number">Page {page.page_number} of {len(book.pages)}</div>
                <h2 class="page-title">{page.title}</h2>
                <div class="concept-badge">💡 {page.concept}</div>

                <div class="image-container">
                    <img src="{image_src}" alt="{page.title}" class="page-image" loading="lazy">
                </div>

                <div class="kid-text">
                    <p>{kid_text_highlighted}</p>
                </div>

                <details class="parent-guide">
                    <summary>📖 Parent Discussion Guide</summary>
                    <div class="guide-content">
                        <p>{page.parent_guide}</p>
                        <div class="vocabulary">
                            <strong>Key Vocabulary:</strong> {', '.join(page.key_vocabulary)}
                        </div>
                    </div>
                </details>
            </div>
        </section>
        """

    # Build learning objectives list
    objectives_html = "\n".join([f"<li>{obj}</li>" for obj in book.learning_objectives])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{book.title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Comic Sans MS', 'Chalkboard SE', 'Arial Rounded MT Bold', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            line-height: 1.6;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }}

        .cover {{
            background: white;
            border-radius: 20px;
            padding: 60px 40px;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}

        .cover h1 {{
            color: #667eea;
            font-size: 3em;
            margin-bottom: 20px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }}

        .cover .subtitle {{
            font-size: 1.3em;
            color: #666;
            margin-bottom: 30px;
        }}

        .cover .metadata {{
            display: flex;
            justify-content: center;
            gap: 30px;
            font-size: 1.1em;
            color: #888;
            margin-bottom: 30px;
        }}

        .cover .metadata span {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .qa-score {{
            display: inline-block;
            background: #4CAF50;
            color: white;
            padding: 10px 20px;
            border-radius: 30px;
            font-size: 1.2em;
            font-weight: bold;
        }}

        .objectives {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-top: 20px;
        }}

        .objectives h3 {{
            color: #667eea;
            margin-bottom: 15px;
        }}

        .objectives ul {{
            list-style: none;
            padding-left: 0;
        }}

        .objectives li {{
            padding: 8px 0;
            padding-left: 25px;
            position: relative;
        }}

        .objectives li:before {{
            content: "✓";
            color: #4CAF50;
            font-weight: bold;
            position: absolute;
            left: 0;
        }}

        .page {{
            background: white;
            border-radius: 20px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            animation: fadeIn 0.5s ease-in;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .page-number {{
            text-align: right;
            color: #999;
            font-size: 0.9em;
            margin-bottom: 10px;
        }}

        .page-title {{
            color: #667eea;
            font-size: 2.2em;
            margin-bottom: 15px;
            text-align: center;
        }}

        .concept-badge {{
            background: #e3f2fd;
            color: #1976d2;
            padding: 8px 16px;
            border-radius: 20px;
            display: inline-block;
            margin-bottom: 25px;
            font-size: 0.95em;
        }}

        .image-container {{
            text-align: center;
            margin: 30px 0;
        }}

        .page-image {{
            max-width: 100%;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.2);
            max-height: 400px;
            object-fit: cover;
        }}

        .kid-text {{
            font-size: 1.8em;
            line-height: 1.8;
            color: #2c3e50;
            margin: 30px 0;
            text-align: center;
            padding: 20px;
            background: #fff9c4;
            border-radius: 15px;
            border-left: 5px solid #ffd54f;
        }}

        .vocab {{
            color: #d32f2f;
            font-weight: bold;
            cursor: help;
            border-bottom: 2px dotted #d32f2f;
        }}

        .parent-guide {{
            margin-top: 30px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
        }}

        .parent-guide summary {{
            background: #f5f5f5;
            padding: 15px 20px;
            cursor: pointer;
            font-size: 1.2em;
            color: #555;
            user-select: none;
            transition: background 0.3s;
        }}

        .parent-guide summary:hover {{
            background: #e0e0e0;
        }}

        .parent-guide[open] summary {{
            background: #667eea;
            color: white;
        }}

        .guide-content {{
            padding: 20px;
            background: #fafafa;
            line-height: 1.8;
        }}

        .vocabulary {{
            margin-top: 15px;
            padding: 15px;
            background: white;
            border-radius: 8px;
            border-left: 4px solid #4CAF50;
        }}

        .navigation {{
            position: fixed;
            bottom: 30px;
            right: 30px;
            display: flex;
            gap: 10px;
        }}

        .nav-btn {{
            background: white;
            border: none;
            padding: 15px 25px;
            border-radius: 50px;
            cursor: pointer;
            font-size: 1.1em;
            box-shadow: 0 5px 20px rgba(0,0,0,0.2);
            transition: all 0.3s;
        }}

        .nav-btn:hover {{
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        }}

        .footer {{
            text-align: center;
            padding: 40px;
            color: white;
            font-size: 0.9em;
        }}

        @media print {{
            body {{
                background: white;
            }}
            .navigation {{
                display: none;
            }}
            .page {{
                page-break-after: always;
                box-shadow: none;
            }}
        }}

        @media (max-width: 768px) {{
            .cover h1 {{
                font-size: 2em;
            }}
            .page-title {{
                font-size: 1.6em;
            }}
            .kid-text {{
                font-size: 1.4em;
            }}
            .page {{
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Cover Page -->
        <div class="cover">
            <h1>📚 {book.title}</h1>
            <div class="subtitle">An Educational Adventure for Curious Kids!</div>
            <div class="metadata">
                <span>👶 Age {book.target_age}+</span>
                <span>📄 {len(book.pages)} Pages</span>
                <span>🎯 {book.topic}</span>
            </div>
            <div class="qa-score">⭐ Quality Score: {book.qa_score}/100</div>

            <div class="objectives">
                <h3>🎓 What You'll Learn</h3>
                <ul>
                    {objectives_html}
                </ul>
            </div>
        </div>

        <!-- Book Pages -->
        {pages_html}

        <!-- Footer -->
        <div class="footer">
            <p>🤖 Generated with Microsoft Agent Framework Workflows</p>
            <p>Made with ❤️ for curious young minds</p>
        </div>
    </div>

    <!-- Navigation -->
    <div class="navigation">
        <button class="nav-btn" onclick="window.scrollTo({{top: 0, behavior: 'smooth'}})">↑ Top</button>
        <button class="nav-btn" onclick="window.print()">🖨️ Print</button>
    </div>
</body>
</html>"""

    return html


@executor(id="book_compiler")
async def book_compiler(qa_result: QAResult, ctx: WorkflowContext[Never, FinalBook]) -> None:
    """Compile final book and yield as workflow output."""

    # Retrieve from shared state
    structure: BookStructure = await ctx.get_shared_state("book:structure")
    pages_content: dict[int, PageContent] = await ctx.get_shared_state("book:pages_content")
    page_images: dict[int, str] = await ctx.get_shared_state("book:page_images")
    topic: str = await ctx.get_shared_state("book:topic")

    # Build complete pages
    complete_pages = []
    for page_plan in structure.pages:
        page_num = page_plan.page_number
        content = pages_content[page_num]
        image_url = page_images[page_num]

        complete_pages.append(
            CompletePage(
                page_number=page_num,
                title=page_plan.title,
                concept=page_plan.concept,
                kid_text=content.kid_text,
                parent_guide=content.parent_guide,
                key_vocabulary=content.key_vocabulary,
                image_url=image_url,
            )
        )

    # Create final book
    final_book = FinalBook(
        title=structure.book_title,
        topic=topic,
        target_age=structure.target_age,
        learning_objectives=structure.learning_objectives,
        pages=sorted(complete_pages, key=lambda p: p.page_number),
        qa_score=qa_result.overall_score,
    )

    # Generate HTML book
    html_content = generate_html_book(final_book)

    # Create URL-safe filename from topic
    import re
    safe_topic = re.sub(r'[^\w\s-]', '', topic)  # Remove special chars
    safe_topic = re.sub(r'[-\s]+', '_', safe_topic)  # Replace spaces/dashes with underscore
    safe_topic = safe_topic.strip('_').lower()  # Clean up and lowercase

    html_filename = f"book_{safe_topic}.html"
    html_path = os.path.join(os.path.dirname(__file__), html_filename)

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # Show completion info
    iterations = await ctx.get_shared_state("qa_iterations") or 1
    if iterations > 1:
        print(f"\n✅ Book approved after {iterations - 1} QA retry attempt(s)")
    print(f"📚 HTML book generated: {html_path}")
    print(f"📊 Final QA Score: {qa_result.overall_score}/100")

    # Auto-open in browser
    import webbrowser
    webbrowser.open(f'file://{os.path.abspath(html_path)}')
    print(f"🌐 Opening book in browser...")

    # Yield final output
    await ctx.yield_output(final_book)


# ============================================================================
# Executor: Topic Input Handler
# ============================================================================


@executor(id="topic_handler")
async def topic_handler(topic: str, ctx: WorkflowContext[Any]) -> None:
    """Handle initial topic input and store in shared state."""
    from agent_framework import AgentExecutorRequest, ChatMessage, Role

    # Initialize workflow state
    await ctx.set_shared_state("book:topic", topic)
    await ctx.set_shared_state("qa_iterations", 0)  # Initialize retry counter

    # Create prompt for structure planner
    prompt = f"""Create an educational children's book about: {topic}

Target audience: 6-year-old children
Requirements:
- 5-6 pages total
- Each page should teach one clear concept
- Use engaging story elements and characters
- Keep it fun and age-appropriate
- Include vivid image descriptions for each page"""

    # Send as AgentExecutorRequest for the agent
    await ctx.send_message(
        AgentExecutorRequest(messages=[ChatMessage(Role.USER, text=prompt)], should_respond=True)
    )


# ============================================================================
# Create Agents
# ============================================================================

chat_client = AzureOpenAIChatClient(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "gpt-4o"),
)

# Structure Planner Agent
structure_planner = chat_client.create_agent(
    name="StructurePlanner",
    instructions="""You are an expert children's educational book designer specializing in content for 6-year-olds.

Create engaging, age-appropriate book structures that:
- Break complex topics into 5-6 simple, sequential concepts
- Use storytelling and characters to make learning fun
- Progress logically from basic to more advanced ideas
- Include clear, visual image prompts for each page

Each page should:
- Have a catchy, kid-friendly title
- Focus on ONE clear learning concept
- Include a story element (character, action, or narrative hook)
- Provide vivid image description with specific keywords

Make it memorable and exciting for young learners!""",
    response_format=BookStructure,
)

# Book QA Agent
book_qa = chat_client.create_agent(
    name="BookQA",
    instructions="""You are an educational content quality reviewer specializing in children's books for 6-year-olds.

Evaluate the COMPLETE book based on:

1. Age-Appropriateness (30 points):
   - Language suitable for 6-year-olds?
   - Concepts broken down simply enough?
   - Sentence length appropriate?

2. Accuracy (25 points):
   - Facts scientifically/historically correct?
   - Explanations accurate and not misleading?

3. Coherence & Flow (20 points):
   - Pages build on each other logically?
   - Story elements connect across pages?
   - Smooth progression of concepts?

4. Engagement (15 points):
   - Will it capture a child's interest?
   - Story elements compelling?
   - Images well-matched to content?

5. Educational Value (10 points):
   - Clear learning outcomes?
   - Parent guides helpful and detailed?
   - Good discussion questions?

Provide constructive feedback. Be thorough but fair. Score 0-100.""",
    response_format=QAResult,
)

print("Agents created: StructurePlanner, ContentGenerator, ImageGenerator, BookQA")


# ============================================================================
# Build Workflow
# ============================================================================

workflow = (
    WorkflowBuilder(name="KidsBookGenerator", description="Generate educational children's books from topics")
    .set_start_executor(topic_handler)
    .add_edge(topic_handler, structure_planner)
    # Extract structured output from agent
    .add_edge(structure_planner, extract_structure)
    # Fan-out: structure → content generator AND image generator (parallel)
    .add_fan_out_edges(extract_structure, [content_generator, image_generator])
    # Fan-in: both complete → QA aggregator
    .add_fan_in_edges([content_generator, image_generator], qa_aggregator)
    # QA and decision
    .add_edge(qa_aggregator, book_qa)
    .add_edge(book_qa, extract_qa_result)
    # extract_qa_result handles routing: approved → compiler, not approved → generators (retry loop)
    .add_edge(extract_qa_result, book_compiler)
    .add_fan_out_edges(extract_qa_result, [content_generator, image_generator])
    .build()
)

print("Workflow created: Topic → Structure → [Content + Images] → QA → Compiler (with retry loop)")


# ============================================================================
# Main Entry Point
# ============================================================================


def main():
    """Launch the Kids Book Generator workflow in DevUI."""
    import logging

    from agent_framework.devui import serve

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger(__name__)

    logger.info("Starting Kids Educational Book Generator Workflow")
    logger.info("Available at: http://localhost:8094")
    logger.info("\nThis workflow demonstrates:")
    logger.info("- Structured outputs with Pydantic models")
    logger.info("- Fan-out/fan-in parallel processing")
    logger.info("- Multi-agent educational content creation")
    logger.info("- Shared state for artifact management")
    logger.info("\nTry topics like:")
    logger.info('  - "How do airplanes fly?"')
    logger.info('  - "Why is the ocean blue?"')
    logger.info('  - "How do plants grow?"')
    logger.info('  - "What are dinosaurs?"')

    serve(entities=[workflow], port=8094, auto_open=True)


if __name__ == "__main__":
    main()
