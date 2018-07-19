# Flycatcher
Find cheapest flights from selected airport.

### Installation

No installation required!

### Usage

1. Download data using one of the provided downloaders or write your own downloader.
 Downloaded data must conform to the provided flight data format.
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