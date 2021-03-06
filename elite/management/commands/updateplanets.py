from django.core. management.base import BaseCommand
from elite.models import Planet
from django.db.models import Q
import json, requests, ijson, csv, time

class Command(BaseCommand):

    def handle(self, *args, **kwargs):

        DOWNLOAD = True

        if DOWNLOAD:

            startTime = time.time()

            URL = "https://www.edsm.net/dump/bodies7days.json"
            response = requests.get(URL, stream=True)

            with open('json/updatedPlanets.json', 'wb') as handle:
                for block in response.iter_content(1024):
                    handle.write(block)
            self.stdout.write("Finished download in " + str(time.time() - startTime) + " seconds")

        beginTime = time.time()
        startTime = time.time()
        with open('json/updatedPlanets.json', 'rb') as input_file:
            bodies = ijson.items(input_file, 'item')
            added = 0
            deleted = 0

            index = 0
            planetsToAdd = []

            self.stdout.write("getting started...")

            #newPlanets = set()
            #existingPlanets = set()
            #names = Planet.objects.values_list('name', flat=True)
            #existingPlanets.update(Planet.objects.values_list('name', flat=True))

            eligablePlanets = [] #dictionarys
            eligableSystems = set() #strings

            for body in bodies:
                if body['type'] == 'Planet':
                    foundIcy = False
                    if 'rings' in body:
                        for ring in body['rings']:
                            if ring['type'] == "Icy":
                                foundIcy = True
                        if foundIcy:
                            if body['reserveLevel'] == 'Pristine':
                                eligableSystems.add(body['systemName'])
                                eligablePlanets.append({'name':body['name'],
                                                        'systemName':body['systemName'],
                                                        'distanceToArrival':body['distanceToArrival']})
                            else:
                                self.stdout.write('found ICY + NOT PRISTINE')
                                if Planet.objects.filter(name=body['name']).exists():
                                    Planet.objects.get(name=body['name']).delete()
                                    self.stdout.write("Deleted Planet: " + body['name'])
                                    deleted += 1

            #finished first loop
            self.stdout.write("Finished adding eligables in " + str(time.time() - startTime) + " seconds")
            startTime = time.time()
            sIndex = 0
            names = []#list of names
            self.stdout.write(str(len(eligableSystems)) + "eligible systems...")
            for system in eligableSystems:
                sIndex += 1
                if sIndex == 1:
                    query = Q(systemName=system)
                else:
                    query.add(Q(systemName=system), Q.OR)
                if sIndex == 990 or sIndex == len(eligableSystems):
                    self.stdout.write('making a query...')

                    queryset = Planet.objects.filter(query)
                    for item in queryset:
                        names.append(item.name)
                    sIndex = 0
            del eligableSystems
            self.stdout.write("Finished Q Query Loop in " + str(time.time() - startTime) + " seconds")
            startTime = time.time()
            for planet in eligablePlanets:
                if planet['name'] not in names:
                    planetToAdd = Planet(name = planet['name'],
                        distanceToArrival = planet['distanceToArrival'],
                        systemName = planet['systemName'])
                    planetsToAdd.append(planetToAdd)
                    #self.stdout.write("adding planet...")
                    added += 1
                    index += 1
                    if index == 999:
                        Planet.objects.bulk_create(planetsToAdd)
                        self.stdout.write("Added Batch of: " + str(index))
                        planetsToAdd = []
                        index = 0
            if index > 0: #if there are left over planets...
                Planet.objects.bulk_create(planetsToAdd)
                self.stdout.write("Added Batch of: " + str(index))

            self.stdout.write("DONE")
            self.stdout.write("Finished " + str(time.time() - beginTime) + " seconds")
            self.stdout.write("Added: " + str(added))
            self.stdout.write("Deleted: " + str(deleted))
