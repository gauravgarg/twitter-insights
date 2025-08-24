
import os, time, re
from datetime import datetime, timedelta
import sqlite3
import snscrape.modules.twitter as sntwitter
from ratelimit import limits, sleep_and_retry
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

 # Removed interval logic; UI will control fetch timing

handles_env = os.getenv("TWITTER_HANDLES", "")
HANDLES = [h.strip().lstrip("@") for h in handles_env.split(",") if h.strip()]
logging.info(f"Handles to collect: {HANDLES}")

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

@sleep_and_retry
@limits(calls=15, period=900)  # 15 calls per 15 minutes (Twitter's public rate limit)
def fetch_and_store(handle, patterns):
    logging.info(f"--- Start fetching tweets for user: {handle} ---")
    try:
        # Get latest tweet date for this handle from DB
        cur.execute("SELECT MAX(datetime(created_at)) FROM tweets WHERE handle = ?", (f"@{handle}",))
        row = cur.fetchone()
        latest_db_date = row[0]
        if latest_db_date:
            latest_db_date = datetime.fromisoformat(latest_db_date)
        else:
            latest_db_date = None

        three_days_ago = datetime.now() - timedelta(days=3)
        tweets = []
        tweet_count = 0
        for tweet in sntwitter.TwitterUserScraper(handle).get_items():
            # Only process actual Tweet objects
            if not isinstance(tweet, sntwitter.Tweet):
                continue
            # Only consider tweets from last 3 days
            if tweet.date < three_days_ago:
                break
            # Stop if tweet is already in DB (by date)
            if latest_db_date and tweet.date <= latest_db_date:
                break
            tweets.append(tweet)
            tweet_count += 1
            if len(tweets) >= 10:
                break
        logging.info(f"Fetched {tweet_count} tweets for user: {handle}")
        if not tweets:
            logging.info(f"No new tweets found for user: {handle}")
            logging.info(f"--- End fetching tweets for user: {handle} ---")
            return
        for t in tweets:
            category, stock = categorize(t.content, patterns)
            try:
                cur.execute(
                    "INSERT INTO tweets (id, handle, content, category, stock_name, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (str(t.id), f"@{handle}", t.content, category, stock, str(t.date))
                )
                logging.info(f"Inserted tweet {t.id} for {handle} | {category} | {stock}")
            except sqlite3.IntegrityError:
                logging.debug(f"Duplicate tweet {t.id} for {handle}")
            except Exception as e:
                logging.error(f"DB error for tweet {t.id} for {handle}: {e}")
        conn.commit()
        logging.info(f"Committed tweets for {handle}")
        logging.info(f"--- End fetching tweets for user: {handle} ---")
    except Exception as e:
        logging.error(f"Error for {handle}: {e}", exc_info=True)

def main_loop():
    if not HANDLES:
        logging.warning("No TWITTER_HANDLES provided. Set env var to collect from usernames.")
        return
    keywords = load_keywords()
    patterns = build_match_patterns(keywords)
    logging.info(f"{datetime.now()} IST | {len(HANDLES)} handles | {len(keywords)} keywords")

    for h in HANDLES:
        fetch_and_store(h, patterns)
        time.sleep(3)  # polite delay between users

    logging.info(f"Cycle complete.")

if __name__ == "__main__":
    main_loop()