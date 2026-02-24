from openai import OpenAI
import json

class CodeEditor:
    def __init__(self, api_key, base_url, model):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        # TODO(haoran): add naive function calling
        self.function = [{
            "name": "code_editor",
            "description": "Edit the code given the issue and the original code",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning_trace": {
                        "type": "string",
                        "description": "Explanation of your reasoning process"
                    },
                    "code_edits": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "file": {
                                    "type": "string",
                                    "description": "Path to the file being edited"
                                },
                                "code_to_be_modified": {
                                    "type": "string",
                                    "description": "The original code snippet that needs to be modified"
                                },
                                "code_edited": {
                                    "type": "string",
                                    "description": "The new code snippet that replaces the original code snippet"
                                }
                            },
                            "required": ["file", "code_to_be_modified", "code_edited"]
                        }
                    }
                },
                "required": ["reasoning_trace", "code_edits"]
            }
        }]
    
    def edit_code(self, issue, original_code, file_path):
        input = json.dumps({
            "input": {
                "issue": issue,
                "original_code": original_code,
                "file_path": file_path,
            }
        })
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": input}],
            functions=self.function,
            function_call={"name": "code_editor"},
        )
        function_call_args = json.loads(response.choices[0].message.function_call.arguments)
        return {
            "reasoning_trace": function_call_args["reasoning_trace"],
            "code_edits": function_call_args["code_edits"],
        }
        
if __name__ == "__main__":
    code_editor = CodeEditor(api_key="sk-qiQ1VkguMJDw04Mv9f03FaEd7fEf450eB6C1E39f570bFa11", 
                             base_url="https://one-api.glm.ai/v1", 
                             model="gpt-4o-2024-11-20")
    issue = "The code is not working"
    original_code = "print('Hello, world!')"
    file_path = "test.py"
    result = code_editor.edit_code(issue, original_code, file_path)
    print(result['reasoning_trace'])
    print(result['code_edits'])
    print(result['code_edits'][0]['file'])
    print(result['code_edits'][0]['code_to_be_modified'])
    print(result['code_edits'][0]['code_edited'])