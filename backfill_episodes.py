#!/usr/bin/env python3
"""
Backfill Planning Center Publishing Episodes
Creates missing episodes for Sundays since August and populates them with YouTube videos
"""

import json
import requests
from requests.auth import HTTPBasicAuth
import os
from decouple import config
from datetime import datetime, timedelta
import time
import sys

# Load credentials
APP_ID = config('App_ID')
SECRET = config('Secret')
YTKEY = os.environ.get('YTKEY') or config('YTKEY')

# Setup logging
LOG_FILE = "backfill.log"

def log_message(message, also_print=True):
    """Write message to log file and optionally print to console"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}\n"

    with open(LOG_FILE, "a") as f:
        f.write(log_entry)

    if also_print:
        print(message)

def log_separator():
    """Write separator line with timestamp to log file"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    separator = f"{'='*50} {timestamp} {'='*50}\n"

    with open(LOG_FILE, "a") as f:
        f.write(separator)

def get_all_sundays_since_august():
    """Get all Sunday dates from August 31, 2025 until today"""
    sundays = []

    # Start from August 31, 2025 (which is a Sunday)
    start_date = datetime(2025, 8, 31).date()
    today = datetime.now().date()

    # Generate all Sundays from August 31 until today
    current_sunday = start_date
    while current_sunday <= today:
        sundays.append(current_sunday)
        current_sunday += timedelta(days=7)

    return sundays

def check_episode_exists(service_date):
    """Check if an episode exists for a given date"""
    service_date_str = service_date.strftime('%B %d, %Y')
    service_date_str = 'Sunday, ' + service_date_str

    # Search for episode by title
    search_url = f'https://api.planningcenteronline.com/publishing/v2/channels/3708/episodes?order=-published_live_at&where[search]={service_date_str}'

    try:
        response = requests.get(search_url, auth=HTTPBasicAuth(APP_ID, SECRET))

        if response.status_code != 200:
            log_message(f"WARNING: Failed to search for {service_date_str}. HTTP {response.status_code}")
            return None

        data = response.json()

        if 'data' in data and len(data['data']) > 0:
            # Episode exists
            episode = data['data'][0]
            return {
                'exists': True,
                'episode_id': episode['id'],
                'title': episode['attributes']['title']
            }
        else:
            # Episode does not exist
            return {
                'exists': False,
                'episode_id': None,
                'title': None
            }

    except Exception as e:
        log_message(f"ERROR: Exception checking episode for {service_date_str}: {e}")
        return None

