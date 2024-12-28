import os
import re
import openai

def parse_function_names_from_file(data_file):
    """
    Parse function names from a data file containing paths in the format:
    "path::ClassName::function_name".

    Args:
        data_file (str): Path to the data file.

    Returns:
        list: List of function names extracted from the data file, with 'test' and underscores removed.
    """
    function_names = []
    with open(data_file, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if line and '::' in line:
                parts = line.split('::')
                if len(parts) == 3:
                    raw_name = parts[2]
                    clean_name = raw_name.replace('test_', '').replace('_', '')
                    function_names.append(clean_name)
    return function_names

def locate_and_process_function(function_name, repo_path):
    """
    Locate the file containing the specified function and process the entire file content.

    Args:
        function_name (str): The function name to locate and process.
        repo_path (str): Base path of the repository.

    Returns:
        dict: A dictionary with the file path and its content.
    """
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)

                with open(file_path, 'r', encoding='utf-8') as infile:
                    file_content = infile.read()

                # Match function name with possible prefixes or suffixes
                function_pattern = rf"def (?:_?{function_name}_?|_?{function_name}|{function_name}_?)\\(.*?\\):"
                if re.search(function_pattern, file_content):
                    relative_path = os.path.relpath(file_path, repo_path)
                    return {
                        "file_path": relative_path,
                        "content": file_content
                    }
    return None

def call_gpt(prompt_text, api_key, api_base):
    """
    Call GPT with the given prompt.

    Args:
        prompt_text (str): The prompt to send to GPT-4.
        api_key (str): OpenAI API key.
        api_base (str): Custom OpenAI API base URL.

    Returns:
        str: The response from GPT-4.
    """
    openai.api_key = api_key
    openai.api_base = api_base
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI model trained to assist with programming tasks."},
            {"role": "user", "content": prompt_text}
        ]
    )
    return response['choices'][0]['message']['content']

def inject_bug_and_generate_prompt(function_details):
    """
    Read the extracted file and format the prompt for injecting bugs.

    Args:
        function_details (dict): A dictionary with the file path and content.

    Returns:
        str: Formatted prompt ready for GPT-4.
    """
    file_path = function_details["file_path"]
    code = function_details["content"]
    prompt = f"# FILE: {file_path}\n```{code}```\n\n"
    prompt += (
        "The above is a piece of Python code and I would like you to follow two steps to complete the task. \n"
        "1. First of all please inject a misuse of = and == bug into it with comments as the following format: \"// Misuse of = and ==\". \n"
        "2. Providing the buggy code in txt format with the following keys: \"context\": \"The code generated in step 1, THE COMPLETE CODE SHOULD NOT BE OMITTED in JSON file.\", \"input\": \"Which function has deliberate error?\", \"answer\": [\"correct_answer\"], \"options\": [\"option1\", \"option2\", \"option3\", \"option4\"]."
    )
    return prompt

if __name__ == "__main__":
    # Path to the data file containing paths
    data_file = "./ageitgey-face_recognition.txt"

    # Parse function names from the data file
    function_names = parse_function_names_from_file(data_file)

    # Path to your local repository
    repo_path = "../UniTSyn/data/repos/ageitgey-face_recognition"

    # OpenAI settings
    openai_api_key = "sk-mbJUXSh916hxnYKO371cD8809919451092B9E170D0544687"
    openai_api_base = "https://api.ai-gaochao.cn/v1"

    for function_name in function_names:
        # Locate and process the function
        function_details = locate_and_process_function(function_name, repo_path)
        if function_details:
            # Generate the GPT prompt
            prompt = inject_bug_and_generate_prompt(function_details)

            gpt_response = call_gpt(prompt, openai_api_key, openai_api_base)
            print("GPT Response:")
            print(gpt_response)
