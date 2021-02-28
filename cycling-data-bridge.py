import os
import sys
import gspread
import requests
import json
import logging
from stravaio import StravaIO
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch, helpers

__version__ = 0.91

def getSheet():
    '''Pull ride entries from google sheet'''
    logging.info('Starting to pull from google sheets')

    # "checkbox" fields should be converted to an array for ingesting in ES
    checkboxToArray = ['during_ride_food', 'gloves', 'go_powder', 'headneck_cover', 'jacket', 'legs', 'pre-ride_food', 'shirts', 'shoe_extra', 'socks']
    

    # Connect to google
    gc = gspread.service_account()
    logging.info('connected to google api')
    
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

    logging.info('Finished pulling from google sheet')
    return convertedSheet


def getStravaToken(client_id, client_secret, access_code=False):
    # need to have valid access_code from oAuth

    logging.info('Starting to get Strava Token')
    
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
            logging.info(e)
    
        payload['refresh_token'] = tokenData['refresh_token']
        payload['grant_type'] = 'refresh_token'
 
        response = requests.post(
            url = url,
            data = payload
        )
 
    # store token data
    strava_tokens = response.json()
    with open('.strava_tokens.json', 'w') as outfile:
        json.dump(strava_tokens, outfile)

    logging.info('Finished getting Strava token')
    return strava_tokens['access_token']
 
 
    # TODO check for 200

def getIndoorRides(token):

    indoor = []
    client = StravaIO(access_token=token)

    #after = 'Last Month'
    after = 'Last Year'
    activityList = client.get_logged_in_athlete_activities(after=after)
    logging.debug(activityList)

    for activity in activityList:
        activity = activity.to_dict()

        if activity['trainer'] and activity['type'] == 'Ride':
            ride = {'strava_link' : 'https://www.strava.com/activities/%s' % activity['id'] }
            indoor.append(ride)

    return indoor
    

def pullStrava(token, rides, tracksIdx, callLimit):
    '''pull ride info from strava'''

    logging.info('Starting to pull ride info from Strava')

    updatedRides =[]
    tracks = []

    stravaFields = [
        'average_cadence',
        'average_speed', 
        'average_watts',
        'calories',     
        'device_name',
        'distance', 
        'elapsed_time', 
        'elev_high', 
        'elev_low', 
        'gear',
        'kilojoules', 
        'max_speed', 
        'max_watts', 
        'moving_time', 
        'name', 
        'start_date', 
        'start_date_local', 
        'start_latlng', 
        'trainer',
        'timezone', 
        'total_elevation_gain'
    ]
    #TODO ->  Want to include gear.name to get bike name

    client = StravaIO(access_token=token)
    
    apiLoopCount = 0
    for ride in rides:
        apiLoopCount += 1

        # process activity
        rideID = ride['strava_link'].split('/')[-1]
        logging.info('getting activity: %s' % rideID)
        activity = client.get_activity_by_id(rideID)
        activity_dict = activity.to_dict()
        logging.debug(activity_dict)

        # store select fields from Strava
        #ride['strava'] = dict( ((sf, activity_dict[sf] ) for sf in stravaFields) )
        strava = {}
        for sf in stravaFields:
            logging.debug(sf)
            try:
                strava[sf] = activity_dict[sf]
            except KeyError:
                logging.debug(sf)
                pass
        ride['strava'] = strava
        logging.debug(ride)

        try:
            ride['location'] = ride['strava']['start_latlng']
        except KeyError:
            pass

        try:
            ride['strava']['distance_mi'] = round(ride['strava']['distance'] / 1609, 2)
        except KeyError:
            print(ride)
            ride['strava']['distance_mi'] = 0
        
        updatedRides.append(ride)
        logging.debug(updatedRides)


        try:
            if not ride['strava']['trainer']:
                # Process Streams for ride - Indoor rides don't have gps tracks
                logging.info('getting stream: %s' % rideID)
                streams = client.get_activity_streams(id=rideID, athlete_id=None, local=False)
                streams_dict = streams.to_dict()
                
                ride_start = datetime.strptime(activity_dict['start_date'], '%Y-%m-%dT%H:%M:%SZ') # I also do this in addWeather, could potentially just do it once
                for point, value in enumerate(streams_dict['time']):
                    # Create new Track for each point
    
                    # offset point from start of ride
                    point_dt = ride_start + timedelta(seconds=streams_dict['time'][point])
                    new_track = {
                                'strava_link' : ride['strava_link'],
                                '_index' : tracksIndexName,
                                'point_ts' : point_dt
                                }
    
                    # Add all stream metrics to new track dict
                    for key in streams_dict.keys():
                        new_track[key] = streams_dict[key][point]
    
                    tracks.append(new_track)
    
                # Mark the end of the ride
                tracks[-1]['track_end'] = True
        except KeyError:
            pass

        if apiLoopCount >= callLimit :
            logging.info('Ending Strava API calls early after reaching API CAll Limit (%s)' % callLimit)
            break

            
    logging.info('Finsihed pulling rides from Strava')
    logging.debug(updatedRides)
    logging.debug(tracks)
    return updatedRides, tracks


