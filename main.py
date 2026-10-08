from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from f1_wiki.spiders.f1_results import F1ResultsSpider
import api_f1
import merge_data
import analysis


def run_scrapy():
    print("[1/4] Collecting race classification data with Scrapy...")
    process = CrawlerProcess(get_project_settings())
    process.crawl(F1ResultsSpider)
    process.start()


def main():
    run_scrapy()

    print("[2/4] Collecting driver and pit-stop data from the F1 API...")
    api_f1.main()

    print("[3/4] Merging the acquired datasets...")
    final_df = merge_data.process_all_seasons(start_year=2019, end_year=2024)
    if final_df is None or final_df.empty:
        print("No merged dataset was generated.")
        return
    merge_data.export_final_dataset(final_df, "data/f1_complete_dataset.csv")

    print("[4/4] Generating analysis figures...")
    analysis.main(final_df, "results")
    print("Pipeline completed. Results saved in data/ and results/.")


if __name__ == "__main__":
    main()
