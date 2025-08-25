

import asyncio
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

async def scrape_last_3_days_tweets(url):
    tweets = []
    today = datetime.utcnow().date()
    three_days_ago = today - timedelta(days=3)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_timeout(5000)
        last_height = None
        scroll_limit = 100
        scroll_count = 0
        while True:
            await page.evaluate("window.scrollBy(0, window.innerHeight);")
            await page.wait_for_timeout(2500)
            current_height = await page.evaluate("document.body.scrollHeight")
            if last_height == current_height:
                break
            last_height = current_height
            scroll_count += 1
            if scroll_count >= scroll_limit:
                break
        # Wait extra time for all content to load
        await page.wait_for_timeout(15000)
        tweet_articles = await page.locator('article').all()
        tweets = []
        for tweet in tweet_articles:
            time_locator = tweet.locator('time').first
            if not await time_locator.count():
                continue
            tweet_date_str = await time_locator.get_attribute('datetime')
            if not tweet_date_str:
                continue
            tweet_date = datetime.fromisoformat(tweet_date_str.replace("Z", "+00:00")).replace(tzinfo=None)
            tweet_date_only = tweet_date.date()
            text_locator = tweet.locator('[lang]').first
            tweet_text = await text_locator.inner_text() if await text_locator.count() else ""
            tweets.append({"date": tweet_date_str, "date_obj": tweet_date_only, "text": tweet_text})
        await browser.close()
    return tweets

if __name__ == "__main__":
    user_profile = "https://x.com/parvejkhan2009"
    tweets = asyncio.run(scrape_last_3_days_tweets(user_profile))
    if not tweets:
        print("No tweets found.")
    # Sort tweets by date descending
    tweets_sorted = sorted(tweets, key=lambda x: x['date_obj'], reverse=True)
    # Get the latest 5 days
    latest_dates = sorted({t['date_obj'] for t in tweets_sorted}, reverse=True)[:5]
    for tweet in tweets_sorted:
        if tweet['date_obj'] in latest_dates:
            clean_text = ' '.join(tweet['text'].split())
            print(f"{tweet['date']} | {clean_text}")
