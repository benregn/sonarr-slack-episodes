#!/usr/bin/python3
import json
import os
from collections import OrderedDict
from collections import defaultdict
from datetime import datetime
from datetime import timedelta

import requests

SONARR_API_URL = os.environ['SONARR_API_URL']
SONARR_API_KEY = os.environ['SONARR_API_KEY']
SLACK_WEBHOOK = os.environ['SLACK_WEBHOOK']


def datetime_to_string(_datetime):
    return _datetime.strftime('%Y-%m-%dT%H:%M:%SZ')


def build_url(base, *parts):
    pieces = [base] + parts
    return '/'.join(s.strip('/') for s in pieces)


def get_current_week_episodes(session):
    week_start = datetime.now().replace(hour=0, minute=0, second=0) - timedelta(days=1)
    params = {
        'start': datetime_to_string(week_start),
        'end': datetime_to_string(week_start + timedelta(days=7)),
    }
    resp = session.get(
        url=build_url(SONARR_API_URL, '/calendar'),
        params=params,
    )
    return resp.json()


def process_episodes_per_day(episodes):
    per_day = defaultdict(list)
    for episode in episodes:
        air_date = datetime.strptime(episode['airDate'], '%Y-%m-%d') + timedelta(days=1)
        per_day[air_date].append({
            'episode_title': episode['title'],
            'series_title': episode['series']['title'],
            'episode_number': episode['episodeNumber'],
            'season_number': episode['seasonNumber'],
        })
    return per_day


def format_episode(episode):
    return '{series_title} (S{season_num}E{episode_num} - {episode_title})'.format(
        series_title=episode['series_title'],
        season_num=episode['season_number'],
        episode_num=episode['episode_number'],
        episode_title=episode['episode_title'],
    )


def format_message(episodes_per_day):
    def _lines():
        for air_date, episodes in OrderedDict(sorted(episodes_per_day.items())).items():
            yield air_date.strftime('*%A* - %d/%m')
            for episode in episodes:
                yield format_episode(episode)
            yield ''
    return '\n'.join(_lines()).strip()


def send_slack_message(message):
    resp = requests.post(
        url=SLACK_WEBHOOK,
        json={
            'text': message,
        },
    )


def main():
    session = requests.Session()
    session.headers.update({'X-Api-Key': SONARR_API_KEY})

    episodes = get_current_week_episodes(session)

    episodes_per_day = process_episodes_per_day(episodes)

    message = format_message(episodes_per_day)

    send_slack_message(message)


if __name__ == '__main__':
    main()
