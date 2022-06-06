#imports
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
    url = 'https://api.planningcenteronline.com/publishing/v2/channels/3708/episodes'
    today = date.today()
    serviceDate = today.strftime('%B %d, %Y\"')
    serviceDate = '\"Sunday, ' + serviceDate
    payload= '{\"data\":{\"attributes\":{\"title\":'+serviceDate+'}}}'
    headers = {}
    res = requests.post(url,auth=HTTPBasicAuth(APP_ID,SECRET),data=payload)
    res = res.json()
    print(res)
    episodeId = res.id
    startsAt = today.strftime('%d/%m/%Y')
    startsAt = startsAt + 'T13:45:00+00:00'
    youtubeEmbed = {'data':{'attributes':{'starts_at':startsAt,'video_embed_code':'<iframe width=\'560\' height=\'315\' src=\'https://www.youtube.com/embed/live_stream?autoplay=1&amp;channel=UCryZmERAkR6-fktliKiCGNA&amp;playsinline=1\' frameborder=\'0\' allow=\'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture\' allowfullscreen></iframe>'}}}
    youtubeUrl = 'https://api.planningcenteronline.com/publishing/v2/episodes/' + episodeId + '/episode_times'
    getepres = requests.get(youtubeUrl,auth=HTTPBasicAuth(APP_ID,SECRET),data=youtubeEmbed)
    getepres()
    libraryUrl = 'https://api.planningcenteronline.com/publishing/v2/episodes/'+ episodeId +'/'
    libraryData = {'data':{'attributes':{'published_to_library_at':{{startsAt}}}}}
    addLibary = requests.patch(libraryUrl,auth=HTTPBasicAuth(APP_ID,SECRET),data=libraryData)
    addLibary()

if __name__ == "__main__":
    main()
