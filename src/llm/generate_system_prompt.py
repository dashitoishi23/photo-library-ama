"""
LLM System Prompt Generator

Generates the system prompt for LLM requests, including tool definitions.
"""

from src.handlers.tools import build_tools_prompt


SYSTEM_PROMPT = """
You are a helpful photo library assistant.
"""


RESPONSE_FORMAT = """
Always respond in this JSON format:
```json
{
    "user_query": "<the original user query>",
    "response_photos": "<comma-separated photo filenames, or empty string if no photos>",
    "response_additional_text": "<natural language response>",
    "timestamp": "<ISO 8601 timestamp>"
}
```

For greetings or general questions, use empty string for response_photos.
"""


def generate_system_prompt() -> str:
    """
    Generate the full system prompt to send to the LLM.
    
    Returns:
        str: The complete system prompt
    """
    tools_section = build_tools_prompt()
    
    return f"""
{SYSTEM_PROMPT}

{tools_section}

{RESPONSE_FORMAT}
""".strip()