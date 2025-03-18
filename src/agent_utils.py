import json

class MessageProcessor:
    def __init__(self, client, available_tools, default_model, default_temperature, default_stop, logger):
        self.client = client
        self.available_tools = available_tools
        self.default_model = default_model
        self.default_temperature = default_temperature
        self.default_stop = default_stop
        self.logger = logger

    def process_message(self, messages, model=None, temperature=None, stop=None):
        response = self.client.chat.completions.create(
            model=model or self.default_model,
            messages=messages,
            tools=self.available_tools,
            temperature=temperature or self.default_temperature,
            stop=stop or self.default_stop,
        )
        response_message = response.choices[0].message
        messages.append(response_message)
        
        if response_message.tool_calls:
            for tool_call in response_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                self.logger.info(f"Tool call: {tool_name} with args: {tool_args}")
                
                tool = self.available_tools[tool_name]
                tool_response = tool(**tool_args)
                
                self.logger.info(f"Tool response: {tool_response}")

                messages.append({
                    "role": "tool",
                    "name": tool_name,
                    "content": tool_response,
                    "tool_call_id": tool_call.id
                })


class CodeExecutionAgent:
    pass