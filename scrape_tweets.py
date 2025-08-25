

import asyncio
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

async def scrape_last_2_days_tweets(url):
    tweets = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_timeout(5000)
        for _ in range(10):
            await page.evaluate("window.scrollBy(0, window.innerHeight);")
            await page.wait_for_timeout(2000)
        tweet_articles = await page.locator('article').all()
        from dateutil import parser
        import re
        today = datetime.utcnow().date()
        two_days_ago = today - timedelta(days=2)
        month_map = {m: i for i, m in enumerate(['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'], 1)}
        filtered_tweets = []
        for idx, tweet in enumerate(tweet_articles):
            try:
                raw_text = await tweet.inner_text()
                match = re.search(r'\b([A-Za-z]{3,9})\s(\d{1,2})\b', raw_text)
                if not match:
                    print(f"No date found in article {idx}")
                    continue
                month_str, day_str = match.group(1)[:3], match.group(2)
                month = month_map.get(month_str)
                day = int(day_str)
                tweet_date = datetime(today.year, month, day).date() if month and day else None
                if not tweet_date:
                    print(f"Could not parse date in article {idx}")
                    continue
                # Remove header lines (username, handle, date)
                lines = raw_text.split('\n')
                for i, line in enumerate(lines):
                    if re.match(r'^[A-Za-z]{3,9}\s\d{1,2}$', line):
                        tweet_text = '\n'.join(lines[i+1:]).strip()
                        break
                else:
                    tweet_text = raw_text.strip()
                filtered_tweets.append({"date": tweet_date.strftime('%Y-%m-%d'), "text": tweet_text})
            except Exception as e:
                print(f"Error parsing article {idx}: {e}")
        tweets = filtered_tweets
        await browser.close()
    return tweets

if __name__ == "__main__":
    user_profile = "https://x.com/gorv_garg"
    tweets = asyncio.run(scrape_last_2_days_tweets(user_profile))
    print("\nFetched tweets from last 2 days:")
    for tweet in tweets:
        # Replace newlines in tweet text with spaces and collapse multiple spaces
        clean_text = ' '.join(tweet['text'].split())
        print(f"{tweet['date']} | {clean_text}")
