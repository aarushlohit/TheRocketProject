"""
Semantic Text Generation Module (PATCH 6).

Generates intelligent text content for TYPE_TEXT commands when creative
intent is detected (e.g., "write a love poem" → actual poem).

ARCHITECTURE:
- Execution remains DETERMINISTIC
- LLM is used ONLY for content generation
- Generation is isolated from execution pipeline

RULES:
1. DO NOT generate content for dangerous commands
2. DO NOT override confirmation system
3. Execution = deterministic, Generation = intelligent
"""

from __future__ import annotations

import os
import re
from typing import Optional, Tuple

from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# CREATIVE KEYWORDS
# =============================================================================

CREATIVE_KEYWORDS = {
    # Writing types
    "poem", "poetry", "sonnet", "haiku", "limerick",
    "story", "short story", "tale", "narrative",
    "essay", "article", "blog post", "blog",
    "paragraph", "text", "content",
    "email", "letter", "message", "note",
    "speech", "presentation", "script",
    "joke", "riddle", "pun",
    "lyrics", "song",
    "quote", "saying", "proverb",
    "description", "summary", "overview",
    "review", "critique", "feedback",
    "bio", "biography", "about me",
    "introduction", "intro",
    "conclusion", "ending",
    "recipe", "instructions", "guide", "tutorial",
    "list", "bullet points",
}

# Prefixes that indicate generation intent
GENERATION_PREFIXES = {
    "write", "compose", "create", "generate", "make",
    "draft", "type", "pen", "author", "craft",
}

# Topics that require semantic expansion
SEMANTIC_TOPICS = {
    "love", "romantic", "funny", "sad", "happy", "inspiring",
    "motivational", "birthday", "anniversary", "thank you",
    "apology", "congratulations", "farewell", "welcome",
    "christmas", "holiday", "valentine", "mother", "father",
    "friend", "nature", "life", "death", "hope", "dream",
}


# =============================================================================
# DETECTION
# =============================================================================

def needs_generation(text: str) -> bool:
    """
    Detect if text requires semantic generation instead of literal typing.
    
    Examples:
        "love poem" → True (should generate actual poem)
        "hello world" → False (type literally)
        "write a birthday message" → True
        "my email is test@example.com" → False
    """
    text_lower = text.lower().strip()
    
    # Empty or very short text - type literally
    if len(text_lower) < 3:
        return False
    
    # Check for creative keywords
    for keyword in CREATIVE_KEYWORDS:
        if keyword in text_lower:
            return True
    
    # Check for generation prefixes combined with content
    words = text_lower.split()
    if words and words[0] in GENERATION_PREFIXES and len(words) > 1:
        # "write poem" pattern
        return True
    
    # Check for "a/an" + creative keyword pattern
    # e.g., "a poem", "an essay"
    if re.search(r'\b(a|an)\s+(' + '|'.join(CREATIVE_KEYWORDS) + r')\b', text_lower):
        return True
    
    # Check for semantic topic + creative keyword
    for topic in SEMANTIC_TOPICS:
        for keyword in CREATIVE_KEYWORDS:
            if topic in text_lower and keyword in text_lower:
                return True
    
    return False


def extract_generation_prompt(text: str) -> Tuple[str, str]:
    """
    Extract the type and content for generation.
    
    Returns:
        Tuple of (content_type, topic/subject)
        
    Examples:
        "love poem" → ("poem", "love")
        "write a funny story" → ("story", "funny")
        "birthday message for mom" → ("message", "birthday for mom")
    """
    text_lower = text.lower().strip()
    
    # Remove generation prefixes
    for prefix in GENERATION_PREFIXES:
        if text_lower.startswith(prefix):
            text_lower = text_lower[len(prefix):].strip()
            break
    
    # Remove articles
    text_lower = re.sub(r'^(a|an|the)\s+', '', text_lower)
    
    # Find the content type
    content_type = "text"
    for keyword in CREATIVE_KEYWORDS:
        if keyword in text_lower:
            content_type = keyword
            # Extract the subject/topic (everything else)
            topic = text_lower.replace(keyword, "").strip()
            # Clean up common words
            topic = re.sub(r'\b(about|for|on|regarding|with)\b', '', topic).strip()
            return content_type, topic if topic else content_type
    
    return content_type, text_lower


# =============================================================================
# GENERATION
# =============================================================================

