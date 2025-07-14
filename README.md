# Project: Reddit Persona Builder

An automated tool that fetches a Reddit user's recent posts and comments, generates a detailed user persona using the OpenAI ChatCompletion API, and writes the persona (with citations) to `outputs/<username>_persona.txt`. If the OpenAI quota is exceeded, it falls back to a simple persona builder using TextBlob.

## Repository Structure

```
persona-builder/
├── main_openai.py        # Main script
├── outputs/             # Generated persona text files
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
└── .gitignore           # Files and folders to ignore
```

## README.md

````md
# Reddit Persona Builder

Fetch a Reddit user's recent posts and comments, build a detailed user persona via OpenAI's Chat API (with citations), and save the persona to a text file. Falls back to a simple TextBlob-based analysis if the API call fails.

## Features
- Scrapes up to 100 posts and 100 comments using PRAW
- Generates a structured persona with evidence citations via OpenAI ChatCompletion
- Graceful fallback to offline analysis with TextBlob (no extra downloads required)

## Prerequisites
- Python 3.8+
- A Reddit API application (client ID & secret)
- An OpenAI API key with sufficient quota

## Setup
1. Clone this repository:
   ```bash
   git clone https://github.com/<your-username>/persona-builder.git
   cd persona-builder
````

2. Create a virtual environment and activate it:

   ```bash
   python -m venv venv
   source venv/bin/activate     # macOS/Linux
   venv\Scripts\activate      # Windows
   ```
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```
4. Prepare environment variables:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and fill in your values:

   ```dotenv
   REDDIT_CLIENT_ID=...
   REDDIT_CLIENT_SECRET=...
   OPENAI_API_KEY=sk-...
   ```

## Usage

```bash
python main_openai.py https://www.reddit.com/user/<username>/
```

* Outputs the persona to `outputs/<username>_persona.txt`

## Files

* `main_openai.py`: Core script
* `requirements.txt`: Dependencies
* `.env.example`: Template for environment variables
* `.gitignore`: Files to ignore in Git

## License

MIT © Your Name

````

## .env.example
```dotenv
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
OPENAI_API_KEY=
````

## .gitignore

```gitignore
# Python
__pycache__/
*.py[cod]

# Environment variables
.env

# Outputs
toutputs/

# IDE files
.vscode/
```
