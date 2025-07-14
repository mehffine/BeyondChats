#!/usr/bin/env python3

import os
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

import praw
import openai


# -----------------------------------------------------------------------------
# 1. Load configuration
# -----------------------------------------------------------------------------
load_dotenv()  # expects .env in same directory

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


if not all([REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, OPENAI_API_KEY]):
    raise RuntimeError(
        "Please set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, and OPENAI_API_KEY in your .env"
    )

# Configure the OpenAI API key
openai.api_key = OPENAI_API_KEY
MODEL_NAME = "gpt-3.5-turbo"  # or "gpt-4" if available

# -----------------------------------------------------------------------------
# 2. Initialize PRAW (Reddit client)
# -----------------------------------------------------------------------------
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent="persona-builder/0.1"
)

# -----------------------------------------------------------------------------
# 3. Fetch posts & comments
# -----------------------------------------------------------------------------
def fetch_user_content(username: str, limit_posts: int = 100, limit_comments: int = 100):
    posts, comments = [], []
    try:
        redditor = reddit.redditor(username)
        _ = redditor.id  # validate existence
        for post in redditor.submissions.new(limit=limit_posts):
            text = post.title + ("\n\n" + post.selftext if post.selftext else "")
            posts.append((post.created_utc, "Post", text, post.permalink))
        for c in redditor.comments.new(limit=limit_comments):
            comments.append((c.created_utc, "Comment", c.body, c.permalink))
    except Exception as e:
        print(f"[ERROR] fetching content for u/{username}: {e}")
        return None, None
    return posts, comments

# -----------------------------------------------------------------------------
# 4. Build persona via OpenAI
# -----------------------------------------------------------------------------
def build_persona(username: str, posts, comments) -> str:
    def fmt(items):
        lines = []
        for ts, kind, txt, permalink in items:
            date = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
            snippet = str(txt).replace("\n", " ").strip()[:200]
            lines.append(
                f"- ({kind} from {date}, https://www.reddit.com{permalink}) \"{snippet}…\""
            )
        return "\n".join(lines)

    persona_prompt = f"""
You are an expert user-research analyst. Your task is to analyze the provided Reddit posts and comments from the user u/{username} to build a detailed user persona.

**Reddit History for u/{username}:**

--- POSTS ---
{fmt(posts)}

--- COMMENTS ---
{fmt(comments)}

**Analysis Task**:
Based *only* on the provided text, create a user persona. The persona should be well-structured, insightful, and directly supported by evidence from the user's activity.

**Output Format**:

**User Persona: u/{username}**

* **Summary:** A brief, one-paragraph overview of the user.

* **Key Interests/Topics:** Bullet points listing the main subjects the user engages with.
    * *Citation:* (Type of content, YYYY-MM-DD, URL)

* **Hobbies & Activities:** Specific hobbies or activities mentioned or implied.
    * *Citation:* (Type of content, YYYY-MM-DD, URL)

* **Expertise Areas:** Subjects where the user demonstrates knowledge or offers help.
    * *Citation:* (Type of content, YYYY-MM-DD, URL)

* **Communication Style & Tone:** Describe the user's language, tone (e.g., formal, casual, humorous, technical), and how they interact with others.
    * *Citation:* (Type of content, YYYY-MM-DD, URL)

* **Values or Motivations:** What seems to be important to the user (e.g., community, learning, helping others, specific ideologies).
    * *Citation:* (Type of content, YYYY-MM-DD, URL)

For each characteristic, you **must cite** one or two specific posts or comments as evidence, including the type, date, and the full permalink.
""".strip()

    messages = [
        {"role": "system", "content": "You are a helpful assistant specializing in user research and persona development."},
        {"role": "user", "content": persona_prompt}
    ]

    try:
        resp = openai.ChatCompletion.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.5,
            max_tokens=1024,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ERROR] generating persona: {e}")
        return None

# -----------------------------------------------------------------------------
# 5. Main entrypoint
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Build a Reddit user persona using their posts and comments."
    )
    parser.add_argument("url", help="Full Reddit user profile URL.")
    args = parser.parse_args()

    if "reddit.com/user/" not in args.url:
        print("[ERROR] Please provide a valid Reddit user profile URL.")
        return

    username = args.url.rstrip("/").split("/")[-1]
    print(f"[+] Fetching content for u/{username}…")
    posts, comments = fetch_user_content(username)

    if posts is None or comments is None:
        return

    print(f"[+] Fetched {len(posts)} posts and {len(comments)} comments.")
    if not posts and not comments:
        print(f"[!] No content found for u/{username}; exiting.")
        return

    print("[+] Generating persona with OpenAI ChatCompletion…")
    persona = build_persona(username, posts, comments)
    if not persona:
        print("[!] Persona generation returned empty; exiting.")
        return

    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"{username}_persona.txt"
    out_file.write_text(persona, encoding="utf-8")
    print(f"[✔] Wrote {len(persona)} characters to {out_file.resolve()}")

if __name__ == "__main__":
    main()
