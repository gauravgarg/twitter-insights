import snscrape.modules.twitter as sntwitter
import pandas as pd
from datetime import datetime, timedelta

# Username to scrape
username = 'mfuz994221'

# Define the date range (last 3 days)
until_date = datetime.utcnow()
since_date = until_date - timedelta(days=3)

# Format dates in YYYY-MM-DD format
since_str = since_date.strftime('%Y-%m-%d')
until_str = until_date.strftime('%Y-%m-%d')

# Container for tweets
tweets = []

# Use TwitterSearchScraper with from:user since:date until:date query
query = f"from:{username} since:{since_str} until:{until_str}"

# Scrape tweets
for i, tweet in enumerate(sntwitter.TwitterSearchScraper(query).get_items()):
    tweets.append([tweet.date, tweet.id, tweet.content])

# Create a DataFrame
df = pd.DataFrame(tweets, columns=['Date', 'Tweet ID', 'Content'])

# Display the tweets
print(df)

# Optionally save to CSV
# df.to_csv(f'{username}_last_3_days_tweets.csv', index=False)
