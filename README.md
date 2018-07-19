# Flycatcher
Find cheapest flights from selected airport. 

Flycatcher provides scripts to download flight data from the selected airport, store it
in the internal flight data format and scan the flight data
in order to find cheapest round-trip flights from the selected airport.

Example:
```
round-trip to Venedig Treviso      (TSF) 05 days (2018-08-20 - 2018-08-25) for 35.28 EUR
round-trip to Verona               (VRN) 03 days (2018-08-26 - 2018-08-29) for 35.82 EUR
round-trip to Brüssel Zaventem     (BRU) 07 days (2018-08-09 - 2018-08-16) for 36.20 EUR
round-trip to Glasgow              (GLA) 04 days (2018-08-24 - 2018-08-28) for 39.01 EUR
round-trip to Rom Ciampino         (CIA) 07 days (2018-08-16 - 2018-08-23) for 39.46 EUR
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