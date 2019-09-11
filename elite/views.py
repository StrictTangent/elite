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
            location = form.cleaned_data['location']

            systemsURL = 'https://www.edsm.net/api-v1/sphere-systems'

            systemsPARAMS = {'systemName':location,'radius':30, 'showId':'showId'}
            response = requests.get(url = systemsURL, params = systemsPARAMS)
            systems = response.json()

            print('got json')

            listOfPlanets = []
            listOfStations = []
            print(str(len(systems)) + " systems...")

            index = 0
            for system in systems:
                index += 1
                print(index)
                if index == 1:
                    query = Q(systemName = system['name'])
                else:
                    query.add(Q(systemName = system['name']), Q.OR)

                if index == 990:
                    bodies = Planet.objects.filter(query)
                    stations = Price.objects.filter(query)
                    for body in bodies:
                        listOfPlanets.append(body)
                    for station in stations:
                        listOfStations.append(station)
                    index = 0
            if index > 0:
                bodies = Planet.objects.filter(query)
                stations = Price.objects.filter(query)
                for body in bodies:
                    listOfPlanets.append(body)
                for station in stations:
                    listOfStations.append(station)

            listOfStations.sort(key=lambda x: x.sell_price, reverse=True)

            print(listOfPlanets)

            miningPlanets = []
            for p in listOfPlanets:
                miningPlanets.append("SYSTEM: " + p.systemName
                    + "\tBODY: " + p.name
                    + "\tARRIVAL(ls): " + str(p.distanceToArrival))



            sellingStations = []
            if len(listOfStations) > 0:
                for i in range(10):
                    name = listOfStations[i].station_name
                    sysName = listOfStations[i].systemName
                    price = listOfStations[i].sell_price
                    distance = listOfStations[i].distance_to_star
                    pad = listOfStations[i].max_landing_pad_size

                    sellingStations.append({'name':name,
                        'systemName':sysName,
                        'price':price,
                        'distanceToArrival':distance,
                        'pad':pad})

                    print(listOfStations[i].station_name + " - " + "COST: " + str(listOfStations[i].sell_price))

            results = {'stations':sellingStations, 'planets':listOfPlanets}

            return render(request, 'elite/wheretomine.html', {'form':form,'results':results})

    else:
        form = LocationForm()

    return render(request, 'elite/wheretomine.html', {'form':form})

    #return HttpResponse('done')



@login_required()
def load_database(request):

    with open('json/databasedump.json', 'rb') as input_file:
        entries = ijson.items(input_file, 'item')

        planetsToAdd = []
        pIndex = 0
        pTotal = 0
        stationsToAdd = []
        sIndex = 0
        sTotal = 0

        for entry in entries:
            if entry['model'] == 'elite.planet':
                fields = entry['fields']
                planetToAdd = Planet(name = fields['name'],
                    distanceToArrival = fields['distanceToArrival'],
                    systemName = fields['systemName'])
                planetsToAdd.append(planetToAdd)
                pIndex += 1
                pTotal += 1

                if pIndex == 999:
                    Planet.objects.bulk_create(planetsToAdd)
                    print("Added Batch of: " + str(pIndex))
                    print("Total: " + str(pTotal)) + " Planets")
                    planetsToAdd = []
                    pIndex = 0

            elif entry['model'] == 'elite.Price':
                fields = entry['fields']
                stationToAdd = Price(system_id=fields['system_id'],
                    station_id=fields['station_id'],
                    systemName=fields['systemName'],
                    station_name=fields['station_name'],
                    sell_price=fields['sell_price'],
                    max_landing_pad_size=fields['max_landing_pad_size'],
                    distance_to_star=fields['distance_to_star'])
                stationsToAdd.append(stationToAdd)
                sIndex += 1
                sTotal += 1

                if sIndex == 999:
                    Price.objects.bulk_create(stationsToAdd)
                    print("Added Batch of: " + str(sIndex))
                    print("Total: " + str(sTotal)) + " Stations")
                    stationsToAdd = []
                    sIndex = 0

        if pIndex > 0:
            Planet.objects.bulk_create(planetsToAdd)
            print("Added Batch of: " + str(pIndex))
            print("Total: " + str(pTotal)) + " Planets")

        if sIndex > 0:
            Price.objects.bulk_create(stationsToAdd)
            print("Added Batch of: " + str(sIndex) + " Stations")
            print("Total: " + str(sTotal)) + " Stations")

    return HttpResponse('done')