# Simple templates for offline generation
TEMPLATES = {
    "poem": """
{topic_title}

Under skies of endless blue,
Words take flight to speak of you.
In every breath and quiet sigh,
A {topic} thought goes drifting by.

Through morning light and evening's gleam,
You linger softly in my dream.
With gentle grace and tender art,
You've found a place within my heart.
""",
    
    "love poem": """
A Love Poem

My heart beats soft, a whispered song,
For you, my love, I've waited long.
Like stars that dance across the night,
Your presence fills my world with light.

In every word and gentle glance,
I find my soul's eternal dance.
Forever yours, through time and space,
My love for you no years erase.
""",
    
    "story": """
Once upon a time, in a world not unlike our own, there lived a dreamer who believed in the impossible. Each day brought new adventures, each challenge a stepping stone to greater things.

Through trials and tribulations, the dreamer persevered, learning that {topic} was not just a destination but a journey—one filled with wonder, discovery, and the magic of believing.

And so the story goes on, for every ending is but a new beginning.
""",
    
    "email": """
Subject: {topic_title}

Dear [Recipient],

I hope this message finds you well. I wanted to reach out regarding {topic}.

[Your message content here]

Please let me know if you have any questions or need further information.

Best regards,
[Your Name]
""",
    
    "message": """
Hi there!

I wanted to share something about {topic} with you.

[Your message here]

Hope to hear from you soon!
""",
    
    "birthday": """
Happy Birthday!

🎂 Wishing you the most wonderful birthday filled with joy, laughter, and all the happiness your heart can hold!

May this new year of your life bring you amazing adventures, beautiful memories, and dreams come true. You deserve all the best!

Have an absolutely fantastic day! 🎉
""",
    
    "thank you": """
Thank You

I wanted to take a moment to express my heartfelt gratitude. Your kindness and support have meant more to me than words can say.

Thank you for being such a wonderful person and for making a positive difference. I truly appreciate everything you've done.

With sincere thanks and warm regards.
""",
    
    "joke": """
Why don't scientists trust atoms?

Because they make up everything! 😄
""",
}


def generate_text(prompt: str) -> str:
    """
    Generate semantic text content based on the prompt.
    
    This function attempts to:
    1. Use LLM if available (OpenAI/local)
    2. Fall back to templates
    
    Args:
        prompt: The generation prompt (e.g., "love poem", "funny story")
    
    Returns:
        Generated text content
    """
    content_type, topic = extract_generation_prompt(prompt)
    
    print(f"\n========== [SEMANTIC GENERATION] ==========")
    print(f"[PROMPT] {prompt}")
    print(f"[TYPE] {content_type}")
    print(f"[TOPIC] {topic}")
    
    # Try LLM generation first
    generated = _try_llm_generation(prompt, content_type, topic)
    if generated:
        print(f"[SOURCE] LLM")
        return generated
    
    # Fall back to templates
    generated = _generate_from_template(content_type, topic)
    print(f"[SOURCE] Template")
    return generated


def _try_llm_generation(prompt: str, content_type: str, topic: str) -> Optional[str]:
    """
    Try to generate using available LLM.
    
    Supports:
    - OpenAI API (if OPENAI_API_KEY is set)
    - Local models via litellm (if configured)
    """
    # Check for OpenAI
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        try:
            return _generate_with_openai(prompt, content_type, topic, api_key)
        except Exception as e:
            logger.warning(f"OpenAI generation failed: {e}")
    
    # Check for local model
    try:
        return _generate_with_local_model(prompt, content_type, topic)
    except Exception as e:
        logger.debug(f"Local model not available: {e}")
    
    return None


def _generate_with_openai(prompt: str, content_type: str, topic: str, api_key: str) -> Optional[str]:
    """Generate using OpenAI API."""
    try:
        import openai
        
        client = openai.OpenAI(api_key=api_key)
        
        system_prompt = f"""You are a creative writing assistant. Generate a {content_type} about {topic}.
Keep it concise, meaningful, and appropriate. Do not include any harmful or inappropriate content.
Just output the content directly without any preamble or explanation."""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Write a {content_type} about {topic if topic else 'something beautiful'}"}
            ],
            max_tokens=500,
            temperature=0.7,
        )
        
        return response.choices[0].message.content.strip()
    except ImportError:
        logger.debug("OpenAI library not installed")
        return None
    except Exception as e:
        logger.warning(f"OpenAI API error: {e}")
        return None


def _generate_with_local_model(prompt: str, content_type: str, topic: str) -> Optional[str]:
    """Generate using local model via litellm or similar."""
    try:
        import litellm
        
        response = litellm.completion(
            model="ollama/llama2",  # Or another local model
            messages=[
                {"role": "user", "content": f"Write a short {content_type} about {topic}"}
            ],
            max_tokens=300,
        )
        
        return response.choices[0].message.content.strip()
    except ImportError:
        return None
    except Exception as e:
        logger.debug(f"Local model error: {e}")
        return None


def _generate_from_template(content_type: str, topic: str) -> str:
    """Generate using built-in templates."""
    topic_title = topic.title() if topic else content_type.title()
    
    # Check for specific content type + topic combinations
    key = f"{topic.lower()} {content_type}" if topic else content_type
    for template_key, template in TEMPLATES.items():
        if template_key in key or key in template_key:
            return template.format(
                topic=topic or content_type,
                topic_title=topic_title
            ).strip()
    
    # Check for content type alone
    if content_type in TEMPLATES:
        return TEMPLATES[content_type].format(
            topic=topic or "this",
            topic_title=topic_title
        ).strip()
    
    # Default template
    return f"""
{topic_title}

Here is some thoughtful content about {topic or 'this topic'}.

This text was generated to express ideas about {content_type}.
Feel free to customize it to your needs.
""".strip()


# =============================================================================
# INTEGRATION FUNCTION
# =============================================================================

def process_type_text_semantic(text: str) -> str:
    """
    Process TYPE_TEXT with semantic generation if needed.
    
    This is the main integration point for the executor.
    
    Args:
        text: The text from TYPE_TEXT slots
    
    Returns:
        Either the original text or generated content
    """
    if needs_generation(text):
        return generate_text(text)
    return text


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "needs_generation",
    "generate_text",
    "process_type_text_semantic",
    "extract_generation_prompt",
    "CREATIVE_KEYWORDS",
]
