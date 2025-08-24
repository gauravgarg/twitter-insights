import requests
import re
import json
from datetime import datetime, timedelta
from time import sleep

GUEST_TOKEN_ENDPOINT = "https://api.twitter.com/1.1/guest/activate.json"
STATUS_ENDPOINT = "https://twitter.com/i/api/graphql/"

CURSOR_PATTERN = re.compile('TimelineCursor","value":"([^"]+)"[^]+Bottom"')
ID_PATTERN = re.compile('"rest_id":"([^"]+)"')
COUNT_PATTERN = re.compile('"statuses_count":([0-9]+)')

variables = {
    "count": 100,
    "withTweetQuoteCount": True,
    "includePromotedContent": True,
    "withQuickPromoteEligibilityTweetFields": False,
    "withSuperFollowsUserFields": True,
    "withUserResults": True,
    "withBirdwatchPivots": False,
    "withDownvotePerspective": False,
    "withReactionsMetadata": False,
    "withReactionsPerspective": False,
    "withSuperFollowsTweetFields": True,
    "withVoice": True,
    "withV2Timeline": False,
}

features = {
    "standardized_nudges_misinfo": True,
    "dont_mention_me_view_api_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "interactive_text_enabled": True,
    "responsive_web_enhance_cards_enabled": True,
    "responsive_web_uc_gql_enabled": True,
    "vibe_tweet_context_enabled": True,
}

def send_request(url, session_method, headers, params=None):
    if params:
        response = session_method(url, headers=headers, stream=True, params={
            "variables": json.dumps(params),
            "features": json.dumps(features)
        })
    else:
        response = session_method(url, headers=headers, stream=True)
    assert response.status_code == 200, f"Failed request to {url}. {response.status_code}. {response.text}"
    result = [line.decode("utf-8") for line in response.iter_lines()]
    return "".join(result)

def search_json(j, target_key, result):
    if type(j) == dict:
        for key in j:
            if key == target_key:
                result.append(j[key])
            search_json(j[key], target_key, result)
        return result
    if type(j) == list:
        for item in j:
            search_json(item, target_key, result)
        return result
    return result

def tweet_subset(d):
    return {
        "id": d["id_str"],
        "text": d["full_text"],
        "created_at": d["created_at"],
    }

def get_tweets(query_id, session, headers, variables, expected_total):
    resp = send_request(f"{STATUS_ENDPOINT}{query_id}/UserTweetsAndReplies", session.get, headers, variables)
    j = json.loads(resp)
    all_tweets = search_json(j, "legacy", [])
    all_tweets = [tweet for tweet in all_tweets if "id_str" in tweet]
    ids = {tweet["id_str"] for tweet in all_tweets}
    while True:
        cursor = CURSOR_PATTERN.findall(resp)[0]
        variables["cursor"] = cursor
        resp = send_request(f"{STATUS_ENDPOINT}{query_id}/UserTweetsAndReplies", session.get, headers, variables)
        j = json.loads(resp)
        next_tweets = search_json(j, "legacy", [])
        next_tweets = [tweet for tweet in next_tweets if "id_str" in tweet]
        next_ids = {tweet["id_str"] for tweet in next_tweets}
        old_id_size = len(ids)
        ids.update(next_ids)
        if old_id_size == len(ids):
            break
        all_tweets.extend(next_tweets)
        if len(all_tweets) > expected_total:
            break
    all_tweets = [tweet for tweet in all_tweets if "full_text" in tweet and tweet.get("user_id_str", "") == variables["userId"]]
    return all_tweets

def get_id_and_tweet_count(session, headers, query_id, username):
    resp = send_request(
        f"{STATUS_ENDPOINT}{query_id}/UserByScreenName",
        session.get,
        headers,
        params={
            "screen_name": username,
            "withSafetyModeUserFields": True,
            "withSuperFollowsUserFields": True
        }
    )
    ids = ID_PATTERN.findall(resp)
    counts = COUNT_PATTERN.findall(resp)
    return ids[0], int(counts[0])

def user_tweets_last_3_days(username):
    print(f"Getting Tweets for {username}")
    session = requests.Session()
    headers = {}
    container = send_request(f"https://twitter.com/{username}", session.get, headers)
    js_files = re.findall(r"src=['\"]([^'\"()]*js)['\"]", container)
    bearer_token = None
    query_id = None
    user_query_id = None
    for f in js_files:
        file_content = send_request(f, session.get, headers)
        bt = re.search(r'"([A-Za-z0-9%-]+%[A-Za-z0-9%-]+)"', file_content)
        ops = re.findall(r'\{queryId:"[A-Za-z0-9_]+[^\}]+UserTweetsAndReplies"', file_content)
        query_op = [op for op in ops if "UserTweetsAndReplies" in op]
        if len(query_op) == 1:
            query_id = re.findall('queryId:"([^"]+)"', query_op[0])[0]
        if bt:
            bearer_token = bt.group(1)
        ops = re.findall(r'\{queryId:"[A-Za-z0-9_]+[^\}]+UserByScreenName"', file_content)
        user_query_op = [op for op in ops if "UserByScreenName" in op]
        if len(user_query_op) == 1:
            user_query_id = re.findall('queryId:"([^"]+)"', user_query_op[0])[0]
    headers['authorization'] = f"Bearer {bearer_token}"
    guest_token_resp = send_request(GUEST_TOKEN_ENDPOINT, session.post, headers)
    guest_token = json.loads(guest_token_resp)['guest_token']
    headers['x-guest-token'] = guest_token
    user_id, total_count = get_id_and_tweet_count(session, headers, user_query_id, username)
    session.close()
    variables["userId"] = user_id
    resp = get_tweets(query_id, session, headers, variables, total_count)
    all_tweets = [tweet_subset(tweet) for tweet in resp]
    # Filter last 3 days
    three_days_ago = datetime.now() - timedelta(days=3)
    last_3_days = []
    for tweet in all_tweets:
        tweet_time = datetime.strptime(tweet["created_at"], "%a %b %d %H:%M:%S %z %Y")
        if tweet_time > three_days_ago:
            last_3_days.append(tweet)
    for tweet in last_3_days:
        print(f"{tweet['created_at']} | {tweet['id']} | {tweet['text']}")
    print(f"Total tweets in last 3 days for {username}: {len(last_3_days)}")
    return last_3_days

if __name__ == "__main__":
    import sys
    username = "mfuz994221"
    if not username:
        print("Usage: python fetch_last3days.py <twitter_username>")
        sys.exit(1)
    user_tweets_last_3_days(username)
