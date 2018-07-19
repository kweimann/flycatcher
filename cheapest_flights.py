from datetime import datetime, timedelta
from setup import ROOT_DIR
import pickle
import logging
import heapq
import argparse
import os


def find_cheapest_flights(flight_data,
                          origin,   # airport id
                          n: int = None,
                          min_days: int = None,
                          max_days: int = None,
                          min_date: datetime = None,
                          max_date: datetime = None,
                          max_price: int = None,
                          selected_destinations: list = None,
                          excluded_destinations: list = None,
                          max_flights_per_airport: int = None):
    """
    Finds cheapest round-trip flights according to provided requirements.
    :param flight_data: data in required format, see documentation for details
    :param origin: id of the starting airport
    :param n: maximal number of yielded round-trip flights. By default yields all flights
    :param min_days: minimal number of days a round-trip should last. Default: 1.
    :param max_days: maximal number of days a round-trip may last. By default maximal number of days possible.
    :param min_date: earliest date of departure. By default equal to the earliest flight possible.
    :param max_date: latest date of return. By default equal to the latest flight possible.
    :param max_price: maximal full price of the round-trip (both flights together)
    :param selected_destinations: consider only these destinations for the round-trip.
    By default consider all destinations.
    :param excluded_destinations: exclude these destinations from the round-trip.
    By default consider all destinations.
    Note that both `selected_destinations` and `excluded_destinations` may not be set at the same time
    :param max_flights_per_airport: maximal number of returned round-trip flights per airport.
    By default return all round-trip flights
    :return: generator of (flight to X, flight from X) in ascending order by round-trip price
    """
    if n is not None and n < 0:
        raise ValueError('`n` must be larger than 0')
    if min_days is not None and min_days <= 0:
        raise ValueError('`min_days` must be larger than 0')
    if max_days is not None and max_days <= 0:
        raise ValueError('`max_days` must be larger than 0')
    if min_days is not None and max_days is not None and min_days > max_days:
        raise ValueError('`min_days` must be smaller than `max_days`')
    if min_date is not None and max_date is not None and min_date > max_date:
        raise ValueError('`min_date` must be smaller or equal `max_date`')
    if max_price is not None and max_price <= 0:
        raise ValueError('`max_price` must be larger than 0')
    if selected_destinations is not None and excluded_destinations is not None:
        raise ValueError('`selected_destinations` and `excluded_destinations` cannot both be set')
    if max_flights_per_airport is not None and max_flights_per_airport <= 0:
        raise ValueError('`max_flights_per_airport` must be larger than 0')

    flights = flight_data['flights']
    # build airport id -> airport mapping
    airports = {airport['id']: airport for airport in flight_data['airports']}

    if origin not in airports:
        raise ValueError('%s is not in the airport list' % origin)

    # filter out all destinations that were not selected
    if selected_destinations is not None:
        for airport_id in list(airports.keys()):
            if origin != airport_id and airport_id not in selected_destinations:
                airports.pop(airport_id)

    # filter out all excluded destinations
    if excluded_destinations is not None:
        for excluded in excluded_destinations:
            airports.pop(excluded, None)

    logging.debug('destination airports: %s' % airports.keys())

    date_range = None

    # scan flights to find earliest and latest flight dates
    for flight in flights:
        date = datetime.strptime(flight['date'], '%Y-%m-%d')

        if date_range is None:
            date_range = date, date
        else:
            date_range_min, date_range_max = date_range
            date_range = min(date, date_range_min), max(date, date_range_max)

    date_range_min, date_range_max = date_range

    # restrict `min_date` to earliest/latest flight date interval
    if min_date is None:
        min_date = date_range_min
    else:
        min_date = max(min(min_date, date_range_max), date_range_min)

    # restrict `max_date` to [earliest, latest] flight date interval
    if max_date is None:
        max_date = date_range_max
    else:
        max_date = min(max(max_date, date_range_min), date_range_max)

    logging.debug('min_date: %s' % min_date.strftime('%Y-%m-%d'))
    logging.debug('max_date: %s' % max_date.strftime('%Y-%m-%d'))

    date_range_days = (max_date - min_date).days

    # restrict `min_days` to [1, max possible days] interval
    if min_days is None:
        min_days = 1
    else:
        min_days = max(min(min_days, date_range_days), 1)

    # restrict `max_days` to [1, max possible days] interval
    if max_days is None:
        max_days = date_range_days
    else:
        max_days = min(max(max_days, 1), date_range_days)

    logging.debug('min_days: %d' % min_days)
    logging.debug('max_days: %d' % max_days)

    # initialize index for future lookup on following fields: date, origin_airport, destination_airport
    index = {
        (min_date + timedelta(day)).strftime('%Y-%m-%d'): {
            origin: {
                destination: [] for destination in airports.keys()
            } for origin in airports.keys()
        } for day in range(date_range_days + 1)
    }

    # add all relevant flights to the index
    for flight in flights:
        flight_date = datetime.strptime(flight['date'], '%Y-%m-%d')
        if flight['origin'] in airports \
                and flight['destination'] in airports \
                and min_date <= flight_date <= max_date:
            index[flight['date']][flight['origin']][flight['destination']].append(flight)

    flight_queue = []
    idx = 0

    # search index looking for round-trip flights that fulfil provided requirements
    # add found round-trip flights to heap sorted by full price of the trip
    for departure_day in range(date_range_days - min_days + 1):
        for return_day in range(departure_day + min_days, min(departure_day + max_days, date_range_days) + 1):
            # first iterate over all possible trip dates (departure, return)
            departure_date = (min_date + timedelta(days=departure_day)).strftime('%Y-%m-%d')
            return_date = (min_date + timedelta(days=return_day)).strftime('%Y-%m-%d')

            # then look for all flight pairs for each trip date
            # iterate over all flights to the destination
            for to_airport_id, to_flights in index[departure_date][origin].items():
                # iterate over all flights from the destination
                for from_flight in index[return_date][to_airport_id][origin]:
                    for to_flight in to_flights:
                        # calculate trip price and push it to heap if trip meets requirements
                        full_price = to_flight['price'] + from_flight['price']
                        if max_price is None or full_price <= max_price:
                            heapq.heappush(flight_queue,
                                           (full_price, departure_day, return_day, idx, to_flight, from_flight))
                            idx += 1

    # restrict the number of yielded trips to [1, heap length] interval
    if n is None:
        n = len(flight_queue)
    else:
        n = min(n, len(flight_queue))

    logging.debug('n: %d' % n)

    if max_flights_per_airport is not None:
        visited_airports = {airport_id: 0 for airport_id in airports.keys()}
    else:
        visited_airports = None

    # yield all found round-trip flights
    for _ in range(n):
        _, _, _, _, to_flight, from_flight = heapq.heappop(flight_queue)
        if visited_airports is None or visited_airports[to_flight['destination']] < max_flights_per_airport:
            yield to_flight, from_flight
            if visited_airports is not None:
                visited_airports[to_flight['destination']] += 1


