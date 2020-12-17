import os
import sys
import gspread
import requests
import json
from stravaio import StravaIO
from pprint import pprint
from datetime import datetime
from pytz import timezone
from elasticsearch import Elasticsearch


def getSheet():
    '''Pull ride entries from google sheet'''
    print('Starting gSheet pull')

    # Set timezone
    central = timezone('US/Central')

    # "checkbox" fields should be converted to an array for ingesting in ES
    checkboxToArray = ['during_ride_food', 'gloves', 'go_powder', 'headneck_cover', 'jacket', 'legs', 'pre-ride_food', 'shirts', 'shoe_extra', 'socks']
    

    # Connect to google
    print('Connecting to gSheet Service')
    gc = gspread.service_account()
    
    # Open and load spreadsheet
    sh = gc.open('Cycling Clothes for Weather').sheet1
    l = sh.get_all_records()

    convertedSheet = []
    for row in l:
        # Replace chars that would make ES a little less fun
        rowLower = {}
        for k,v in row.items():
            if v == '':
                # No need to index empty cells
                continue

            # make fields names friendlier for es/lucene
            k = k.lower().replace('/', '').replace('  ', '').replace('(', '').replace(')', '').strip().replace(' ', '_')

            # convert multiple results to array
            if k in checkboxToArray:
                v = v.split(',')

            rowLower[k] = v

        convertedSheet.append(rowLower)

    return convertedSheet


def getStravaToken(client_id, client_secret, access_code=False):
    # need to have valid access_code from oAuth
    
    url = 'https://www.strava.com/oauth/token'
    payload = {
        'client_id': client_id,
        'client_secret': client_secret
     }
 
    if access_code:
       '''
         You have to manually (for now) call oAuth to get the access token
         http://www.strava.com/oauth/authorize?client_id=<client_id>&response_type=code&redirect_uri=http://localhost/exchange_token&approval_prompt=force&scope=profile:read_all,activity:read_all
     '''
        #assume we need to pull a new initial token
       payload['code'] = access_code
       payload['grant_type'] = 'authorization_code'
 
       response = requests.post(
           url = url,
           data = payload
       )
 
    #    # store token data
    #    strava_tokens = response.json()
    #    with open('.strava_tokens.json', 'w') as outfile:
    #        json.dump(strava_tokens, outfile)
 
    else:
        try:
            with open('.strava_tokens.json') as file:
                tokenData = json.load(file)
        except Exception as e:
            print(e)
    
        payload['refresh_token'] = tokenData['refresh_token']
        payload['grant_type'] = 'refresh_token'
 
        #print(payload)
        response = requests.post(
            url = url,
            data = payload
        )
 
    # store token data
    strava_tokens = response.json()
    with open('.strava_tokens.json', 'w') as outfile:
        json.dump(strava_tokens, outfile)

    return strava_tokens['access_token']
 
 
    # TODO check for 200


def pullStrava(token, rides):
    '''pull ride info from strava'''

    updatedRides =[]
    stravaFields = [
        'average_speed', 
        'average_watts',
        'calories',     
        'distance', 
        'elapsed_time', 
        'elev_high', 
        'elev_low', 
        'kilojoules', 
        'max_speed', 
        'max_watts', 
        'moving_time', 
        'name', 
        'start_date', 
        'start_date_local', 
        'start_latlng', 
        'timezone', 
        'total_elevation_gain'
    ]

    client = StravaIO(access_token=token)
    
    for ride in rides:
        rideID = ride['strava_link'].split('/')[-1]
        activity = client.get_activity_by_id(rideID)
        activity_dict = activity.to_dict()

        for sf in stravaFields:
            # store select fields from Strava
            # create geopoint field from start_latlng
            ride['strava'] = dict( ((sf, activity_dict[sf] ) for sf in stravaFields) )
            ride['location'] = ride['strava']['start_latlng']
            ride['strava']['distance_mi'] = round(ride['strava']['distance'] / 1609, 2)
        
        updatedRides.append(ride)
            
    return updatedRides


