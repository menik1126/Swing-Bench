import os
import openai

def concatenate_py_files(repo_path, output_file):
    """
    Traverse all .py files in a repo and concatenate their contents into a single file.
    Each file's content is prefixed with its relative path.

    Args:
        repo_path (str): Path to the local repository.
        output_file (str): Path to the output file.
    """
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for root, _, files in os.walk(repo_path):
            for file in files:
                if file.endswith('.py') and "test" not in file.lower():
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, repo_path)
                    outfile.write(f"# FILE: {relative_path}\n")
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        outfile.write(infile.read())
                        outfile.write("\n\n")  # Separate files with a blank line

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

def inject_bug_and_generate_prompt(file_path):
    """
    Read the concatenated file and format the prompt for injecting bugs.

    Args:
        file_path (str): Path to the concatenated file.

    Returns:
        str: Formatted prompt ready for GPT-4.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()
    
    # code = "test"

    prompt = f"""
    ```{code}```
    The above is a piece of Python code and I would like you to follow two steps to complete the task. 
    1. First of all please inject a misuse of = and == bug into it with comments as the following format: "// Misuse of = and ==". 
    2. Providing the buggy code in txt format with the following keys: "context": "The code generated in step 1, THE COMPLETE CODE SHOULD NOT BE OMITTED in JSON file.", "input": "Which function has deliberate error?", "answer": ["correct_answer"], "options": ["option1", "option2", "option3", "option4"].
    You just need to return the text file, THE COMPLETE CODE SHOULD NOT BE OMITTED in JSON file.
    """
    # print(prompt)
    return prompt


if __name__ == "__main__":
    # Path to your local repository
    repo_path = "../UniTSyn/data/repos/ageitgey-face_recognition"

    # Path to the output file
    output_file = "./test_concat_file.txt"

    # OpenAI settings
    openai_api_key = "sk-EaJIsRtJR3wNozOzFA97U2HHxeBDhi3QngjBHFpGT8aPu5Ae"
    # openai_api_base = "https://api.ai-gaochao.cn/v1"
    openai.api_base = "https://api.openai.com/v1"

    concatenate_py_files(repo_path, output_file)
    print(f"All .py files have been concatenated into {output_file}")

    prompt = inject_bug_and_generate_prompt(output_file)

    gpt_response = call_gpt(prompt, openai_api_key, openai_api_base)
    print("GPT Response:")
    print(gpt_response)
