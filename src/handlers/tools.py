from typing import Optional, Any, Callable
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tools")


TOOL_SCHEMA = {
    "name": "search_photos",
    "description": "Search for photos in the user's photo collection using natural language. Use this when the user wants to find specific photos by describing what they're looking for (e.g., 'beach photos', 'sunset photos from Kerala', 'photos taken with Samsung camera').",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language search query (e.g., 'beach photos at Kerala')"
            },
            "n_results": {
                "type": "integer",
                "description": "Number of results to return",
                "default": 10
            }
        },
        "required": ["query"]
    }
}


AVAILABLE_TOOLS = {}


def register_tool(func: Callable) -> Callable:
    """Decorator to register a function as a tool."""
    AVAILABLE_TOOLS[func.__name__] = func
    return func


def get_tool_schemas() -> list[dict]:
    """Get all registered tool schemas."""
    return [TOOL_SCHEMA]


def execute_tool(tool_name: str, arguments: dict) -> dict:
    """Execute a tool by name with given arguments."""
    if tool_name not in AVAILABLE_TOOLS:
        return {"success": False, "error": f"Tool '{tool_name}' not found"}
    
    try:
        tool_func = AVAILABLE_TOOLS[tool_name]
        return tool_func(**arguments)
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return {"success": False, "error": str(e)}


def parse_tool_call_from_response(response: str) -> Optional[tuple[str, dict]]:
    """
    Parse a tool call from LLM response.
    
    The LLM should respond in this format for tool calls:
    ```json
    {"tool": "search_photos", "args": {"query": "beach photos", "n_results": 5}}
    ```
    """
    try:
        data = json.loads(response.strip())
        if "tool" in data and "args" in data:
            return (data["tool"], data["args"])
    except json.JSONDecodeError:
        pass
    return None


def build_tools_prompt() -> str:
    """Build the tools section for system prompt."""
    schemas = get_tool_schemas()
    return f"""
You may call the following tools as needed:

{json.dumps(schemas, indent=2)}

To call a tool, respond in this JSON format:
```json
{{"tool": "tool_name", "args": {{"param1": "value1"}}}}
```
"""