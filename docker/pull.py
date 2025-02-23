#!/usr/bin/env python3

import os
import sys
import re
import argparse
import subprocess
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

# Helper function to execute shell commands
def run_command(command):
    """Run a shell command and print output to the terminal."""
    try:
        result = subprocess.run(command, shell=True, text=True, stdout=sys.stdout, stderr=sys.stderr)
        return result.returncode, None  # No need to return output since it's printed directly
    except Exception as e:
        return 1, str(e)

# Pull and tag a single Docker image
def pull_and_tag_image(namespace, image):
    """Pull and tag a Docker image."""
    try:
        print(f"Pulling {namespace}/{image} into {image}")
        # Pull the image
        pull_command = f"docker pull {namespace}/{image}"
        pull_exit_code, pull_output = run_command(pull_command)
        if pull_exit_code != 0:
            return f"Failed to pull {namespace}/{image}: {pull_output}"

        # Rename/tag the image
        renamed_image = re.sub(r"_s_", "__", image)
        tag_command = f"docker tag {namespace}/{image} {renamed_image}"
        tag_exit_code, tag_output = run_command(tag_command)
        if tag_exit_code != 0:
            return f"Failed to tag {namespace}/{image} as {renamed_image}: {tag_output}"

        return f"Successfully pulled and tagged {namespace}/{image}"
    except Exception as e:
        return f"Error processing {namespace}/{image}: {str(e)}"

# Main function
def main():
    # Argument parsing
    parser = argparse.ArgumentParser(description="Pull and tag Docker images with progress bar.")
    parser.add_argument("level", choices=["base", "env", "instance"], help="Cache level: base, env, or instance")
    parser.add_argument("set", nargs="?", default="lite", choices=["verified", "lite", "full", "rest"], help="Set: lite, full, or rest (default: lite)")
    parser.add_argument("--namespace", default="xingyaoww", help="Docker namespace (default: xingyaoww)")
    args = parser.parse_args()

    level = args.level
    image_set = args.set
    namespace = args.namespace

    print(f"Using namespace: {namespace}")

    # Determine the image file
    script_dir = os.path.dirname(os.path.realpath(__file__))
    if image_set == "rest":
        image_file = os.path.join(script_dir, "rest.txt")
    else:
        image_file = os.path.join(script_dir, "shuf-all-swebench-verified-instance-images.txt")

    if not os.path.exists(image_file):
        print(f"Image file not found: {image_file}")
        sys.exit(1)

    # Define the pattern based on the level
    if level == "base":
        pattern = r"sweb\.base"
    elif level == "env":
        pattern = r"sweb\.base|sweb\.env"
    elif level == "instance":
        pattern = r"sweb\.base|sweb\.env|sweb\.eval"
    else:
        print(f"Invalid cache level: {level}")
        sys.exit(1)

    print(f"Pulling docker images for [{level}] level")
    print(f"Pattern: {pattern}")
    print(f"Image file: {image_file}")

    # Read and filter images
    with open(image_file, "r") as f:
        images = [line.strip() for line in f if re.search(pattern, line.strip())]

    if not images:
        print("No matching images found.")
        sys.exit(0)

    print(f"Found {len(images)} matching images.")

    # Pull and tag images with progress bar
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Use tqdm for progress bar
        for result in tqdm(executor.map(lambda img: pull_and_tag_image(namespace, img), images), total=len(images)):
            results.append(result)

    # Print results
    print("\nResults:")
    for res in results:
        print(res)

if __name__ == "__main__":
    main()
