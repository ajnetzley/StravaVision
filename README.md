This is a repo where I do a deep dive into a variety of my Strava data files, looking into different metrics and creating different visualizations

## Activities Scraping Directions
### Manual JSON Requests through Strava Playground
To manually your activities from a specified timeframe, execute the following steps.

#### 1: Navigate to the Strava Playground Website
Via browser, access the Strava API v3 Playground [here](https://developers.strava.com/playground/)

#### 2: Give Access to your Profile
Select the "Authorize" button on the right side of the screen ![playground](images/playground.png)

Select "activity:read_all" and "Authorize" ![authorize](images/authorize.png)

Confirm authorization from your profile ![authorize_confirm](images/authorize_confirm.png)

#### 3: Execute the API Call

Scroll down in the playground and select "Get /athlete/activities" and click "Try it out" ![athlete_activities](images/athlete_activities.png)

Fill in the parameters desired for the API call ![api-call](images/api-call.png)

Download the API Response and store in the "activities_data" folder ![api-response](images/api-response.png)




