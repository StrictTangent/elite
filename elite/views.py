from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
import json, requests, ijson, csv, time, bs4
from django.contrib.auth.decorators import login_required
from .models import Planet, Price, System
from django.db.models import Q
from .forms import LocationForm

def elite_main(request):

    if request.method == 'POST':

        form = LocationForm(request.POST)
        if form.is_valid():
            systemsURL = 'https://www.edsm.net/api-v1/sphere-systems'

            if (request.POST.get('stationName')): #IF WE ARE LOOKING UP PLANETS
                print('looking up planets')
                results = request.session.get('results')
                listOfSystems = []  # this is the list of systems within the radius

                location = request.POST.get('systemName')
                systemsPARAMS = {'systemName':location,'radius':20}#, 'showId':'showId'}
                response = requests.get(url = systemsURL, params = systemsPARAMS)
                systems = response.json()

                listOfSystems = []
                for system in systems:
                    listOfSystems.append(system)
                listOfSystems.sort(key=lambda x: x['distance'])

                pList = []
                for system in listOfSystems:
                    if System.objects.filter(name=system['name']).exists():
                        starsystem = System.objects.get(name=system['name'])

                        trafficURL = 'https://www.edsm.net/api-system-v1/traffic'
                        trafficPARAMS = {'systemName':system['name']}

                        securityURL = 'https://www.edsm.net/api-v1/system'
                        securityPARAMS = {'systemName':system['name'], 'showInformation':1}

                        response = requests.get(url=trafficURL, params=trafficPARAMS)
                        trafficData = response.json()
                        del response
                        traffic = trafficData['traffic']['week']
                        del trafficData


                        response = requests.get(url=securityURL, params=securityPARAMS)
                        securityData = response.json()
                        del response
                        if securityData['information']:
                            security = securityData['information']['security']
                        else:
                            security = "Unknown"
                        del securityData

                        planets = json.loads(starsystem.planets)
                        for planet in planets:
                            pList.append({'name':planet['name'],
                                'systemName':system['name'],
                                'distanceToArrival':planet['distanceToArrival'],
                                'distance':system['distance'],
                                'traffic':traffic,
                                'security':security})
                    if len(pList) >= 20:
                        break


                stationResults = {'stations':results, 'sellStation':request.POST.get('stationName')}
                return render(request, 'elite/wheretomine.html', {'form':form,'stationResults':stationResults, 'planetResults':pList})

            else:   #IF WE ARE LOOKING UP STATIONS
                RADIUS_MAX = 100 # set the max search radius to 100 lightyears

                location = form.cleaned_data['location']
                radius = form.cleaned_data['radius']
                if radius > RADIUS_MAX:
                    radius = RADIUS_MAX

                #Set parameters and get request from EDSM
                systemsPARAMS = {'systemName':location,'radius':radius}#, 'showId':'showId'}
                response = requests.get(url = systemsURL, params = systemsPARAMS)
                systems = response.json()

                listOfStations = [] # this is the list of planets within the radius

                index = 0
                distances = {}
                for system in systems:  # iterate through every starsystem within the radius
                    distances.update({system['name']:system['distance']})
                    index += 1
                    # build up a Q query
                    if index == 1:
                        query = Q(systemName = system['name'])
                    else:
                        query.add(Q(systemName = system['name']), Q.OR)

                    if index == 990:
                        stations = Price.objects.filter(query)
                        for station in stations:
                            listOfStations.append(station)  # add stations found to the list
                        index = 0
                if index > 0:
                    stations = Price.objects.filter(query)
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
                        distanceTo = listOfStations[i].distance_to_star
                        pad = listOfStations[i].max_landing_pad_size
                        distance = distances[sysName]
                        id = listOfStations[i].station_id



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
                            'distanceToArrival':distanceTo,
                            'distance':distance,
                            'pad':pad,
                            'id':id})

                        sellingStations.sort(key=lambda x: x['price'], reverse=True)    # finally sort the stations by the new price
                finalList = sellingStations[:10]
                for station in finalList:
                    #get updated time
                    res = requests.get('https://eddb.io/station/' + str(station['id']))
                    res.raise_for_status()
                    soup = bs4.BeautifulSoup(res.text, features="html.parser")
                    elements = soup.select('div div div div')
                    next = False
                    updated = "Unknown"
                    for element in elements:
                        if next:
                            updated = element.getText()
                            next = False
                            break
                        if element.getText() == 'Price Update:':
                            next = True
                    station.update({'updated':updated})
                stationResults = {'stations':finalList}
                #results = {'stations':sellingStations[:10], 'planets':listOfPlanets}    # create a dictionary of 'results' to pass to the template which include
                                                                                        # both stations to sell at and planets to mine at
                request.session['results'] = sellingStations[:10]
                return render(request, 'elite/wheretomine.html', {'form':form,'stationResults':stationResults})

    else:
        form = LocationForm()
        return render(request, 'elite/wheretomine.html', {'form':form})

