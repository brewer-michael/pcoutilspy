#imports
import json
import requests
from requests.auth import HTTPBasicAuth
import os
from decouple import config
from datetime import datetime
import time
import sys
#define main function

APP_ID = config('App_ID')
SECRET = config('Secret')
auth = {'application_id':APP_ID,'secret':SECRET}

# Setup logging
LOG_FILE = "updateyoutube.log"

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
    #get most recent PCO sermon and update it once a live video is found at the specified youtube channel
    log_separator()
    log_message("=== Starting updateyoutube.py ===")

    apitoken = os.environ.get('YTKEY')
    if not apitoken:
        log_message("ERROR: YTKEY environment variable not found")
        return

    today = datetime.now().date()
    serviceDate = today.strftime('%B %d, %Y')
    serviceDate = 'Sunday, ' + serviceDate
    log_message(f"Looking for episode: {serviceDate}")

    pcoURL = 'https://api.planningcenteronline.com/publishing/v2/channels/3708/episodes?order=-published_live_at&page=1&where[search]=' + serviceDate

    try:
        res = requests.get(pcoURL,auth=HTTPBasicAuth(APP_ID,SECRET))

        if res.status_code != 200:
            log_message(f"ERROR: Failed to get episode from PCO. HTTP {res.status_code}")
            log_message(f"Response: {res.text}")
            return

        res_json = res.json()

        if 'data' not in res_json or len(res_json['data']) == 0:
            log_message(f"ERROR: No episodes found for {serviceDate}")
            return

        episodeId = res_json["data"][0]["id"]
        log_message(f"Found episode ID: {episodeId}")

    except Exception as e:
        log_message(f"ERROR: Failed to parse episode response: {e}")
        return

    #episodeId = res['data'][0]['id']
    #need to get back listing from youtube to update embed url accordingly
    #query episode id for starttimeid and assign youtube url
    startsAt = today.strftime('%Y-%m-%d')
    startsAt = startsAt + 'T13:45:00Z'
    youtubeUrl = 'https://api.planningcenteronline.com/publishing/v2/episodes/' + episodeId + '/episode_times'

    try:
        getepres = requests.get(youtubeUrl,auth=HTTPBasicAuth(APP_ID,SECRET))

        if getepres.status_code != 200:
            log_message(f"ERROR: Failed to get episode times. HTTP {getepres.status_code}")
            log_message(f"Response: {getepres.text}")
            return

        getepres_json = getepres.json()

        if 'data' not in getepres_json or len(getepres_json['data']) == 0:
            log_message("ERROR: No episode times found")
            return

        episodeTimeId = getepres_json["data"][0]["id"]
        log_message(f"Found episode time ID: {episodeTimeId}")

    except Exception as e:
        log_message(f"ERROR: Failed to parse episode times: {e}")
        return

    #print(getepres)
    #episodeTimeId = getepres['data'][0]['id']
    #print(episodeTimeId)
    episodeTimeURL = 'https://api.planningcenteronline.com/publishing/v2/episodes/'+ episodeId + '/episode_times/'+ episodeTimeId
    #episodeTimeId = getepres['data'][0]['id']
    #create a wait timer to get a valid youtube video id or else fail out the file
    def GetYoutubeVideoId(apitoken):
        youtubeLiveUrl = 'https://www.googleapis.com/youtube/v3/search?part=snippet&eventType=live&maxResults=1&order=date&type=video&key=' + apitoken  + '&channelId=UCryZmERAkR6-fktliKiCGNA'

        log_message("Searching for live YouTube stream...")
        for attempt in range(30):  # 30 attempts with 10-second intervals = 5 minutes
                # Make the request
                try:
                        getYoutubeLive = requests.get(youtubeLiveUrl)
                        if getYoutubeLive.status_code != 200:
                            log_message(f"Attempt {attempt + 1}/30: YouTube API returned status {getYoutubeLive.status_code}")
                            time.sleep(10)
                            continue

                        getYoutubeLive_json = getYoutubeLive.json()

                        # Check if we have items in the response
                        if 'items' in getYoutubeLive_json and len(getYoutubeLive_json['items']) > 0:
                            youtubeLiveId = getYoutubeLive_json['items'][0]['id']['videoId']
                            log_message(f"Found live stream: {youtubeLiveId}")
                            return youtubeLiveId
                        else:
                            log_message(f"Attempt {attempt + 1}/30: No live stream found yet")
                except (KeyError, IndexError) as e:
                        log_message(f"Attempt {attempt + 1}/30: Error parsing response - {e}")
                except Exception as e:
                        log_message(f"Attempt {attempt + 1}/30: Unexpected error - {e}")

                # Wait for 10 seconds before making the request again
                time.sleep(10)

        # If no live stream found, try to get the most recent stream from the channel
        log_message("No live stream found after 5 minutes. Attempting to get most recent stream...")
        try:
            # Get most recent uploaded video from the channel (not filtered by eventType=live)
            recentStreamUrl = 'https://www.googleapis.com/youtube/v3/search?part=snippet&channelId=UCryZmERAkR6-fktliKiCGNA&maxResults=1&order=date&type=video&key=' + apitoken
            recentStreamResponse = requests.get(recentStreamUrl)

            if recentStreamResponse.status_code != 200:
                log_message(f"Failed to get recent streams: HTTP {recentStreamResponse.status_code}")
                log_message(f"Response: {recentStreamResponse.text}")
                raise Exception(f"YouTube API error: {recentStreamResponse.status_code}")

            recentStream_json = recentStreamResponse.json()

            if 'items' in recentStream_json and len(recentStream_json['items']) > 0:
                recentVideoId = recentStream_json['items'][0]['id']['videoId']
                videoTitle = recentStream_json['items'][0]['snippet']['title']
                log_message(f"Found most recent video: {recentVideoId} - '{videoTitle}'")
                return recentVideoId
            else:
                log_message("No videos found on channel")
                raise Exception("No videos found on channel")

        except Exception as e:
            log_message(f"Error getting most recent stream: {e}")
            raise Exception(f"Unable to get YouTube video ID after all attempts: {e}")
    
    #print(getepres)
    try:
        youtubeVideoId = GetYoutubeVideoId(apitoken)
        #youtubeEmbed = '{\"data\":{\"attributes\":{\"starts_at\":'+startsAt+',\"video_embed_code\":\"<iframe width=\\\"560\\\" height=\\\"315\\\" src=\\\"https://www.youtube.com/embed/'+ youtubeVideoId +'?autoplay=1&amp;playsinline=1\\\" frameborder=\\\"0\\\" allow=\\\"accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share\\\" allowfullscreen></iframe>\\\\"}}}'
        #youtubeEmbed = '{\"data\":{\"attributes\":{\"starts_at\":'+startsAt+',\"video_embed_code\":\"<iframe width=\\\"560\\\" height=\\\"315\\\" src=\\\"https://www.youtube.com/embed/'+ youtubeVideoId +'\\\" frameborder=\\\"0\\\" allow=\\\"accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share\\\" allowfullscreen></iframe>\\\\"}}}'
        
        youtubeEmbed = {
            "data": {
                "attributes": {
                    "starts_at": startsAt,
                    "video_embed_code": (
                        f"<iframe width='560' height='315' "
                        f"src='https://www.youtube.com/embed/{youtubeVideoId}' "
                        "frameborder='0' allow='accelerometer; autoplay; "
                        "clipboard-write; encrypted-media; gyroscope; "
                        "picture-in-picture; web-share' allowfullscreen></iframe>"
                    )
                }
            }
        }

        log_message(f"\nUpdating episode with YouTube video ID: {youtubeVideoId}")
        patchIframe = requests.patch(episodeTimeURL,auth=HTTPBasicAuth(APP_ID,SECRET),json=youtubeEmbed)

        if patchIframe.status_code not in [200, 201]:
            log_message(f"WARNING: Episode time iframe patch returned HTTP {patchIframe.status_code}")
            log_message(f"Response: {patchIframe.text}")
        else:
            log_message(f"✓ Episode time iframe updated successfully (HTTP {patchIframe.status_code})")

        # Log patchIframe attributes
        log_file = "pco_patch_log.txt"

        with open(log_file, "a") as f:
            f.write("=== YouTube Embed Payload ===\n")
            f.write(json.dumps(youtubeEmbed, indent=2))  # nicely formatted JSON
            f.write("\n" + "="*20 + "\n")
            f.write("=== PATCH Response ===\n")
            f.write(f"Status: {patchIframe.status_code}\n")
            try:
                f.write(json.dumps(patchIframe.json(), indent=2))
            except Exception:
                f.write(patchIframe.text)  # fallback if response is not JSON
            f.write("\n" + "="*20 + "\n\n")

        libraryVideoURL = 'https://www.youtube.com/watch?v=' + youtubeVideoId
        libraryPayload = {"data": {"attributes": {"library_video_url": libraryVideoURL}}}

        pcoEpisodeURL = 'https://api.planningcenteronline.com/publishing/v2/episodes/' + episodeId
        log_message(f"\nUpdating library video URL...")
        addLibrary = requests.patch(pcoEpisodeURL,auth=HTTPBasicAuth(APP_ID,SECRET),json=libraryPayload)

        if addLibrary.status_code not in [200, 201]:
            log_message(f"WARNING: Library video URL patch returned HTTP {addLibrary.status_code}")
            log_message(f"Response: {addLibrary.text}")
        else:
            log_message(f"✓ Library video URL updated successfully (HTTP {addLibrary.status_code})")

        log_message(f"\nFetching YouTube video description...")
        youtubeVideoUrl = 'https://www.googleapis.com/youtube/v3/videos?part=snippet&id=' + youtubeVideoId + '&key=' + apitoken
        youtubeVideoResponse = requests.get(youtubeVideoUrl)

        if youtubeVideoResponse.status_code != 200:
            log_message(f"WARNING: Failed to get YouTube video details. HTTP {youtubeVideoResponse.status_code}")
        else:
            youtubeVideoObject = youtubeVideoResponse.json()
            if 'items' in youtubeVideoObject and len(youtubeVideoObject['items']) > 0:
                youtubeVideoDescription = youtubeVideoObject['items'][0]['snippet']['description']
                log_message(f"✓ Retrieved video description ({len(youtubeVideoDescription)} characters)")

                summaryPayload = {
                    "data": {
                        "attributes": {
                            "description": youtubeVideoDescription
                        }
                    }
                }
                log_message(f"\nUpdating episode description...")
                addSummary = requests.patch(pcoEpisodeURL,auth=HTTPBasicAuth(APP_ID,SECRET),json=summaryPayload)

                if addSummary.status_code not in [200, 201]:
                    log_message(f"WARNING: Episode description patch returned HTTP {addSummary.status_code}")
                    log_message(f"Response: {addSummary.text}")
                else:
                    log_message(f"✓ Episode description updated successfully (HTTP {addSummary.status_code})")
            else:
                log_message("WARNING: No video details found in YouTube response")

        log_message("\n=== Update completed successfully ===")

    except Exception as e:
        log_message(f"\nERROR: Update failed with exception: {e}")
        import traceback
        import io
        # Capture traceback to string and log it
        tb_stream = io.StringIO()
        traceback.print_exc(file=tb_stream)
        log_message(tb_stream.getvalue(), also_print=False)
        # Also print to console
        traceback.print_exc()
        exit()

if __name__ == "__main__":
        try:
                main()
        except Fail:
                sys.exit()
        else:
                pingConfirm = requests.get('https://hc-ping.com/78356338-0428-4f04-ad71-b3f805264745')