@login_required()
def import_planets(request):
    theFile = 'json/icybodies.json'

    with open(theFile, 'rb') as input_file:
        data = json.load(input_file)
        planets = data['bodies']

        index = 0
        planetsToAdd = []
        for planet in planets:
            planetToAdd = Planet(name = planet['name'], distanceToArrival = planet['distanceToArrival'], systemName = planet['systemName'])
            planetsToAdd.append(planetToAdd)
            index += 1
            if index == 999:
                Planet.objects.bulk_create(planetsToAdd)
                planetsToAdd = []
                index = 0
        if index > 0: #if there are left over planets...
            Planet.objects.bulk_create(planetsToAdd)
    return HttpResponse('done')



@login_required()
def update_planets(request):

    DOWNLOAD = True

    if DOWNLOAD:
        URL = "https://www.edsm.net/dump/bodies7days.json"
        response = requests.get(URL, stream=True)

        with open('json/updatedPlanets.json', 'wb') as handle:
            for block in response.iter_content(1024):
                handle.write(block)

    with open('json/updatedPlanets.json', 'rb') as input_file:
        bodies = ijson.items(input_file, 'item')
        added = 0
        deleted = 0

        index = 0
        planetsToAdd = []

        newPlanets = set()
        existingPlanets = set()
        #names = Planet.objects.values_list('name', flat=True)
        existingPlanets.update(Planet.objects.values_list('name', flat=True))
        for body in bodies:
            if body['type'] == 'Planet':
                foundIcy = False
                if 'rings' in body:
                    for ring in body['rings']:
                        if ring['type'] == "Icy":
                            foundIcy = True
                    if foundIcy:
                        if body['reserveLevel'] == 'Pristine':
                            newPlanets.add(body['name'])
                        else:
                            print('found ICY + NOT PRISTINE')
                            if Planet.objects.filter(name=body['name']).exists():
                                database.get(name=body['name']).delete()
                                print("Deleted Planet: " + body['name'])
                                deleted += 1

        namesToAdd = newPlanets - existingPlanets
        B = newPlanets & existingPlanets
        print("BRAND NEW:")
        print(len(namesToAdd))
        print("WOULD BE DUPLICATES:")
        print(len(B))

        index = 0

        with open('json/updatedPlanets.json', 'rb') as input_file2:
            bodies = ijson.items(input_file2, 'item')
            for body in bodies:
                if body['name'] in namesToAdd:
                    planetToAdd = Planet(name = body['name'],
                        distanceToArrival = body['distanceToArrival'],
                        systemName = body['systemName'])
                    planetsToAdd.append(planetToAdd)
                    added += 1
                    index += 1
                    if index == 999:
                        Planet.objects.bulk_create(planetsToAdd)
                        print("Added Batch of: " + str(index))
                        planetsToAdd = []
                        index = 0
            if index > 0: #if there are left over planets...
                Planet.objects.bulk_create(planetsToAdd)
                print("Added Batch of: " + str(index))

            print("BRAND NEW:")
            print(len(namesToAdd))
            print("WOULD BE DUPLICATES:")
            print(len(B))

            print("DONE")
            print("Added: " + str(added))
            print("Deleted: " + str(deleted))
    return HttpResponse('done')


@login_required()
def import_prices(request):

    void_opals = '350'

    stations = []

    DOWNLOAD = False

    if DOWNLOAD:
        URL = 'https://eddb.io/archive/v6/listings.csv'
        response = requests.get(URL, stream=True)

        with open('json/listings.csv', 'wb') as handle:
            for block in response.iter_content(1024):
                handle.write(block)



    with open('json/listings.csv') as csv_file:
        csv_reader = csv.DictReader(csv_file)

        with open('json/stationinfo.json', 'rb') as stationinfofile:
            stationinfo = json.load(stationinfofile)

            index = 0

            Price.objects.all().delete()
            print('deleted old prices..')


            for row in csv_reader:
                if row['commodity_id'] == void_opals:

                    if row['station_id'] in stationinfo:
                        station_name = stationinfo[row['station_id']]['station_name']
                        max_landing_pad_size = stationinfo[row['station_id']]['max_landing_pad_size']
                        system_name = stationinfo[row['station_id']]['system_name']
                        if stationinfo[row['station_id']]['distance_to_star']:
                            distance_to_star = stationinfo[row['station_id']]['distance_to_star']
                        else:
                            distance_to_star = 0
                    else:
                        print('station not found')



                    ##ADD LANDING PAD AND DISTANCE!!!!
                    stationToAdd = Price(system_id = row['id'],
                        systemName=system_name,
                        station_name=station_name,
                        max_landing_pad_size=max_landing_pad_size,
                        distance_to_star=distance_to_star,
                        station_id = row['station_id'],
                        sell_price = row['sell_price']
                        )
                    stations.append(stationToAdd)
                    index += 1
                    if index == 999:
                        Price.objects.bulk_create(stations)
                        stations = []
                        index = 0

            print('finished loop')
            if index > 0:
                Price.objects.bulk_create(stations)
            print('done collecting')

    return HttpResponse('done')
