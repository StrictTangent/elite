from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
import json, requests, ijson, csv, time
from django.contrib.auth.decorators import login_required
from .models import Planet, Price
from django.db.models import Q
from .forms import LocationForm

def elite_main(request):

    if request.method == 'POST':
        form = LocationForm(request.POST)

        if form.is_valid():

            RADIUS = 30 # set the search radius to 30 lightyears

            location = form.cleaned_data['location']

            #Set parameters and get request from EDSM
            systemsURL = 'https://www.edsm.net/api-v1/sphere-systems'
            systemsPARAMS = {'systemName':location,'radius':RADIUS, 'showId':'showId'}
            response = requests.get(url = systemsURL, params = systemsPARAMS)
            systems = response.json()

            listOfPlanets = []  # this is the list of planets within the radius
            listOfStations = [] # this is the list of planets within the radius

            index = 0
            for system in systems:  # iterate through every starsystem within the radius
                index += 1

                # build up a Q query
                if index == 1:
                    query = Q(systemName = system['name'])
                else:
                    query.add(Q(systemName = system['name']), Q.OR)

                if index == 990:
                    bodies = Planet.objects.filter(query)
                    stations = Price.objects.filter(query)
                    for body in bodies:
                        listOfPlanets.append(body)      # add planets found to the list
                    for station in stations:
                        listOfStations.append(station)  # add stations found to the list
                    index = 0
            if index > 0:
                bodies = Planet.objects.filter(query)
                stations = Price.objects.filter(query)
                for body in bodies:
                    listOfPlanets.append(body)          # add remaining planets found to the list
                for station in stations:
                    listOfStations.append(station)      # add remaining statinos found to the list

            listOfStations.sort(key=lambda x: x.sell_price, reverse=True)   # sort the list of stations by the sell price

            sellingStations = []        # this is the list of station information (dictionaries) we will pass to the template
            if len(listOfStations) > 0: # so long as there ARE stations...

                URL = 'https://www.edsm.net/api-system-v1/stations/market'
                stationRange = 20

                if len(listOfStations) < 20:
                    stationRange = len(listOfStations)
                for i in range(stationRange):               # iterate through top stations (up to max of 20)
                    name = listOfStations[i].station_name
                    sysName = listOfStations[i].systemName
                    price = listOfStations[i].sell_price
                    distance = listOfStations[i].distance_to_star
                    pad = listOfStations[i].max_landing_pad_size


                    ## NOW UPDATE TO NEWEST PRICES WITHIN THE TOP 20 STATIONS ##
                    PARAMS = {'systemName':sysName, 'stationName':name}
                    response = requests.get(url=URL, params=PARAMS)
                    data = response.json()
                    commodities = data['commodities']
                    for commodity in commodities:
                        if commodity['id'] == 'opal':
                            price = commodity['sellPrice']  #update the price to be added to the dictionary
                            if price != listOfStations[i].sell_price: #if the price has changed...
                                Price.objects.filter(station_id=listOfStations[i].station_id).update(sell_price=price) #update price in database
                    #create and append dictionary to list of selling stations
                    sellingStations.append({'name':name,
                        'systemName':sysName,
                        'price':price,
                        'distanceToArrival':distance,
                        'pad':pad})


                    sellingStations.sort(key=lambda x: x['price'], reverse=True)    # finally sort the stations by the new price


            results = {'stations':sellingStations[:10], 'planets':listOfPlanets}    # create a dictionary of 'results' to pass to the template which include
                                                                                    # both stations to sell at and planets to mine at
            return render(request, 'elite/wheretomine.html', {'form':form,'results':results})

    else:
        form = LocationForm()

    return render(request, 'elite/wheretomine.html', {'form':form})
