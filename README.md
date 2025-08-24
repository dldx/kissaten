A coffee beans database scraped from individual coffee roasters across the world.


## Data

Each roaster has its own scraper. The scrapers are in the `src/kissaten/scrapers` directory.
The data is stored in individual json files in the `data` directory, with one folder per roaster per timestamp.

## Usage

To run all the scrapers, use the `kissaten scrape` command.
To run a single scraper, use the `kissaten scrape <roaster_name>` command.
To get a list of all the roasters, use the `kissaten list roasters` command.