def addWeather(apiKey, rides):
    '''Add weather from OpenWeather (API allows for last 5 days)'''

    logging.info('Starting to pull weather info')
    logging.debug(rides)
    
    weatherRides = []
    for ride in rides:
        try:
            if ride['strava']['trainer'] == True:
                logging.info('skipping weather pull for %s' % ride)
                weatherRides.append(ride)
            else:
                lat, long = ride['strava']['start_latlng']

                dtStart = datetime.strptime(ride['strava']['start_date'], '%Y-%m-%dT%H:%M:%SZ')
                dt = int(dtStart.timestamp())
                hoursSpan = int(ride['strava']['elapsed_time']/60/60) + 1 # lazy way to ensure we get weather for the span of hours ride went across

                oneCall = 'http://api.openweathermap.org/data/2.5/onecall/timemachine?lat=%s&lon=%s&units=imperial&dt=%s&appid=%s' % (lat, long, dt, apiKey)
                logging.info('Calling wather for %s' % oneCall)

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
        except KeyError:
            '''can't process weather info possibly because it is an indoor ride but not labeled as such (trainer)
               or something is up with the weather info, eitherway still include it for upload'''

            weatherRides.append(ride)

    logging.info('Finished pulling weather info')
    logging.debug(weatherRides)
    return weatherRides


def esGetExisting(esConn, index):
    '''Get existing rides in ES'''

    logging.info('Starting to get list of existing rides in ES')

    search = {"size":10000,"query":{"match_all":{}},"fields":["strava_link","timestamp"],"_source":False}
    rides = es.search(index=index, body=search)

    existing = {'ts':[], 'sl':[]}
    for row in rides['hits']['hits']:
        existing['sl'].append(row['fields']['strava_link'][0])

    logging.info('Finished getting existing rides from ES')
    print(existing)
    return existing


def esInsert(indexName, newRides, newTracks):
    '''Insert new rides to ES'''

    logging.info('Starting to insert new rides to ES')
    # TODO convert to bulk client at some point
    logging.info('Indexing rows to index: %s' % indexName)
    for ride in newRides:
        logging.debug(ride)
        res = es.index(index=indexName, body=ride)
        logging.info(res)

    logging.info('Finished inserting rides to ES')

    logging.info('Starting inserting Track Streams to ES')
    # need to 
    # FIX MAPPING FOR TIME here, time and need to create a geo_point
    helpers.bulk(es, newTracks)

    logging.info('Finished inserting Track Streams to ES')

def esConnect(cid, user, passwd):
    '''Connect to Elastic Cloud cluster'''

    logging.info('Starting to create ES Connection')
    es = Elasticsearch(cloud_id=cid, http_auth=(user, passwd))

    logging.info('Finished creating ES Connection')
    return es

def dropExisting(existing, rides, indoorRides):
    '''We only want to work with and insert new rides to ES'''

    logging.info('Starting to drop existing rides from google sheet')
    print('indoor')
    print(indoorRides)

    logging.debug(indoorRides)
    new = []
    ###TODO COmbine these two loops
    for ride in rides:
        if ride['strava_link'] not in existing['sl']:
            logging.info('New ride found: %s' % ride['strava_link'])
            new.append(ride)

    for ride in indoorRides:
        print(ride)
        if ride['strava_link'] not in existing['sl']:
            logging.info('New indoor ride found: %s' % ride['strava_link'])
            new.append(ride)
        
    if not new:
        logging.info('No new strava rides found in google sheet or indoor on Strava')
        #logging.info('No new strava rides found in google sheet')
        logging.info('Exiting')
        sys.exit()

    logging.info('Finished dropping existing rides')
    return new

def createMeta(rides):
    ''' use data from weather but fall back to manual input for other data'''

    logging.info('Starting to create meta weather fields')
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

    logging.info('Finished creating meta weather fields')
    logging.debug(compiledRides)
    return compiledRides


if __name__ == '__main__':
    
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(module)s:%(funcName)s:%(lineno)d:%(message)s', level=logging.INFO)
    logging.info('Starting up')

    # ES info
    es_id = os.getenv('es_id')
    es_user = os.getenv('es_user')
    es_pass = os.getenv('es_pass')
    indexName = 'cycling-report-extended'
    tracksIndexName = 'cycling-tracks'
    #indexName = 'cycling-report-extended-indoor-test'
    #tracksIndexName = 'cycling-tracks-indoor-test'

    # OpenWeather info
    apiKey = os.getenv('apiKey')

    # strava info
    strava_client = os.getenv('stravaClientID')
    strava_secret = os.getenv('stravaClientSecret')
    strava_api_limit = 40

    # Do stuff

    # Get rides for Google Sheet
    sheet = getSheet()

    # get strava token
    token = getStravaToken(strava_client, strava_secret, access_code=False)

    # Get indoor rides for past week
    indoor = getIndoorRides(token)

    # connect to ESS
    es = esConnect(es_id, es_user, es_pass)

    # get existing rides (docs)
    existing = esGetExisting(es, indexName)

    # drop existing rides
    newRides = dropExisting(existing, sheet, indoor)

    # pull strava data for ride
    stravaAdded, stravaTracks = pullStrava(token, newRides, tracksIndexName, strava_api_limit)
    logging.info(stravaAdded)

    # add All the Weather!
    weatherRides = addWeather(apiKey, stravaAdded)

    # create metafields - if/else fields
    processedRides = createMeta(weatherRides)

    # sent new rides to ESS
    esInsert(indexName, processedRides, stravaTracks)



#vim: expandtab tabstop=4
