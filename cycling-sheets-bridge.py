import os
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

        ## Create a new field "startDateTime" based on "date" and "start_time" fields
        #rideSDT = '%s %s' % (rowLower['date'], rowLower['start_time'])
        #rideSDT = central.localize(datetime.strptime(rideSDT, '%m/%d/%Y %I:%M:%S %p'))
        ## Convert to UTC
        #utcSDT = datetime.utcfromtimestamp(rideSDT.timestamp())
        #rowLower['startDateTime'] = utcSDT

        # 'timestamp' is the column name created by the Google form automatically generated when the form is submitted / entered into Sheets
       # convertedSheet[rowLower['timestamp']] = rowLower
        convertedSheet.append(rowLower)


#    pprint(convertedSheet)
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
            with open('strava_tokens.json') as file:
                tokenData = json.load(file)
        except Exception as e:
            print(e)
    
        payload['refresh_token'] = tokenData['refresh_token']
        payload['grant_type'] = 'refresh_token'
 
        print(payload)
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
        print()
        print()
        print(ride)
        rideID = ride['strava_link'].split('/')[-1]
        print()
        print(token)
        print(rideID)
        activity = client.get_activity_by_id(rideID)
        activity_dict = activity.to_dict()

        for sf in stravaFields:
            print(activity_dict)
            #rides[ride]['strava'] = dict( ((sf, activity_dict[sf] ) for sf in stravaFields) )
            ride['strava'] = dict( ((sf, activity_dict[sf] ) for sf in stravaFields) )
        
        updatedRides.append(ride)
            
    return updatedRides


def addWeather(apiKey, rides):
    '''Add weather from OpenWeather (API allows for last 5 days)'''
    print('starting addWeather')
    pprint(rides)
    
    for ride in rides:
        dt = ride['dt'] #check the key name
    oneCall = 'http://api.openweathermap.org/data/2.5/onecall/timemachine?lat=%s&lon=%s&units=imperial&dt=%s&appid=%s' % (lat, long, dt, apiKey)

    response = requests.get(oneCall)
    weather = json.loads(response.text)



def esGetExisting(esConn, index):
    '''Get existing rides in ES'''
    rides = es.search(index=index, body={"query": {"match_all": {}}})

    existing = (row['_source']['startDateTime'] for row in rides['hits']['hits'])
    return existing


def esInsert(indexName, newRides):
    '''Insert new rides to ES'''
    
#    # RIght not I'm just deleting the index and reindexing the sheet.
#    # maybe at some point just index the new rows
#    print('Deleting existing index %s' % indexName)
#    es.indices.delete(index=indexName)

    # TODO convert to bulk client at some point
    print('Indexing rows to index: %s' % indexName)
    for k,v in sheet.items():
        print(body)
    for ride in newRides:
        res = es.index(index=indexName, body=ride)

def esConnect(cid, user, passwd):
    '''Connect to Elastic Cloud cluster'''

    es = Elasticsearch(cloud_id=cid, http_auth=(user, passwd))
    return es

def dropExisting(existing, rides):
    #TODO delete existing docs from sheet
    # use strava.start_date

    return rides

if __name__ == '__main__':
    
    # Set variables
    es_id = os.getenv('es_id')
    es_user = os.getenv('es_user')
    es_pass = os.getenv('es_pass')
    #indexName = 'cycling-report'
    indexName = 'test_cycling-report'

    # OpenWeather info
    apiKey = os.getenv('apiKey')
    lat = os.getenv('lat')
    long = os.getenv('long')

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
    processedRides = addWeather(apiKey, lat, long, stravaAdded)

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