def search_youtube_for_sunday_service(service_date):
    """Search YouTube for a Sunday Service video from a specific date"""

    try:
        # Search for videos published around the service date
        # YouTube API allows filtering by publishedAfter and publishedBefore
        # Search within 7 days before and after the service date
        date_before = service_date + timedelta(days=4)
        date_after = service_date - timedelta(days=4)

        published_after = date_after.strftime('%Y-%m-%dT00:00:00Z')
        published_before = date_before.strftime('%Y-%m-%dT23:59:59Z')

        search_url = (
            f"https://www.googleapis.com/youtube/v3/search?"
            f"part=snippet&"
            f"channelId=UCryZmERAkR6-fktliKiCGNA&"
            f"publishedAfter={published_after}&"
            f"publishedBefore={published_before}&"
            f"maxResults=20&"
            f"order=date&"
            f"type=video&"
            f"key={YTKEY}"
        )

        response = requests.get(search_url)

        if response.status_code != 200:
            log_message(f"WARNING: YouTube API failed. HTTP {response.status_code}")
            log_message(f"Response: {response.text[:200]}")
            return None

        data = response.json()

        if 'items' not in data or len(data['items']) == 0:
            log_message(f"No videos found on channel")
            return None

        # Look through results for "Sunday Service" in title
        best_match = None
        closest_diff = 999

        for item in data['items']:
            title = item['snippet']['title']
            video_id = item['id']['videoId']
            published_at = item['snippet']['publishedAt']

            # Check if title contains "Sunday Service" (case insensitive)
            title_upper = title.upper()
            if 'SUNDAY SERVICE' in title_upper:
                # Parse published date
                pub_date = datetime.strptime(published_at[:10], '%Y-%m-%d').date()

                # Calculate date difference
                date_diff = abs((pub_date - service_date).days)

                # Allow videos published within 3 days of the service (before or after)
                if date_diff <= 3:
                    log_message(f"  Candidate: '{title}' (ID: {video_id}, published: {pub_date}, diff: {date_diff} days)")

                    # Keep track of closest match
                    if date_diff < closest_diff:
                        closest_diff = date_diff
                        best_match = {
                            'video_id': video_id,
                            'title': title,
                            'published_at': published_at,
                            'date_diff': date_diff
                        }

        if best_match:
            log_message(f"Found match: '{best_match['title']}' (ID: {best_match['video_id']}, {best_match['date_diff']} days difference)")
            return best_match
        else:
            log_message(f"No Sunday Service video found for {service_date}")
            return None

    except Exception as e:
        log_message(f"ERROR: Exception searching YouTube: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_episode_with_video(service_date, youtube_video):
    """Create a new episode and populate it with YouTube video"""

    service_date_str = service_date.strftime('%B %d, %Y')
    service_title = 'Sunday, ' + service_date_str

    # Calculate timestamps
    date_str = service_date.strftime('%Y-%m-%d')
    starts_at = date_str + 'T13:45:00Z'
    starts_at_pco = date_str + 'T13:45:00+00:00'

    log_message(f"\n--- Creating Episode: {service_title} ---")

    # Step 1: Create episode
    episode_url = 'https://api.planningcenteronline.com/publishing/v2/channels/3708/episodes'
    episode_payload = {
        "data": {
            "attributes": {
                "published_to_library_at": starts_at,
                "title": service_title
            }
        }
    }

    try:
        log_message(f"Creating episode...")
        response = requests.post(
            episode_url,
            auth=HTTPBasicAuth(APP_ID, SECRET),
            json=episode_payload
        )

        if response.status_code not in [200, 201]:
            log_message(f"ERROR: Failed to create episode. HTTP {response.status_code}")
            log_message(f"Response: {response.text}")
            return False

        episode_data = response.json()
        episode_id = episode_data['data']['id']
        log_message(f"✓ Episode created: ID {episode_id}")

    except Exception as e:
        log_message(f"ERROR: Exception creating episode: {e}")
        return False

    # Step 2: Get episode time ID
    try:
        log_message(f"Getting episode time ID...")
        episode_times_url = f'https://api.planningcenteronline.com/publishing/v2/episodes/{episode_id}/episode_times'
        response = requests.get(episode_times_url, auth=HTTPBasicAuth(APP_ID, SECRET))

        if response.status_code != 200:
            log_message(f"ERROR: Failed to get episode times. HTTP {response.status_code}")
            return False

        times_data = response.json()
        if 'data' not in times_data or len(times_data['data']) == 0:
            log_message(f"ERROR: No episode times found")
            return False

        episode_time_id = times_data['data'][0]['id']
        log_message(f"✓ Episode time ID: {episode_time_id}")

    except Exception as e:
        log_message(f"ERROR: Exception getting episode time: {e}")
        return False

    # Step 3: Update episode time with YouTube video embed
    try:
        log_message(f"Updating episode time with YouTube video {youtube_video['video_id']}...")

        video_embed_payload = {
            "data": {
                "attributes": {
                    "starts_at": starts_at,
                    "video_embed_code": (
                        f"<iframe width='560' height='315' "
                        f"src='https://www.youtube.com/embed/{youtube_video['video_id']}' "
                        "frameborder='0' allow='accelerometer; autoplay; "
                        "clipboard-write; encrypted-media; gyroscope; "
                        "picture-in-picture; web-share' allowfullscreen></iframe>"
                    )
                }
            }
        }

        episode_time_url = f'https://api.planningcenteronline.com/publishing/v2/episodes/{episode_id}/episode_times/{episode_time_id}'
        response = requests.patch(
            episode_time_url,
            auth=HTTPBasicAuth(APP_ID, SECRET),
            json=video_embed_payload
        )

        if response.status_code not in [200, 201]:
            log_message(f"WARNING: Episode time update returned HTTP {response.status_code}")
            log_message(f"Response: {response.text}")
        else:
            log_message(f"✓ Episode time updated")

    except Exception as e:
        log_message(f"ERROR: Exception updating episode time: {e}")
        # Continue anyway - episode is created

    # Step 4: Update episode with library video URL
    try:
        log_message(f"Updating library video URL...")

        library_url = f"https://www.youtube.com/watch?v={youtube_video['video_id']}"
        library_payload = {
            "data": {
                "attributes": {
                    "library_video_url": library_url,
                    "published_to_library_at": starts_at_pco
                }
            }
        }

        episode_update_url = f'https://api.planningcenteronline.com/publishing/v2/episodes/{episode_id}'
        response = requests.patch(
            episode_update_url,
            auth=HTTPBasicAuth(APP_ID, SECRET),
            json=library_payload
        )

        if response.status_code not in [200, 201]:
            log_message(f"WARNING: Library URL update returned HTTP {response.status_code}")
            log_message(f"Response: {response.text}")
        else:
            log_message(f"✓ Library video URL updated")

    except Exception as e:
        log_message(f"ERROR: Exception updating library URL: {e}")
        # Continue anyway

    # Step 5: Get and update YouTube video description
    try:
        log_message(f"Fetching YouTube video description...")

        video_details_url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={youtube_video['video_id']}&key={YTKEY}"
        response = requests.get(video_details_url)

        if response.status_code == 200:
            video_data = response.json()
            if 'items' in video_data and len(video_data['items']) > 0:
                description = video_data['items'][0]['snippet']['description']

                if description:
                    description_payload = {
                        "data": {
                            "attributes": {
                                "description": description
                            }
                        }
                    }

                    response = requests.patch(
                        episode_update_url,
                        auth=HTTPBasicAuth(APP_ID, SECRET),
                        json=description_payload
                    )

                    if response.status_code in [200, 201]:
                        log_message(f"✓ Episode description updated ({len(description)} characters)")
                    else:
                        log_message(f"WARNING: Description update returned HTTP {response.status_code}")
                else:
                    log_message(f"Video has no description")
        else:
            log_message(f"WARNING: Failed to fetch video details. HTTP {response.status_code}")

    except Exception as e:
        log_message(f"WARNING: Exception fetching video description: {e}")
        # Continue anyway

    log_message(f"✓ Episode {episode_id} created and populated successfully")
    return True

def main():
    log_separator()
    log_message("=== Starting Backfill Process ===")

    if not YTKEY:
        log_message("ERROR: YTKEY environment variable not found")
        return 1

    # Get all Sundays since August 31, 2025
    log_message("\n--- Step 1: Finding all Sundays since August 31, 2025 ---")
    sundays = get_all_sundays_since_august()
    log_message(f"Found {len(sundays)} Sundays from {sundays[0]} to {sundays[-1]}")

    # Check which episodes are missing
    log_message("\n--- Step 2: Checking for existing episodes ---")
    missing_episodes = []
    existing_episodes = []

    for sunday in sundays:
        service_date_str = sunday.strftime('%B %d, %Y')
        log_message(f"Checking {service_date_str}...")

        result = check_episode_exists(sunday)

        if result is None:
            log_message(f"  ERROR: Could not check episode status")
            continue

        if result['exists']:
            log_message(f"  ✓ Episode exists: {result['episode_id']}")
            existing_episodes.append(sunday)
        else:
            log_message(f"  ✗ Episode missing")
            missing_episodes.append(sunday)

        # Rate limit - be nice to the API
        time.sleep(0.5)

    log_message(f"\nSummary: {len(existing_episodes)} existing, {len(missing_episodes)} missing")

    if len(missing_episodes) == 0:
        log_message("\n✓ No missing episodes - all Sundays have episodes!")
        return 0

    # Search YouTube for missing episodes
    log_message("\n--- Step 3: Searching YouTube for missing episodes ---")
    episodes_to_create = []

    for sunday in missing_episodes:
        service_date_str = sunday.strftime('%B %d, %Y')
        log_message(f"\nSearching YouTube for {service_date_str}...")

        youtube_video = search_youtube_for_sunday_service(sunday)

        if youtube_video:
            episodes_to_create.append({
                'date': sunday,
                'youtube': youtube_video
            })
            log_message(f"  ✓ Will create episode with video: {youtube_video['title']}")
        else:
            log_message(f"  ✗ No video found - skipping")

        # Rate limit for YouTube API
        time.sleep(1)

    log_message(f"\nFound YouTube videos for {len(episodes_to_create)} missing episodes")

    if len(episodes_to_create) == 0:
        log_message("\nNo episodes can be created (no matching YouTube videos found)")
        return 0

    # Confirm before creating
    log_message("\n--- Step 4: Creating Episodes ---")
    log_message(f"About to create {len(episodes_to_create)} episodes:")
    for ep in episodes_to_create:
        log_message(f"  - {ep['date'].strftime('%B %d, %Y')}: {ep['youtube']['title']}")

    log_message("\nStarting creation process...")

    created_count = 0
    failed_count = 0

    for ep in episodes_to_create:
        success = create_episode_with_video(ep['date'], ep['youtube'])

        if success:
            created_count += 1
        else:
            failed_count += 1

        # Rate limit between episode creations
        time.sleep(2)

    log_message(f"\n=== Backfill Complete ===")
    log_message(f"Created: {created_count}")
    log_message(f"Failed: {failed_count}")
    log_message(f"Total missing: {len(missing_episodes)}")
    log_message(f"Not found on YouTube: {len(missing_episodes) - len(episodes_to_create)}")

    return 0 if failed_count == 0 else 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        log_message("\nBackfill interrupted by user")
        sys.exit(130)
    except Exception as e:
        log_message(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
