# Cycling Data Bridge
The goal of this project is to centralize objective and subjective cycling data.
1. Nutrition, clothing, comfort feel, etc. are entered in a Google Form (subjective)
2. Python script pulls that data as well as Strava (metrics and gps tracks) and Weather measurements (objective)
3. Sends them to an Elasticsearch cluster for visulization and reference.

[![Data Flow Diagram](https://github.com/jeffvestal/cycling-data-bridge/raw/main/cycling%20report%20Diagram.png "Data Flow Diagram")](https://github.com/jeffvestal/cycling-report/raw/main/cycling%20report%20Diagram.png "Data Flow Diagram")

### Requirements
- Google Form to collect post ride report data
-- This can also just be directly entered into a Google Sheet
-- API access to call Google Drive
--TODO: add api info
- Strava Account
-- Upload / enter ride info 
-- ride url should be entered in google sheet to auto pull that info
-- TODO add Strava API info
- OpenWeather API account
-- A free account can pull data from previous 5 days
-- TODO add weather API info
- Elasticsearch cluster
-- cloud.elastic.co makes it easy to get up and running but any cluster will work
- Host to run python
-- TODO link to pytohn libraries used
- A bike ride

### Python Libraries used (non-standard)
[pip freeze output](https://raw.githubusercontent.com/jeffvestal/cycling-data-bridge/main/py_freeze.txt?token=AMWFQYHCRJMNSOZN5O2WU6K73TIGW "pip freeze output")
- [elasticsearch](https://pypi.org/project/elasticsearch7/ "elasticsearch")
- [gspread](https://pypi.org/project/gspread/ "gspread")
- [stravaio](https://pypi.org/project/stravaio/ "stravaio")


### Environment Variables to configure
- **es_id**= "elastic cloud_id"
- **es_user**="elasticsearch user"
- **es_pass**="es_user password"
- **apiKey**="openWeather API key"
- **stravaClientID**="Strava API App ID"
- **stravaClientSecret**="Strava API App Client Secret"


----
# Documentation

The code provided is a Python script that helps a cyclist extract, process, and analyze cycling data from multiple sources including Google Sheets, Strava, and OpenWeatherMap. 

## Main Libraries Used

- `gspread`: To interact with Google Sheets.
- `requests`: To make HTTP requests.
- `json`: To handle JSON data.
- `logging`: To maintain a log of all operations.
- `stravaio`: To interact with the Strava API.
- `elasticsearch`: To interact with Elasticsearch service.
- `datetime`: To work with dates and times.

## Functions

1. `getSheet()`: This function connects to Google Sheets using the `gspread` library, specifically to a sheet named 'Cycling Clothes for Weather'. It fetches all records from this sheet, processes them to fit with Elasticsearch format, and returns a list of these records. The function is used to fetch the cyclist's ride data stored in Google Sheets.

2. `getStravaToken(client_id, client_secret, access_code=False)`: This function retrieves an access token from the Strava API using the provided `client_id` and `client_secret`. It manages both initial and subsequent token refresh processes. This function is necessary to authorize requests made to the Strava API.

3. `getIndoorRides(token)`: This function fetches the indoor ride activities of a cyclist from Strava using the provided access `token`. It returns a list of ride details where each ride detail is a dictionary containing a Strava link for the specific activity.

4. `pullStrava(token, rides, tracksIdx, callLimit)`: This function fetches detailed ride information from Strava and also pulls associated GPS tracks for outdoor rides. The function takes as input a Strava access `token`, a list of `rides` (obtained from the Google Sheet or indoor rides from Strava), a `tracksIdx` which is the name of the Elasticsearch index to store the GPS tracks, and a `callLimit` to limit the number of API calls to Strava.

5. `addWeather(apiKey, rides)`: This function uses the OpenWeatherMap API to fetch weather data for the duration of each outdoor ride. It takes the OpenWeatherMap `apiKey` and a list of `rides` as input.

6. `esGetExisting(esConn, index)`: This function retrieves existing ride data from an Elasticsearch index. This is used to avoid duplicating ride data.

7. `esInsert(indexName, newRides, newTracks)`: This function inserts new ride data and associated GPS tracks into Elasticsearch.

8. `esConnect(cid, user, passwd)`: This function creates a connection to Elasticsearch using the provided cloud `cid`, `user`, and `passwd`.

9. `dropExisting(existing, rides, indoorRides)`: This function removes any rides from the list of `rides` and `indoorRides` that already exist in Elasticsearch (as defined by the `existing` list).

10. `createMeta(rides)`: This function extracts and consolidates weather data from the ride data.

In the script's main section, it retrieves necessary credentials from the environment variables, fetches data from Google Sheets and Strava, processes the data, fetches weather information for the rides, and stores the processed data in Elasticsearch.

To use this script as a cyclist, you need to:

1. Have a Google Sheet named 'Cycling Clothes for Weather' with your ride data.
2. Set up a Strava account and grant access to this application.
3. Set up an OpenWeatherMap account to get an API key for fetching weather data.
4. Set up an Elasticsearch service to store and process your ride data.

Then,

 in current output. Click to display more.




