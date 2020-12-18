# Cycling Data Bridge
The goal of this project is to centralize objective and subjective cycling data.
1. Nutrition, clothing, comfort feel, etc. are entered in a Google Form (subjective)
2. Python script pulls that data as well as Strava and. Weather measurements (objective)
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

### Python Libraries used
- TODO list of main libraries used
- [pip freeze output](https://raw.githubusercontent.com/jeffvestal/cycling-data-bridge/main/py_freeze.txt?token=AMWFQYHCRJMNSOZN5O2WU6K73TIGW "pip freeze output")

### Environment Variables to configure
- TODO a bunch



