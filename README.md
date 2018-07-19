# Flycatcher
Find cheapest flights from selected airport. 

Flycatcher provides scripts to download flight data from the selected airport, store it
in the internal flight data format and scan the flight data
in order to find cheapest round-trip flights from the selected airport.

Example:
```
round-trip to Verona               (VRN) 31 days (2018-07-29 - 2018-08-29) for 25.96 EUR
round-trip to London Stansted      (STN) 28 days (2018-07-24 - 2018-08-21) for 25.98 EUR
round-trip to Brüssel Zaventem     (BRU) 01 days (2018-08-29 - 2018-08-30) for 29.96 EUR
round-trip to Rom Ciampino         (CIA) 22 days (2018-08-01 - 2018-08-23) for 29.97 EUR
round-trip to Bologna              (BLQ) 31 days (2018-07-28 - 2018-08-28) for 29.98 EUR

```

### Installation

No installation required!

### Usage

1. Download data using one of the provided downloaders or write your own downloader.
 Downloaded data must conform to the provided flight data format. Available downloaders:
    * `ryanair_downloader.py`
2. Run `cheapest_flights.py` on the downloaded flight data to find cheapest flights.

### Flight Data Model

```
{
	airports: [
		{
			id: String
			iata: Optional[String]
			name: Optional[String]
		}
	],
	flights: [
		{
			origin: String          # id
			destination: String     # id
			date: String            # %Y-%m-%d
			price: Double
			currency: String
			time: Optional[String]  # %H:%M:%S
			duration: Optional[Int] # seconds
		}
	]
}
```