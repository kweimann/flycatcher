from flycatcher.downloader import Downloader
from datetime import datetime
from setup import ROOT_DIR
import argparse
import calendar
import logging
import os
import pickle


class RyanairDownloader(Downloader):
    API_ENDPOINT = 'https://api.ryanair.com/farefinder/3/roundTripFares'
    HEADERS = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.5',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Host': 'api.ryanair.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:62.0) Gecko/20100101 Firefox/62.0'
    }

    def get_round_trip_fares(self,
                             origin: str,           # airport iata
                             date_from: datetime,
                             date_to: datetime,
                             language: str = 'en',
                             market: str = 'en-US',
                             headers=HEADERS):
        params = dict(
            departureAirportIataCode=origin,
            inboundDepartureDateFrom=date_from.strftime('%Y-%m-%d'),
            inboundDepartureDateTo=date_to.strftime('%Y-%m-%d'),
            outboundDepartureDateFrom=date_from.strftime('%Y-%m-%d'),
            outboundDepartureDateTo=date_to.strftime('%Y-%m-%d'),
            language=language,
            market=market
        )

        return self._get(self.API_ENDPOINT, params=params, headers=headers)

    def get_cheapest_per_day(self,
                             origin: str,       # airport iata
                             destination: str,  # airport iata
                             month: int,
                             year: int,
                             market: str = 'en-US',
                             headers=HEADERS):
        url = self.API_ENDPOINT + '/%s/%s/cheapestPerDay' % (origin, destination)

        params = dict(
            outboundMonthOfDate='%04d-%02d-01' % (year, month),
            market=market
        )

        return self._get(url, params=params, headers=headers)


def get_ryanair_flight_data(origin: str,                # airport iata
                            date_from: datetime = None,
                            date_to: datetime = None,
                            language: str = None,
                            market: str = None):
    """
    Downloads and parsed flight data from Ryanair API
    :param origin: IATA of the starting airport
    :param date_from: earliest date of departure. By default equal to the current day.
    :param date_to: latest date of return. By default equal to the last day of the month after `date_from`.
    :param language: data language
    :param market: language code. Flights prices depend on the market.
    :return:
    """
    if date_to is not None and date_to < datetime.now():
        raise ValueError('`date_to` must be a future date')
    if date_from is not None and date_to is not None and date_from > date_to:
        raise ValueError('`date_from` must be smaller or equal `date_to`')

    # set `date_from` to current day if not provided by the user
    if date_from is None:
        date_from = datetime.now()

    # set `date_to` to the last day of the month after `date_from` if not provided by the user
    if date_to is None:
        to_month = date_from.month % 12 + 1
        to_year = date_from.year + date_from.month // 12
        _, to_day = calendar.monthrange(to_year, to_month)
        date_to = datetime(to_year, to_month, to_day)

    if language is None:
        language = 'en'

    if market is None:
        market = 'en-US'

    logging.debug('date_from: %s' % date_from.strftime('%Y-%m-%d'))
    logging.debug('date_to: %s' % date_to.strftime('%Y-%m-%d'))

    # initialize downloader, wait up to 500-1000 ms between two requests
    downloader = RyanairDownloader(wait_between_requests=(500, 1000))

    # download cheapest fares in the given time period
    # use this information to determine possible destination airports
    round_trip_fares = downloader.get_round_trip_fares(origin,
                                                       date_to=date_to,
                                                       date_from=date_from,
                                                       language=language,
                                                       market=market)

    if round_trip_fares is None or not round_trip_fares['fares']:
        logging.error('Failed to download round trip fares.')
        return

    # get origin airport data
    origin_airport = round_trip_fares['fares'][0]['outbound']['departureAirport']

    origin_airport = {
        'id': origin_airport['iataCode'],
        'name': origin_airport['name'],
        'iata': origin_airport['iataCode']
    }

    data = {
        'airports': [],
        'flights': []
    }

    # get data of all destination airports
    for fare in round_trip_fares['fares']:
        destination_airport = fare['outbound']['arrivalAirport']
        airport = {
            'id': destination_airport['iataCode'],
            'name': destination_airport['name'],
            'iata': destination_airport['iataCode'],
        }

        data['airports'].append(airport)

    logging.debug('destination airports (%d): %s'
                  % (len(data['airports']),
                     [airport['id'] for airport in data['airports']]))

    # calculate how many months of flight data need to be downloaded
    month_difference = (date_to.year - date_from.year) * 12 + date_to.month - date_from.month

    for destination in data['airports']:
        for current_month_difference in range(month_difference + 1):
            month = (date_from.month - 1 + current_month_difference) % 12 + 1
            year = date_from.year + (date_from.month - 1 + current_month_difference) // 12

            # for each destination download two-way flight data by month
            for from_airport, to_airport in _two_way_generator([(origin, destination['iata'])]):
                logging.info('Downloading flights from %s to %s on %04d-%02d.'
                             % (from_airport, to_airport, year, month))

                # get flight data on a route in given month
                cheapest_per_day = downloader.get_cheapest_per_day(from_airport,
                                                                   to_airport,
                                                                   month=month,
                                                                   year=year,
                                                                   market=market)

                if cheapest_per_day is None:
                    logging.warning('Failed to download flights.')
                else:
                    for flight in cheapest_per_day['outbound']['fares']:

                        flight_day = datetime.strptime(flight['day'], '%Y-%m-%d')

                        # make sure flight is available and meets the requirements
                        if flight['price'] \
                                and not flight['unavailable'] \
                                and not flight['soldOut'] \
                                and date_from <= flight_day <= date_to:

                            flight = {
                                'origin': from_airport,
                                'destination': to_airport,
                                'date': flight['day'],
                                'price': flight['price']['value'],
                                'currency': flight['price']['currencyCode']
                            }

                            data['flights'].append(flight)

    data['airports'].append(origin_airport)

    return data


def _two_way_generator(routes):
    for route in iter(routes):
        yield route
        yield reversed(route)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download and parse flight data from Ryanair API.')
    parser.add_argument('origin', type=str, help='IATA of the starting airport')
    parser.add_argument('-out', type=str, help='path to file where data should be stored. '
                                               'By default `ryanair_<origin>.p` in the package root directory')
    parser.add_argument('-date_from', type=str, help='earliest date of departure.'
                                                     ' By default equal to the current day.')
    parser.add_argument('-date_to', type=str, help='latest date of return.'
                                                   ' By default equal to the last day of the month after `date_from`.')
    parser.add_argument('-language', type=str, help='data language. Default: en')
    parser.add_argument('-market', type=str, help='language code. Flights prices depend on the market.'
                                                  ' Default: en-US')
    parser.add_argument('--debug', action='store_true', help='show debug messages')
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format='%(asctime)s %(levelname)-8s %(name)-25.25s %(message)s')

    path = args.out if args.out is not None else os.path.join(ROOT_DIR, 'ryanair_%s.p' % args.origin)
    date_from = None if args.date_from is None else datetime.strptime(args.date_from, '%Y-%m-%d')
    date_to = None if args.date_to is None else datetime.strptime(args.date_to, '%Y-%m-%d')

    with open(path, 'wb') as fh:
        data = get_ryanair_flight_data(args.origin,
                                       date_from=date_from,
                                       date_to=date_to,
                                       language=args.language,
                                       market=args.market)

        if data:
            pickle.dump(data, fh)
