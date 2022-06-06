#imports
import requests
import os
from decouple import config
from datetime import date
#define main function

APP_ID = config.App_ID
SECRET = config.Secret
auth = {'application_id':APP_ID,'secret':SECRET}

def main():
    url = 'https://api.planningcenteronline.com/publishing/v2/channels/3708/episodes'
    today = date.today()
    serviceDate = today.strftime('%B %d, %Y')
    payload= {'application_id':APP_ID,'secret':SECRET, 'data':{'attributes':{'title':'Sunday, ' + serviceDate}}}
    headers = {}
    res = requests.post(url,data=payload).json()
    episodeId = res.id
    startsAt = today.strftime('%d/%m/%Y')
    startsAt = startsAt + 'T13:45:00+00:00'
    youtubeEmbed = {'application_id':APP_ID,'secret':SECRET,'data':{'attributes':{'starts_at':startsAt,'video_embed_code':'<iframe width=\'560\' height=\'315\' src=\'https://www.youtube.com/embed/live_stream?autoplay=1&amp;channel=UCryZmERAkR6-fktliKiCGNA&amp;playsinline=1\' frameborder=\'0\' allow=\'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture\' allowfullscreen></iframe>'}}}
    youtubeUrl = 'https://api.planningcenteronline.com/publishing/v2/episodes/' + episodeId + '/episode_times'
    getepres = requests.get(youtubeUrl,data=youtubeEmbed)
    getepres()
    libraryUrl = 'https://api.planningcenteronline.com/publishing/v2/episodes/'+ episodeId +'/'
    libraryData = {'application_id':APP_ID,'secret':SECRET,'data':{'attributes':{'published_to_library_at':{{startsAt}}}}}
    addLibary = requests.patch(libraryUrl,libraryData)
    addLibary()

if __name__ == "__main__":
    main()
