#imports
import json
import requests
from requests.auth import HTTPBasicAuth
import os
from decouple import config
from datetime import datetime
import sys
#define main function

APP_ID = config('App_ID')
SECRET = config('Secret')
auth = {'application_id':APP_ID,'secret':SECRET}

# Setup logging
LOG_FILE = "main.log"

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

def main():
    #create new service and return episode id
    log_separator()
    log_message("=== Starting main.py ===")

    url = 'https://api.planningcenteronline.com/publishing/v2/channels/3708/episodes'
    today = datetime.now().date()
    serviceDate = today.strftime('%B %d, %Y')
    dateNow = today.strftime('%Y-%m-%d')
    startsAt = dateNow + 'T13:45:00Z'
    startsAtPCO = dateNow + 'T13:45:00+00:00'
    serviceDate = 'Sunday, ' + serviceDate
    log_message(f"Creating episode for: {serviceDate}")
#    payload= '{\"data\":{\"attributes\":{\"published_to_library_at\":'+startsAt+',\"title\":'+serviceDate+'}}}'
#    headers = {}
#    res = requests.post(url,auth=HTTPBasicAuth(APP_ID,SECRET),data=payload).json()

    # Build JSON payload with 'data' as required
    payload = {
        "data": {
            "attributes": {
                "published_to_library_at": startsAt,
                "title": serviceDate
            }
        }
    }

    # --- Create new episode ---
    log_message("\nCreating new episode in Planning Center...")
    res = requests.post(
        url,
        auth=HTTPBasicAuth(APP_ID, SECRET),
        json=payload   # send JSON with "data"
    )

    if res.status_code not in [200, 201]:
        log_message(f"ERROR: Failed to create episode. HTTP {res.status_code}")
        log_message(f"Response: {res.text}")
        return
    else:
        log_message(f"✓ Episode created successfully (HTTP {res.status_code})")

    res_json = res.json()

    if 'data' not in res_json or 'id' not in res_json['data']:
        log_message("ERROR: Invalid response from episode creation")
        log_message(f"Response: {res.text}")
        return

    episodeId = res_json['data']['id']
    log_message(f"Episode ID: {episodeId}")
    #query episode id for starttimeid and assign youtube url
#    youtubeEmbed = '{\"data\":{\"attributes\":{\"starts_at\":'+startsAt+',\"video_embed_code\":\"<iframe width=\\\"560\\\" height=\\\"315\\\" src=\\\"https://www.youtube.com/embed/live_stream?autoplay=1&amp;channel=RaDDkBdBMRA&amp;playsinline=1\\\" frameborder=\\\"0\\\" allow=\\\"accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture\\\" allowfullscreen></iframe>\"}}}'
 
       # --- YouTube embed payload ---
    youtubeEmbed = {
        "data": {
            "attributes": {
                "starts_at": startsAt,
                "video_embed_code": """<iframe width="560" height="315"
                 src="https://www.youtube.com/embed/live_stream?autoplay=1&amp;channel=RaDDkBdBMRA&amp;playsinline=1"
                 frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                 allowfullscreen></iframe>"""
            }
        }
    }


    log_message("\nGetting episode time ID...")
    youtubeUrl = 'https://api.planningcenteronline.com/publishing/v2/episodes/' + episodeId + '/episode_times'
    getepres = requests.get(youtubeUrl,auth=HTTPBasicAuth(APP_ID,SECRET))

    if getepres.status_code != 200:
        log_message(f"ERROR: Failed to get episode times. HTTP {getepres.status_code}")
        log_message(f"Response: {getepres.text}")
        return

    getepres_json = getepres.json()

    if 'data' not in getepres_json or len(getepres_json['data']) == 0:
        log_message("ERROR: No episode times found")
        return

    episodeTimeId = getepres_json['data'][0]['id']
    log_message(f"Episode time ID: {episodeTimeId}")

    episodeTimeURL = 'https://api.planningcenteronline.com/publishing/v2/episodes/'+ episodeId + '/episode_times/'+ episodeTimeId

    log_message("\nUpdating episode with YouTube livestream embed...")
    patchIframe = requests.patch(episodeTimeURL,auth=HTTPBasicAuth(APP_ID,SECRET),json=youtubeEmbed)

    if patchIframe.status_code not in [200, 201]:
        log_message(f"WARNING: Episode iframe patch returned HTTP {patchIframe.status_code}")
        log_message(f"Response: {patchIframe.text}")
    else:
        log_message(f"✓ Episode iframe updated successfully (HTTP {patchIframe.status_code})")

    libraryUrl = 'https://api.planningcenteronline.com/publishing/v2/episodes/'+ episodeId +'/'
    libraryData = {
        "data": {
            "attributes": {
                "published_to_library_at": startsAtPCO
            }
        }
    }

    log_message("\nPublishing episode to library...")
    addLibrary = requests.patch(libraryUrl,auth=HTTPBasicAuth(APP_ID,SECRET),json=libraryData)

    if addLibrary.status_code not in [200, 201]:
        log_message(f"WARNING: Library publication patch returned HTTP {addLibrary.status_code}")
        log_message(f"Response: {addLibrary.text}")
    else:
        log_message(f"✓ Episode published to library successfully (HTTP {addLibrary.status_code})")

    log_message("\n=== Episode creation completed successfully ===")

if __name__ == "__main__":
        try:
                main()
        except Fail:
                sys.exit()
        else:
                pingConfirm = requests.get('https://hc-ping.com/0996324d-68a4-4098-a8ce-84152a1c132a')


