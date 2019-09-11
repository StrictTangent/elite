from django.core. management.base import BaseCommand
from elite.models import Planet
import json, requests, ijson, csv, time

class Command(BaseCommand):

    def handle(self, *args, **kwargs):

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
                                self.stdout.write('found ICY + NOT PRISTINE')
                                if Planet.objects.filter(name=body['name']).exists():
                                    database.get(name=body['name']).delete()
                                    self.stdout.write("Deleted Planet: " + body['name'])
                                    deleted += 1

            namesToAdd = newPlanets - existingPlanets
            B = newPlanets & existingPlanets
            self.stdout.write("BRAND NEW:")
            self.stdout.write(len(namesToAdd))
            self.stdout.write("WOULD BE DUPLICATES:")
            self.stdout.write(len(B))

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
                            self.stdout.write("Added Batch of: " + str(index))
                            planetsToAdd = []
                            index = 0
                if index > 0: #if there are left over planets...
                    Planet.objects.bulk_create(planetsToAdd)
                    self.stdout.write("Added Batch of: " + str(index))

                self.stdout.write("BRAND NEW:")
                self.stdout.write(len(namesToAdd))
                self.stdout.write("WOULD BE DUPLICATES:")
                self.stdout.write(len(B))

                self.stdout.write("DONE")
                self.stdout.write("Added: " + str(added))
                self.stdout.write("Deleted: " + str(deleted))
