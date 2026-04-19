from src.llm.generate_system_prompt import generate_system_prompt
from src.llm.llm_call import llm_call
from src.handlers.tools import parse_tool_call_from_response, execute_tool


def run_agent(user_query: str, max_iterations: int = 10) -> dict:
    messages = []
    
    system_prompt = generate_system_prompt()
    messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_query})

    result = {}
    tool_call = ""

    llm_response = llm_call(messages, temperature=0.0, max_tokens=500)

    llm_message = llm_response.get("choices", [{}])[0].get("message", {})
    messages.append(llm_message)

    content = llm_message.get("content", "")

    tool_call = parse_tool_call_from_response(content)
    if tool_call != None:
        result = execute_tool(tool_call[0], tool_call[1])
        print(f"{result}")
    else:
        result = content

    
    return {
        "result": result,
        "tool_call": tool_call
    }
