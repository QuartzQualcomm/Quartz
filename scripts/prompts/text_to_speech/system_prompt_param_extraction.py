import json
from .tool_info import TOOL_INFO

def get_system_prompt_for_param_extraction(tool_name: str):
    """
    Generates a system prompt for the LLM to extract parameters for a given tool.
    """
    if tool_name not in TOOL_INFO:
        raise ValueError(f"Tool '{tool_name}' not found in TOOL_INFO.")

    tool = TOOL_INFO[tool_name]
    params = tool["params"]
    
    param_definitions = "\n".join([f'- `{name}` ({details["type"]}): {details["description"]}' for name, details in params.items()])

    if tool_name == "text_to_speech":
        example_command = "Convert 'hello, this is me' to speech"
        example_params = {
            "text": "hello, this is me"
        }
        additional_examples = """- "Say 'how are you doing today?'" -> {{"text": "how are you doing today?"}}
- "Read out loud 'this is a test'" -> {{"text": "this is a test"}}
- "Can you say 'I am an AI assistant'?" -> {{"text": "I am an AI assistant"}}
- "I want to hear 'this is a sample text'" -> {{"text": "this is a sample text"}}"""
    else:
        # Generic fallback for other potential tools, though not used now.
        example_command = "No example available"
        example_params = {}
        additional_examples = "No additional examples available."

    return f"""You are a highly intelligent parameter extractor for a tool-using system. Your goal is to extract parameters for the '{tool_name}' tool based on the user's command. You MUST respond with a single, valid JSON object. Do not add any text before or after the JSON object.

TOOL DESCRIPTION: {tool['description']}

PARAMETERS TO EXTRACT:
{param_definitions}

If a parameter's value cannot be found in the user command, you MUST use the string "NULL" for its value.

For example, for the user command "{example_command}", your response should be:
```json
{json.dumps(example_params, indent=2)}
```

Additional examples:
{additional_examples}
"""