def OLDelite_main(request):

    if request.method == 'POST':

        form = LocationForm(request.POST)
        if form.is_valid():
            systemsURL = 'https://www.edsm.net/api-v1/sphere-systems'

            if (request.POST.get('stationName')): #IF WE ARE LOOKING UP PLANETS
                print('looking up planets')
                results = request.session.get('results')
                listOfPlanets = []  # this is the list of planets within the radius

                location = request.POST.get('systemName')
                systemsPARAMS = {'systemName':location,'radius':30, 'showId':'showId'}
                response = requests.get(url = systemsURL, params = systemsPARAMS)
                systems = response.json()

                index = 0
                distances = {}
                for system in systems:  # iterate through every starsystem within the radius
                    index += 1
                    distances.update({system['name']:system['distance']})
                    # build up a Q query
                    if index == 1:
                        query = Q(systemName = system['name'])
                    else:
                        query.add(Q(systemName = system['name']), Q.OR)

                    if index == 990:
                        bodies = Planet.objects.filter(query)
                        for body in bodies:
                            listOfPlanets.append(body)      # add planets found to the list
                        index = 0
                if index > 0:
                    bodies = Planet.objects.filter(query)
                    for body in bodies:
                        listOfPlanets.append(body)          # add remaining planets found to the list

                #repack planets to include distance
                pList = []
                for planet in listOfPlanets:
                    pList.append({'name':planet.name,
                    'systemName':planet.systemName,
                    'distanceToArrival':planet.distanceToArrival,
                    'distance':distances[planet.systemName]})

                stationResults = {'stations':results, 'sellStation':request.POST.get('stationName')}
                return render(request, 'elite/wheretomine.html', {'form':form,'stationResults':stationResults, 'planetResults':pList})

            else:   #IF WE ARE LOOKING UP STATIONS
                RADIUS_MAX = 50 # set the search radius to 30 lightyears

                location = form.cleaned_data['location']
                radius = form.cleaned_data['radius']
                if radius > RADIUS_MAX:
                    radius = RADIUS_MAX

                #Set parameters and get request from EDSM
                systemsPARAMS = {'systemName':location,'radius':radius, 'showId':'showId'}
                response = requests.get(url = systemsURL, params = systemsPARAMS)
                systems = response.json()

                listOfStations = [] # this is the list of planets within the radius

                index = 0
                distances = {}
                for system in systems:  # iterate through every starsystem within the radius
                    distances.update({system['name']:system['distance']})
                    index += 1
                    # build up a Q query
                    if index == 1:
                        query = Q(systemName = system['name'])
                    else:
                        query.add(Q(systemName = system['name']), Q.OR)

                    if index == 990:
                        #bodies = Planet.objects.filter(query)
                        stations = Price.objects.filter(query)
                        #for body in bodies:
                        #    listOfPlanets.append(body)      # add planets found to the list
                        for station in stations:
                            listOfStations.append(station)  # add stations found to the list
                        index = 0
                if index > 0:
                    #bodies = Planet.objects.filter(query)
                    stations = Price.objects.filter(query)
                    #for body in bodies:
                    #    listOfPlanets.append(body)          # add remaining planets found to the list
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
                        distanceTo = listOfStations[i].distance_to_star
                        pad = listOfStations[i].max_landing_pad_size
                        distance = distances[sysName]


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
                            'distanceToArrival':distanceTo,
                            'distance':distance,
                            'pad':pad})

                        sellingStations.sort(key=lambda x: x['price'], reverse=True)    # finally sort the stations by the new price

                stationResults = {'stations':sellingStations[:10]}
                #results = {'stations':sellingStations[:10], 'planets':listOfPlanets}    # create a dictionary of 'results' to pass to the template which include
                                                                                        # both stations to sell at and planets to mine at
                request.session['results'] = sellingStations[:10]
                return render(request, 'elite/wheretomine.html', {'form':form,'stationResults':stationResults})

    else:
        form = LocationForm()
        return render(request, 'elite/wheretomine.html', {'form':form})
