#imports
import json
import requests
from requests.auth import HTTPBasicAuth
import os
from decouple import config
from datetime import date
#define main function

APP_ID = config('App_ID')
SECRET = config('Secret')
auth = {'application_id':APP_ID,'secret':SECRET}

def main():
    #create new service and return episode id
    apitoken = os.environ.get('YTKEY')	
    url = 'https://www.googleapis.com/youtube/v3/search?part=snippet&channelId=UCryZmERAkR6-fktliKiCGNA&eventType=live&maxResults=1&order=date&type=video&key=' + apitoken 
    today = date.today()
    serviceDate = today.strftime('%B %d, %Y\"')
    serviceDate = '\"Sunday, ' + serviceDate
    payload= '{\"data\":{\"attributes\":{\"title\":'+serviceDate+'}}}'
    headers = {}
    pcoURL = 'https://api.planningcenteronline.com/publishing/v2/channels/3708/episodes?order=-published_live_at&page=1&where[search]=' + serviceDate + '>'
    res = requests.get(pcoURL,auth=HTTPBasicAuth(APP_ID,SECRET)).json()
    episodeId = res['data']['id']
    #need to get back listing from youtube to update embed url accordingly
    #query episode id for starttimeid and assign youtube url
    startsAt = today.strftime('\"%Y-%m-%d')
    startsAt = startsAt + 'T13:45:00Z\"'
    youtubeEmbed = '{\"data\":{\"attributes\":{\"starts_at\":'+startsAt+',\"video_embed_code\":\"<iframe width=\\\"560\\\" height=\\\"315\\\" src=\\\"https://www.youtube.com/embed/'+ episodeId +'?autoplay=1&amp;playsinline=1\\\" frameborder=\\\"0\\\" allow=\\\"accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share\\\" allowfullscreen></iframe>\\\\"}}}'
    print(youtubeEmbed)
    youtubeUrl = 'https://www.googleapis.com/youtube/v3/search?part=snippet&eventType=live&maxResults=1&order=date&type=video&key=' + apitoken  + '&channelId=UCryZmERAkR6-fktliKiCGNA'
    getepres = requests.get(youtubeUrl,auth=HTTPBasicAuth(APP_ID,SECRET),data=youtubeEmbed).json()
    #print(getepres)
    episodeTimeId = getepres['data'][0]['id']
    print(episodeTimeId)
    episodeTimeURL = 'https://api.planningcenteronline.com/publishing/v2/episodes/'+ episodeId + '/episode_times/'+ episodeTimeId
    patchIframe = requests.patch(episodeTimeURL,auth=HTTPBasicAuth(APP_ID,SECRET),data=youtubeEmbed)
    print(patchIframe)
    libraryUrl = 'https://api.planningcenteronline.com/publishing/v2/episodes/'+ episodeId +'/'
    libraryData = '{\"data\":{\"attributes\":{\"published_to_library_at\":'+startsAt+'}}}'
    addLibrary = requests.patch(libraryUrl,auth=HTTPBasicAuth(APP_ID,SECRET),data=libraryData)
    #print(addLibrary)

if __name__ == "__main__":
        try:
                main()
        except Fail:
                sys.exit()
        else:
                pingConfirm = requests.get('https://hc-ping.com/0996324d-68a4-4098-a8ce-84152a1c132a')

