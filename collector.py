
import os, time, re
from datetime import datetime
import tweepy, sqlite3
from dotenv import load_dotenv
from db_init import get_conn, init_db
from utils import build_match_patterns, find_first_match, normalize_keyword
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logging.info("Starting collector.py...")
load_dotenv()

BEARER_TOKEN = os.getenv("BEARER_TOKEN")
if not BEARER_TOKEN:
    logging.error("Missing BEARER_TOKEN in env.")
    raise SystemExit("Missing BEARER_TOKEN in env.")

INTERVAL = int(os.getenv("COLLECTOR_INTERVAL", "3600"))
logging.info(f"Collector interval set to {INTERVAL} seconds.")

handles_env = os.getenv("TWITTER_HANDLES", "")
HANDLES = [h.strip().lstrip("@") for h in handles_env.split(",") if h.strip()]
logging.info(f"Handles to collect: {HANDLES}")

client = tweepy.Client(bearer_token=BEARER_TOKEN, wait_on_rate_limit=True)

conn = get_conn()
init_db(conn)
cur = conn.cursor()
logging.info("Database initialized.")

def load_keywords():
    cur.execute("SELECT keyword FROM stock_keywords")
    keywords = [r[0] for r in cur.fetchall()]
    logging.info(f"Loaded {len(keywords)} keywords from DB.")
    return keywords

def categorize(text, patterns):
    match = find_first_match(text, patterns)
    if match:
        logging.debug(f"Categorized as Stock-Specific: {match}")
        return "Stock-Specific", normalize_keyword(match)
    logging.debug("Categorized as Financial Awareness.")
    return "Financial Awareness", None

def fetch_and_store(handle, patterns):
    import time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logging.info(f"Fetching user: {handle}")
            user = client.get_user(username=handle)
            if not user or not user.data:
                logging.warning(f"User not found: {handle}")
                return

            tweets = client.get_users_tweets(
                user.data.id,
                max_results=10,
                tweet_fields=["created_at","text","lang"]
            )

            if not tweets or not tweets.data:
                logging.info(f"No tweets found for user: {handle}")
                return

            for t in tweets.data:
                category, stock = categorize(t.text, patterns)
                try:
                    cur.execute(
                        "INSERT INTO tweets (id, handle, content, category, stock_name, created_at) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (str(t.id), f"@{handle}", t.text, category, stock, str(t.created_at))
                    )
                    logging.info(f"Inserted tweet {t.id} for {handle} | {category} | {stock}")
                except sqlite3.IntegrityError:
                    logging.debug(f"Duplicate tweet {t.id} for {handle}")
            conn.commit()
            logging.info(f"Committed tweets for {handle}")
            break
        except tweepy.TooManyRequests as e:
            # Tweepy >=4.10.0: TooManyRequests is raised for rate limits
            wait_time = getattr(e, 'retry_after', 900)  # fallback to 15 min if not provided
            logging.warning(f"Rate limit exceeded for {handle}. Sleeping for {wait_time} seconds.")
            time.sleep(wait_time)
        except tweepy.TweepyException as e:
            logging.error(f"Tweepy error for {handle}: {e}")
            break
        except Exception as e:
            logging.error(f"Error for {handle}: {e}")
            break

def main_loop():
    if not HANDLES:
        logging.warning("No TWITTER_HANDLES provided. Set env var to collect from usernames.")
        return
    keywords = load_keywords()
    patterns = build_match_patterns(keywords)
    logging.info(f"{datetime.now()} IST | {len(HANDLES)} handles | {len(keywords)} keywords")

    for h in HANDLES:
        fetch_and_store(h, patterns)

    logging.info(f"Cycle complete.")

def main_loop_forever():
    while True:
        main_loop()
        logging.info(f"Sleeping {INTERVAL}s...")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main_loop()