class TripFormatter:
    def __init__(self, airports):
        """
        :param airports: dictionary airport_id -> airport
        """
        self.airports = airports

    def format(self, to_flight, from_flight):
        """
        Formats round-trip flight.
        :param to_flight: flight to the destination
        :param from_flight: flight from the destination
        :return: formatted round-trip flight
        """
        departure_date = datetime.strptime(to_flight['date'], '%Y-%m-%d')
        return_date = datetime.strptime(from_flight['date'], '%Y-%m-%d')
        duration_days = (return_date - departure_date).days

        destination = self.airports[to_flight['destination']]

        if 'name' in destination:
            if 'iata' in destination:
                name = '%-20.20s (%s)' % (destination['name'], destination['iata'])
            else:
                name = '%-20.20s' % destination['name']
        else:
            name = destination['id']

        return 'round-trip to %s %02d days (%s - %s) for %0.2f %s' \
               % (name,
                  duration_days,
                  to_flight['date'],
                  from_flight['date'],
                  to_flight['price'] + from_flight['price'],
                  to_flight['currency'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Find cheapest flights from selected airport.')
    parser.add_argument('origin', type=str, help='id of the starting airport')
    parser.add_argument('-data', type=str, help='path to flight data. '
                                                'By default `ryanair_<origin>.p` in the package root directory')
    parser.add_argument('-n', type=int, help='maximal number of yielded round-trip flights. '
                                             'By default yields all flights')
    parser.add_argument('-min_days', type=int, help='minimal number of days a round-trip should last.'
                                                    ' Default: 1')
    parser.add_argument('-max_days', type=int, help='maximal number of days a round-trip may last.'
                                                    ' By default maximal number of days possible')
    parser.add_argument('-min_date', type=str, help='earliest date of departure (format: yyyy-mm-dd).'
                                                    ' By default equal to earliest flight possible')
    parser.add_argument('-max_date', type=str, help='latest date of return (format: yyyy-mm-dd).'
                                                    ' By default equal to latest flight possible')
    parser.add_argument('-max_price', type=int, help='maximal full price of the round-trip (both flights together) '
                                                     'By default consider all flights')
    parser.add_argument('-selected_destinations', help='consider only these destinations for the round-trip. '
                                                       'Comma-separated list of airport ids. '
                                                       'By default consider all destinations')
    parser.add_argument('-excluded_destinations', help='exclude these destinations from the round-trip. '
                                                       'Comma-separated list of airport ids. '
                                                       'By default consider all destinations. '
                                                       'Note that both `selected_destinations` and '
                                                       '`excluded_destinations` may not be set at the same time')
    parser.add_argument('-max_flights_per_airport', type=int,
                        help='maximal number of yielded round-trip flights per destination airport. '
                             'By default return all round-trip flights')
    parser.add_argument('--debug', action='store_true', help='show debug messages')
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format='%(asctime)s %(levelname)-8s %(name)-10.10s %(message)s')

    path = args.data if args.data is not None else os.path.join(ROOT_DIR, 'ryanair_%s.p' % args.origin)

    if os.path.isfile(path):
        data = pickle.load(open(path, 'rb'))

        airports = {airport['id']: airport for airport in data['airports']}
        formatter = TripFormatter(airports)

        if args.origin not in airports:
            logging.error('%s not found in the airport list. Available airport ids: %s'
                          % (args.origin, ','.join(airports.keys())))
        else:
            try:
                min_date = None if args.min_date is None else datetime.strptime(args.min_date, '%Y-%m-%d')
                max_date = None if args.max_date is None else datetime.strptime(args.max_date, '%Y-%m-%d')

                cheapest_flights = find_cheapest_flights(data,
                                                         origin=args.origin,
                                                         n=args.n,
                                                         min_days=args.min_days,
                                                         max_days=args.max_days,
                                                         min_date=min_date,
                                                         max_date=max_date,
                                                         max_price=args.max_price,
                                                         selected_destinations=args.selected_destinations,
                                                         excluded_destinations=args.excluded_destinations,
                                                         max_flights_per_airport=args.max_flights_per_airport)

                for to_flight, from_flight in cheapest_flights:
                    print(formatter.format(to_flight, from_flight))
            except ValueError as e:
                logging.exception(e)
    elif args.data is None:
        logging.error('Failed to automatically find flight data.'
                      ' Please use -data argument to specify the path to flight data.')
    else:
        logging.error('Flight data not found: %s' % path)