def addWeather(apiKey, rides):
    '''Add weather from OpenWeather (API allows for last 5 days)'''

    print('starting addWeather')
    
    weatherRides = []
    for ride in rides:
        lat, long = ride['strava']['start_latlng']

        dtStart = datetime.strptime(ride['strava']['start_date'], '%Y-%m-%dT%H:%M:%SZ')
        dt = int(dtStart.timestamp())
        dtStartHour = int(dtStart.replace(microsecond=0, second=0, minute=0).timestamp())
        hoursSpan = int(ride['strava']['elapsed_time']/60/60) + 1 # lazy way to ensure we get weather for the span of hours ride went across

        oneCall = 'http://api.openweathermap.org/data/2.5/onecall/timemachine?lat=%s&lon=%s&units=imperial&dt=%s&appid=%s' % (lat, long, dt, apiKey)
        print(oneCall)

        response = requests.get(oneCall)
        weather = json.loads(response.text)
        try:
            weatherSpans = weather['hourly'][dtStart.hour : dtStart.hour + hoursSpan + 1]
            weatherStart = weatherSpans[0]

            ride['weather'] = {
                                'weatherSpans' : weatherSpans, 
                                'weatherStart' : weatherStart,
                                'location' : {'lat' : weather['lat'], 'lon' : weather['lon'] },
                                'timezone' : weather['timezone'],
                                'timezone_offset' : weather['timezone_offset']
                              }
        except KeyError:
            ride['weather'] = {'missingReason' : weather}
        weatherRides.append(ride)

    return weatherRides


def esGetExisting(esConn, index):
    '''Get existing rides in ES'''

    print('starting esGetExisting')

    search = {"size":10000,"query":{"match_all":{}},"fields":["strava_link","timestamp"],"_source":False}
    rides = es.search(index=index, body=search)

    existing = {'ts':[], 'sl':[]}
    for row in rides['hits']['hits']:
        existing['ts'].append(row['fields']['timestamp'][0])
        existing['sl'].append(row['fields']['strava_link'][0])

    return existing


def esInsert(indexName, newRides):
    '''Insert new rides to ES'''
    print('Inserting Rides into ES')

    # TODO convert to bulk client at some point
    print('Indexing rows to index: %s' % indexName)
    for ride in newRides:
#        print(ride)
        res = es.index(index=indexName, body=ride)

def esConnect(cid, user, passwd):
    '''Connect to Elastic Cloud cluster'''

    es = Elasticsearch(cloud_id=cid, http_auth=(user, passwd))
    return es

def dropExisting(existing, rides):

    new = []
    for ride in rides:
        if ride['strava_link'] not in existing['sl']:
            print('new ride found: %s' % ride['strava_link'])
            new.append(ride)
        
    if not new:
        print ('no new strava rides found. Exiting')
        sys.exit()
    return rides

def createMeta(rides):
    ''' use data from weather but fall back to manual input for other data'''

    print('starting createMeta')
    weatherFallback = ( ('temp', 'starting_temp'), ('feels_like', 'real_feel'), ('wind_speed', 'wind_speed') )
    compiledRides = []

    for ride in rides:
        meta = {}
        for weatherField, fallback in weatherFallback:
            try:
                meta[weatherField] = ride['weather']['weatherStart'][weatherField]
            except KeyError:
                try:
                    meta[weatherField] = ride[fallback]
                except:
                    pass
        ride['meta'] = meta
        compiledRides.append(ride)

    return compiledRides


if __name__ == '__main__':
    
    # ES info
    es_id = os.getenv('es_id')
    es_user = os.getenv('es_user')
    es_pass = os.getenv('es_pass')
    indexName = 'cycling-report-extended'

    # OpenWeather info
    apiKey = os.getenv('apiKey')

    # strava info
    strava_client = os.getenv('stravaClientID')
    strava_secret = os.getenv('stravaClientSecret')


    # Get rides for Google Sheet
    sheet = getSheet()

    # connect to ESS
    es = esConnect(es_id, es_user, es_pass)

    # get existing rides (docs)
    existing = esGetExisting(es, indexName)

    # drop existing rides
    newRides = dropExisting(existing, sheet)

    # get strava token
    token = getStravaToken(strava_client, strava_secret, access_code=False)

    # pull strava data for ride
    stravaAdded = pullStrava(token, newRides)

    # add All the Weather!
    weatherRides = addWeather(apiKey, stravaAdded)

    # create metafields - if/else fields
    processedRides = createMeta(weatherRides)

    # sent new rides to ESS
    esInsert(indexName, processedRides)


'''
- get rows from gsheet
- format data
- get "key" of ride from ES
- drop rows for existing rides
- get ride info from strava
- get weather for new (remaining rides)
- upload to ES

TODO
- pull location from Strava and get lat,long?
- add ability to update rides from sheet (or just make the update delete form ESS, but then missing some data)
- 
'''




# vim: expandtab tabstop=4
