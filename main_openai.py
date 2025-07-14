#!/usr/bin/env python3

import os
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

import praw
import openai
from textblob import TextBlob
from collections import Counter

# --------------------------------------------------------------------------
# 1. Load configuration
# --------------------------------------------------------------------------
load_dotenv()

REDDIT_CLIENT_ID     = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
OPENAI_API_KEY       = os.getenv("OPENAI_API_KEY")

if not all([REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, OPENAI_API_KEY]):
    raise RuntimeError(
        "Please set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, and OPENAI_API_KEY in your .env"
    )

openai.api_key = OPENAI_API_KEY
MODEL_NAME = "gpt-3.5-turbo"  # switch to "gpt-4" if you have access

# --------------------------------------------------------------------------
# 2. Initialize PRAW (Reddit client)
# --------------------------------------------------------------------------
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent="persona-builder/0.1"
)

# --------------------------------------------------------------------------
# 3. Fetch posts & comments
# --------------------------------------------------------------------------
def fetch_user_content(username: str, limit_posts=100, limit_comments=100):
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

# --------------------------------------------------------------------------
# 4a. Build persona via OpenAI LLM
# --------------------------------------------------------------------------
def build_persona_llm(username, posts, comments):
    def fmt(items):
        out = []
        for ts, kind, txt, permalink in items:
            date = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
            snippet = txt.replace("\n", " ").strip()[:200]
            out.append(f"- ({kind} from {date}, https://www.reddit.com{permalink}) “{snippet}…”")
        return "\n".join(out)

    prompt = f"""
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

    try:
        resp = openai.ChatCompletion.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful assistant specializing in user research and persona development."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=1024,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        err = str(e).lower()
        if "quota" in err:
            print("[ERROR] OpenAI quota exceeded.")
        else:
            print(f"[ERROR] generating persona: {e}")
        return None

# --------------------------------------------------------------------------
# 4b. Fallback: simple persona builder (TextBlob + word frequency)
# --------------------------------------------------------------------------
def build_persona_simple(posts, comments):
    combined = " ".join([text for _, _, text, _ in posts + comments])
    blob = TextBlob(combined)

    # Simple stopword list
    stopwords = {
        'the','and','is','in','to','of','a','for','on','it','with','this',
        'that','i','you','as','was','are','but','they','be','or','not'
    }
    words = [w.lower() for w in blob.words if w.isalpha() and w.lower() not in stopwords]
    freq = Counter(words)
    top = freq.most_common(5)

    sentiment = blob.sentiment
    lines = []

    # Summary
    lines.append("**Summary:**")
    if top:
        topics = ", ".join([t for t,_ in top])
        tone = "positive" if sentiment.polarity > 0 else "negative" if sentiment.polarity < 0 else "neutral"
        lines.append(f"User frequently discusses {topics}. Overall sentiment is {tone}.\n")
    else:
        lines.append("Not enough content to summarize interests.\n")

    # Key Interests/Topics
    lines.append("**Key Interests/Topics:**")
    for topic, count in top:
        lines.append(f"- {topic} (mentioned {count} times)")

    # Communication Style & Tone
    avg_len = sum(len(s.words) for s in blob.sentences) / len(blob.sentences) if blob.sentences else 0
    lines.append("\n**Communication Style & Tone:**")
    lines.append(f"- Sentiment polarity: {sentiment.polarity:.2f}, subjectivity: {sentiment.subjectivity:.2f}")
    lines.append(f"- Average sentence length: {avg_len:.1f} words\n")

    return "\n".join(lines)

# --------------------------------------------------------------------------
# 5. Main entrypoint
# --------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Build a Reddit user persona.")
    parser.add_argument("url", help="Full Reddit user profile URL (e.g. https://www.reddit.com/user/kojied/)")
    args = parser.parse_args()

    if "reddit.com/user/" not in args.url:
        print("[ERROR] Please provide a valid Reddit user profile URL.")
        return

    username = args.url.rstrip("/").split("/")[-1]
    print(f"[+] Fetching content for u/{username}…")
    posts, comments = fetch_user_content(username)
    if not posts and not comments:
        print("[ERROR] No posts or comments found; exiting.")
        return

    # Attempt LLM first
    print("[+] Trying OpenAI persona generation…")
    persona = build_persona_llm(username, posts, comments)

    # Fallback if needed
    if not persona:
        print("[+] Falling back to simple persona builder…")
        persona = build_persona_simple(posts, comments)

    # Write out
    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"{username}_persona.txt"
    out_file.write_text(persona, encoding="utf-8")
    print(f"[✔] Persona written to {out_file.resolve()}")

if __name__ == "__main__":
    main()
