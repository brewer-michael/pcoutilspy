#imports
import json
import requests
from requests.auth import HTTPBasicAuth
import os
from decouple import config
from datetime import date
import time
#define main function

APP_ID = config('App_ID')
SECRET = config('Secret')
auth = {'application_id':APP_ID,'secret':SECRET}

def main():
    #get most recent PCO sermon and update it once a live video is found at the specified youtube channel
    apitoken = str(os.environ.get('YTKEY'))
    today = date.today()
    serviceDate = today.strftime('%B %d, %Y')
    serviceDate = 'Sunday, ' + serviceDate
    pcoURL = 'https://api.planningcenteronline.com/publishing/v2/channels/3708/episodes?order=-published_live_at&page=1&where[search]=' + serviceDate
    res = requests.get(pcoURL,auth=HTTPBasicAuth(APP_ID,SECRET)).json()
    print(res)
    episodeId = res['data'][0]['id']
    #need to get back listing from youtube to update embed url accordingly
    #query episode id for starttimeid and assign youtube url
    startsAt = today.strftime('\"%Y-%m-%d')
    startsAt = startsAt + 'T13:45:00Z\"'
    youtubeUrl = 'https://api.planningcenteronline.com/publishing/v2/episodes/' + episodeId + '/episode_times'
    getepres = requests.get(youtubeUrl,auth=HTTPBasicAuth(APP_ID,SECRET)).json()
    #print(getepres)
    episodeTimeId = getepres['data'][0]['id']
    print(episodeTimeId)
    episodeTimeURL = 'https://api.planningcenteronline.com/publishing/v2/episodes/'+ episodeId + '/episode_times/'+ episodeTimeId
    #episodeTimeId = getepres['items'][0]['id']
    print(episodeTimeId)
    #create a wait timer to get a valid youtube video id or else fail out the file
    def GetYoutubeVideoId(apitoken):
        youtubeLiveUrl = 'https://www.googleapis.com/youtube/v3/search?part=snippet&eventType=live&maxResults=1&order=date&type=video&key=' + apitoken  + '&channelId=UCryZmERAkR6-fktliKiCGNA'
        for _ in range(2):  # 30 attempts with 10-second intervals = 5 minutes
                # Make the request
                try:
                        getYoutubeLive = requests.get(youtubeLiveUrl).json()
                        youtubeLiveId = getYoutubeLive['items'][0]['id']['videoId']
                        return youtubeLiveId
                except (KeyError, IndexError):
                        pass

                # Wait for 10 seconds before making the request again
                time.sleep(10)

        # If no videoId is found after waiting, raise an exception or exit the file
        raise Exception("Timeout: Unable to get YouTube Live ID")
    
    #print(getepres)
    try:
        youtubeVideoId = GetYoutubeVideoId(apitoken)
        youtubeEmbed = '{\"data\":{\"attributes\":{\"starts_at\":'+startsAt+',\"video_embed_code\":\"<iframe width=\\\"560\\\" height=\\\"315\\\" src=\\\"https://www.youtube.com/embed/'+ youtubeVideoId +'?autoplay=1&amp;playsinline=1\\\" frameborder=\\\"0\\\" allow=\\\"accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share\\\" allowfullscreen></iframe>\\\\"}}}'
        print(youtubeEmbed)
        patchIframe = requests.patch(episodeTimeURL,auth=HTTPBasicAuth(APP_ID,SECRET),data=youtubeEmbed)
        print(patchIframe)
        #print(addLibrary)
    except Exception:
           exit()

if __name__ == "__main__":
        try:
                main()
        except Fail:
                sys.exit()
        else:
                pingConfirm = requests.get('https://hc-ping.com/0996324d-68a4-4098-a8ce-84152a1c132a')
