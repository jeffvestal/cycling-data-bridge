import os
import gspread
import requests
import json
from pprint import pprint
from datetime import datetime
from pytz import timezone
from elasticsearch import Elasticsearch


def excel_sheet():
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
    
    convertedSheet = {}
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

        # Create a new field "startDateTime" based on "date" and "start_time" fields
        rideSDT = '%s %s' % (rowLower['date'], rowLower['start_time'])
        rideSDT = central.localize(datetime.strptime(rideSDT, '%m/%d/%Y %I:%M:%S %p'))
        # Convert to UTC
        utcSDT = datetime.utcfromtimestamp(rideSDT.timestamp())
        rowLower['startDateTime'] = utcSDT

        # 'timestamp' is the column name created by the Google form automatically generated when the form is submitted / entered into Sheets
        convertedSheet[rowLower['timestamp']] = rowLower



#    pprint(convertedSheet)
    return convertedSheet

def addWeather(apiKey, lat, long, rides):
    '''Add weather from OpenWeather (API allows for last 5 days)'''

    
    for ride in rides
        dt = ride['dt'] #check the key name
    oneCall = 'http://api.openweathermap.org/data/2.5/onecall/timemachine?lat=%s&lon=%s&units=imperial&dt=%s&appid=%s' % (lat, long, dt, apiKey)

    response = requests.get(oneCall)
    weather = json.loads(response.text)



def esGetExisting(esConn, index):
    '''Get existing rides in ES'''
    es.search(index=index, , body={"query": {"match_all": {}}})

    existing = (row['_source']['startDateTime'] for row in rides['hits']['hits'])
    return existing






def esInsert(indexName, sheet):
    '''Insert new rides to ES'''
    
#    # RIght not I'm just deleting the index and reindexing the sheet.
#    # maybe at some point just index the new rows
#    print('Deleting existing index %s' % indexName)
#    es.indices.delete(index=indexName)

    # TODO convert to bulk client at some point
    print('Indexing rows to index: %s' % indexName)
    for k,v in sheet.items():
        res = es.index(index=indexName, body=v)

def esConnect(cid, user, passwd)
    '''Connect to Elastic Cloud cluster'''

    es = Elasticsearch(cloud_id=cid, http_auth=(user, passwd))
    return es

if __name__ == '__main__':
    
    # Set variables
    es_id = os.getenv('es_id')
    es_user = os.getenv('es_user')
    es_pass = os.getenv('es_pass')
    indexName = 'cycling-report'

    # OpenWeather info
    apiKey = os.getenv('apiKey')
    lat = os.getenv('lat')
    long = os.getenv('long')


    # Get rides for Google Sheet
    sheet = excel_sheet()

    # connect to ESS
    es = esConnect(es_id, es_user, es_pass)

    # get existing rides (docs)
    existing = esGetExisting(es, indexName)

    # add All the Weather!
    processedRides = addWeather(apiKey, lat, long, existing)

    # sent new rides to ESS
    esInsert(indexName, processedRides)


'''
- get rows from gsheet
- format data
- get "key" of ride from ES
- drop rows for existing rides
- get weather for new (remaining rides)
- upload to ES

TODO
- pull location from Strava and get lat,long?
- add ability to update rides from sheet (or just make the update delete form ESS, but then missing some data)
- 
'''




# vim: expandtab tabstop=4
