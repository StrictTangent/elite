from django.core. management.base import BaseCommand
from elite.models import Price
import json, requests, ijson, csv, time

class Command(BaseCommand):

    def handle(self, *args, **kwargs):

        void_opals = '350'
        stations = []
        DOWNLOAD = True

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
                self.stdout.write('deleted old prices..')


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
                            self.stdout.write('station not found')




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

                self.stdout.write('finished loop')
                if index > 0:
                    Price.objects.bulk_create(stations)
                self.stdout.write('done collecting')
