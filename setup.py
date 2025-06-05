import setuptools
import os

def read_requirements(filename):
    """Read requirements from requirements.txt file"""
    requirements = []
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#') and not line.startswith('-'):
                    requirements.append(line)
    return requirements

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

# Read base requirements from requirements.txt
base_requirements = [
    'beautifulsoup4',
    'chardet',
    'datasets',
    'docker',
    'ghapi',
    'GitPython',
    'modal',
    'pre-commit',
    'python-dotenv',
    'requests',
    'rich',
    'tenacity',
    'tqdm',
    'unidiff',
]

# Add requirements from requirements.txt if it exists
requirements_txt_deps = read_requirements('requirements.txt')
all_requirements = base_requirements + requirements_txt_deps

setuptools.setup(
    name='Swingbench',
    author='Anonymous',
    author_email='anonymous@anonymous.com',
    description='The official Swingbench package - a benchmark for evaluating LMs on software engineering',
    keywords='nlp, benchmark, code',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3 :: Only',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
    install_requires=all_requirements,
    extras_require={
        'inference': [
            'anthropic',
            'flash_attn',
            'jedi',
            'openai',
            'peft',
            'protobuf',
            'sentencepiece',
            'tiktoken',
            'torch',
            'transformers',
            'triton',
        ],
        'test': [
            'pytest',
            'pytest-cov',
        ]
    },
    include_package_data=True,
)