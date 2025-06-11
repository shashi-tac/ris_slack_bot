# RIS (Real-time Information Synthesis) - Slack Bot Deployment

import feedparser
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from transformers import pipeline
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import schedule
import time
import os

# Slack configuration (set these as environment variables)
SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "#general")

client = WebClient(token=SLACK_TOKEN)

# Summarization pipeline (can be swapped with OpenAI API if needed)
summarizer = pipeline("summarization")

# RSS Feeds for Tech News
RSS_FEEDS = {
    "TechCrunch": "https://techcrunch.com/feed/",
    "Ars Technica": "http://feeds.arstechnica.com/arstechnica/index",
    "Wired": "https://www.wired.com/feed/rss",
    "MIT Technology Review": "https://www.technologyreview.com/feed/",
    "IEEE Spectrum": "https://spectrum.ieee.org/rss/fulltext",
    "VentureBeat": "https://venturebeat.com/feed/",
    "The Verge": "https://www.theverge.com/rss/index.xml" 
}

def fetch_rss_articles():
    articles = []
    for source, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:  # Limit for demo
            articles.append({
                "source": source,
                "title": entry.title,
                "link": entry.link,
                "published": entry.published,
                "summary": entry.summary
            })
    return articles

def clean_html(raw_html):
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text()

def summarize_text(text):
    try:
        if len(text.split()) < 50:
            return text
        summary = summarizer(text[:1000], max_length=100, min_length=30, do_sample=False)
        return summary[0]['summary_text']
    except Exception as e:
        return "[Summary Failed]"

def create_summary_digest(articles):
    digest = []
    for article in articles:
        clean_text = clean_html(article['summary'])
        short_summary = summarize_text(clean_text)
        digest.append({
            "title": article['title'],
            "link": article['link'],
            "source": article['source'],
            "summary": short_summary,
            "published": article['published']
        })
    return digest

def send_digest_to_slack(digest):
    if not digest:
        return
    message_blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": "*📰 RIS Hourly Tech Digest*"}}
    ]
    for entry in digest:
        block_text = f"*<{entry['link']}|{entry['title']}>*\n_Source_: {entry['source']}\n_Published_: {entry['published']}\n{entry['summary']}"
        message_blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": block_text}})
        message_blocks.append({"type": "divider"})
    try:
        client.chat_postMessage(channel=SLACK_CHANNEL, blocks=message_blocks)
    except SlackApiError as e:
        print(f"Error sending message to Slack: {e.response['error']}")

def run_ris():
    print("Running RIS to fetch and send digest...")
    articles = fetch_rss_articles()
    digest = create_summary_digest(articles)
    send_digest_to_slack(digest)

# Schedule to run every hour
schedule.every().hour.do(run_ris)

if __name__ == "__main__":
    print("RIS Slack bot is running...")
    run_ris()  # Initial run
    while True:
        schedule.run_pending()
        time.sleep(60)
