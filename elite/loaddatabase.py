from elite.models import Planet, Price
import ijson, json

print('here we go!!!')

with open('databasedump.json', 'rb') as input_file:
    entries = ijson.items(input_file, 'item')

    planetsToAdd = []
    pIndex = 0
    pTotal = 0
    stationsToAdd = []
    sIndex = 0
    sTotal = 0

    MODE = 'price'

    for entry in entries:
        #if entry['model'] == 'elite.planet':
        if MODE == 'planet':
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
                print("Total: " + str(pTotal) + " Planets")
                planetsToAdd = []
                pIndex = 0

        elif entry['model'] == 'elite.price':
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
                print("Total: " + str(sTotal) + " Stations")
                stationsToAdd = []
                sIndex = 0

    if pIndex > 0:
        Planet.objects.bulk_create(planetsToAdd)
        print("Added Batch of: " + str(pIndex))
        print("Total: " + str(pTotal) + " Planets")

    if sIndex > 0:
        Price.objects.bulk_create(stationsToAdd)
        print("Added Batch of: " + str(sIndex) + " Stations")
        print("Total: " + str(sTotal) + " Stations")
