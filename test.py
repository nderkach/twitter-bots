#!/usr/bin/env python

from flask import Flask, render_template, redirect, request, make_response, jsonify
from twython import Twython, TwythonError, TwythonAuthError
from redis import Redis
from twython import TwythonStreamer
import os
from threading import Thread

app = Flask(__name__)
redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
r = Redis.from_url(redis_url)

APP_KEY = "kHLxa38Nt8sT8P9lz4ymRcgHT"
APP_SECRET = "MLZzxOoFCBCtOVCkN1yssGrEMGiR7U4BW4oGoxRphvv0zoUlWp"
# ACCESS_TOKEN = "18433358-lE9CBUNqZ8ucITBiePnfmkTISSe3CkBKK34Uq88QC"
# ACCESS_TOKEN_SECRET = "UEgD6ZwIVJtjHP0T5vyft0LyiLoVXWBeiIRGsyg14vEgZ"

@app.route('/callback')
def callback():
    verifier = request.args.get('oauth_verifier')
    token = r.get("twitter:token")
    secret =  r.get("twitter:secret")
    twitter = Twython(APP_KEY, APP_SECRET, token, secret)
    last = twitter.get_authorized_tokens(verifier)
    twitter = Twython(APP_KEY, APP_SECRET, last['oauth_token'], last['oauth_token_secret'])
    r.set("twitter:token", last['oauth_token'])
    r.set("twitter:secret", last['oauth_token_secret'])

    return render_template('index.html')


@app.route('/')
def index():
    try:
        token = r.get("twitter:token")
        secret =  r.get("twitter:secret")
        twitter = Twython(APP_KEY, APP_SECRET, token, secret)
        twitter.verify_credentials()

    except:
        twitter = Twython(APP_KEY, APP_SECRET)
        print(request.host)
        auth = twitter.get_authentication_tokens(callback_url='http://' + request.host + '/callback')
        r.set("twitter:token", auth['oauth_token'])
        r.set("twitter:secret", auth['oauth_token_secret'])
        return redirect(auth['auth_url'])

    return render_template('index.html')

@app.route('/unfollow-nonfollowers')
def unfollow_nonfollowers():
    twitter = get_twitter()
    nfblist = not_following_back(twitter)
    for nfbid in nfblist:
        unfollow(nfbid)

    return make_response(jsonify( { 'count': len(nfblist) } ), 200)

def start_user_stream():
    token = r.get("twitter:token")
    secret =  r.get("twitter:secret")
    stream = MyStreamer(APP_KEY, APP_SECRET, token, secret)
    stream.user()

@app.route('/start-streaming')
def start_streaming():
    t = Thread(target=start_user_stream)
    t.start()
    return make_response(jsonify({}), 200)

def get_twitter():
    token = r.get("twitter:token")
    secret =  r.get("twitter:secret")
    return Twython(APP_KEY, APP_SECRET, token, secret)

def follow(user_id):
    twitter = get_twitter()
    twitter.create_friendship(user_id=user_id)

def unfollow(user_id):
    twitter = get_twitter()
    twitter.destroy_friendship(user_id=user_id)

def not_following_back(twitter):
    friends = twitter.get_friends_ids().get('ids')
    followers = twitter.get_followers_ids().get('ids')
    not_following_back_ids = [x for x in friends if x not in followers]
    return not_following_back_ids

class MyStreamer(TwythonStreamer):
    def on_success(self, data):
        # check if someone favorited or retweeted your stuff 
        user_id = None
        if 'event' in data:
            if data['event'] == 'favorite':
            #m aybe check additionally if it was a favorite/retweet or the oppooiste
            # hint: 
            # if data['event'] == 'favorite' or :
            # retweeted_count changes 
                user_id = data['source']['id']
            elif data['event'] == 'follow':
                # someone followed you
                r.set(data['target']['id'], 'follows', True)
        elif 'retweeted_status' in data:
            user_id = data['user']['id']

        if user_id:
            follow(user_id)

    def on_error(self, status_code, data):
        print(status_code, data)

# def get_favorited_users(twitter):


if __name__ == "__main__":
    app.run(debug=True)
