import os
import re
import openai

# Map of bug types and their descriptions
bug_map = {
    "misused ==/=": "First of all please inject a misuse of = and == bug into it with comments as the following format: \"// Misuse of = and ==\".",
    "missing colons": "First of all please inject a missing colon bug into it with comments as the following format: \"// Missing colon\".",
    "unclosed parentheses": "First of all please inject an unclosed parentheses bug into it with comments as the following format: \"// Unclosed parentheses\".",
    "illegal separation": "First of all please inject an illegal separation bug into it with comments as the following format: \"// Illegal separation\".",
    "illegal indentation": "First of all please inject an illegal indentation bug into it with comments as the following format: \"// Illegal indentation\".",
    "unclosed string": "First of all please inject an unclosed string bug into it with comments as the following format: \"// Unclosed string\".",
    "illegal comment": "First of all please inject an illegal comment bug into it with comments as the following format: \"// Illegal comment\".",
    "faulty indexing": "First of all please inject a faulty indexing bug into it with comments as the following format: \"// Faulty indexing\".",
    "undefined objects": "First of all please inject an undefined object bug into it with comments as the following format: \"// Undefined object\".",
    "undefined methods": "First of all please inject an undefined method bug into it with comments as the following format: \"// Undefined method\".",
    "illegal keywords": "First of all please inject an illegal keyword bug into it with comments as the following format: \"// Illegal keyword\".",
    "condition error": "First of all please inject a condition error bug into it with comments as the following format: \"// Condition error\".",
    "operation error": "First of all please inject an operation error bug into it with comments as the following format: \"// Operation error\".",
    "variable error": "First of all please inject a variable error bug into it with comments as the following format: \"// Variable error\"."
}


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
                    clean_name = raw_name.replace('test_', '')
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
                function_pattern = rf"def _?{function_name}"
                if re.search(function_pattern, file_content):
                    relative_path = os.path.relpath(file_path, repo_path)
                    return {
                        "file_path": relative_path,
                        "content": file_content
                    }
                
    print(f"Function '{function_name}' not found in the repository.")
    return None

def call_gpt(prompt_text, api_key, api_base=None):
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
    if api_base:
        openai.api_base = api_base
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI model trained to assist with programming tasks."},
            {"role": "user", "content": prompt_text}
        ]
    )
    return response['choices'][0]['message']['content']

def inject_bug_and_generate_prompt(function_details, bug_type):
    """
    Read the extracted file and format the prompt for injecting bugs.

    Args:
        function_details (dict): A dictionary with the file path and content.

    Returns:
        str: Formatted prompt ready for GPT-4.
    """
    file_path = function_details["file_path"]
    code = function_details["content"]

    bug_injection_instruction = bug_map.get(bug_type)


    prompt = f"# FILE: {file_path}\n```{code}```\n\n"
    prompt += (
        f"The above is a piece of Python code and I would like you to follow two steps to complete the task.\n"
        f"1. {bug_injection_instruction}\n"
        "2. Generate a text file in the following format, and replace the contents of the \"context\" here with the complete buggy code you generated in step 1, without comments and the complete code should not be omitted, replace the contents of the \"answers\" with the name of the function you injected the bug into, and replace the contents of the \"options\" with the names of all the functions in the entire code: "
        "\"context\": \"The code generated in step 1\", "
        "\"input\": \"Which function has deliberate error?\", "
        "\"answer\": [\"correct_answer\"], "
        "\"options\": [\"option1\", \"option2\", \"option3\", \"option4\"].\n"
        "The answer you generate does not need to contain the results of the first step, you just need to return the text file."
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
    openai_api_key = "sk-nZGxCfIBxtuzEMdKO7Y52xd91ulbCl74fJSfv7XPhDLF8iZF"
    openai_api_base = "https://api.feidaapi.com/v1"

    # Output file to collect GPT responses
    output_file = "injected.txt"

    selected_bug_type = "illegal indentation"

    with open(output_file, 'w', encoding='utf-8') as outfile:
        for function_name in function_names:
            # Locate and process the function
            function_details = locate_and_process_function(function_name, repo_path)

            if function_details:
                # Generate the GPT prompt
                prompt = inject_bug_and_generate_prompt(function_details, selected_bug_type)

                gpt_response = call_gpt(prompt, openai_api_key, openai_api_base)

                # Write the GPT response to the output file
                outfile.write(f"Function Name: {function_name}\n")
                outfile.write(f"Response:\n{gpt_response}\n")
                outfile.write("=" * 80 + "\n")  # Add a separator for readability

                print(f"Response for '{function_name}' saved.")
