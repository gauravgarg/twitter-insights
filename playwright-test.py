from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta

def scrape_last_3_days_tweets(url):
    tweets = []
    three_days_ago = datetime.utcnow() - timedelta(days=3)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        page.wait_for_selector("[data-testid='tweet']")

        last_height = None

        while True:
            tweet_elements = page.query_selector_all("[data-testid='tweet']")

            new_tweets = []
            for tweet in tweet_elements:
                time_elem = tweet.query_selector("time")
                if not time_elem:
                    continue
                tweet_date_str = time_elem.get_attribute("datetime")
                tweet_date = datetime.fromisoformat(tweet_date_str.replace("Z", "+00:00")).replace(tzinfo=None)
                if tweet_date < three_days_ago:
                    page.close()
                    browser.close()
                    return tweets + new_tweets

                text_elem = tweet.query_selector("[lang]")
                tweet_text = text_elem.inner_text() if text_elem else ""
                new_tweets.append({"date": tweet_date_str, "text": tweet_text})

            for nt in new_tweets:
                if nt not in tweets:
                    tweets.append(nt)

            page.evaluate("window.scrollBy(0, window.innerHeight);")
            page.wait_for_timeout(2000)  # adjust delay as needed

            current_height = page.evaluate("document.body.scrollHeight")
            if last_height == current_height:
                break
            last_height = current_height

        browser.close()
    return tweets

if __name__ == "__main__":
    user_profile = "https://twitter.com/mfuz994221"
    tweets_last_3_days = scrape_last_3_days_tweets(user_profile)
    for i, tweet in enumerate(tweets_last_3_days, 1):
        print(f"Tweet {i} ({tweet['date']}): {tweet['text']}\n")
    print(f"Total tweets in last 3 days: {len(tweets_last_3_days)}")