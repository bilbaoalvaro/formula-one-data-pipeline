# Formula One — Data Acquisition Pipeline

Data acquisition and analysis project built around Formula 1 race data. The pipeline combines web scraping, API requests, data integration and exploratory analysis.

## Project overview

The project follows four main steps:

1. **Web scraping**
   Scrapy collects race classification data from Formula 1 season pages on Wikipedia.

2. **API acquisition**
   The project queries the Jolpica F1 API for driver numbers and pit-stop information for the 2019–2024 seasons, including retry and backoff handling for API rate limits.

3. **Data integration**
   The two sources are merged by driver number to build a consolidated race-level dataset.

4. **Analysis**
   The resulting data is used to study the relationship between starting position and final position, constructor performance, number of pit stops, and pit-stop duration.

## Key analyses

- Starting grid position vs. final race position
- Top constructors by average finishing position
- Average finishing position by number of pit stops
- Pit-stop duration vs. final race position

## Technologies

**Python · Scrapy · Pandas · Requests · NumPy · Matplotlib**

## Project structure

```text
formula-one-data-pipeline/
├── README.md
├── main.py
├── api_f1.py
├── merge_data.py
├── analysis.py
├── scrapy.cfg
├── requirements.txt
├── .gitignore
├── f1_wiki/
│   ├── settings.py
│   └── spiders/
│       └── f1_results.py
├── data/
│   └── sample/
│       └── 2019_round_01.csv ...
├── results/
└── docs/
    └── final_report.pdf
```

## Running the pipeline

Install the dependencies:

```bash
pip install -r requirements.txt
```

Then run:

```bash
python main.py
```

The pipeline requires an internet connection because the acquisition stage accesses Wikipedia and the public Jolpica F1 API. The complete acquisition output is generated locally and is not stored in the repository. A small sample of the scraped data is included in `data/sample/` for reference.

## Project context

**Course:** Data Acquisition  
**Degree:** Mathematical Engineering & Artificial Intelligence  
**University:** Universidad Pontificia Comillas — ICAI  
**Academic year:** 2025/26  

**Group project.**

Team: Enrique Capella, Daniel Carrasco, Alejandro Corredera and Álvaro Bilbao.
