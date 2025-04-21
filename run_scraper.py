# run_scraper.py
import time

from scienceDirectExtractor import (
    get_links_from_issues_science_direct, 
    actual_paper_links, 
    filter_links,
    get_unique_link,
    send_links_to_scrape,
    get_business_score,
    add_columns_score_justification_created_on,
    add_papers_to_db
)

from ieeeExtractor import (
    get_links_from_issues_ieee,
    filter_links_ieee,
    get_unique_link_ieee,
    send_links_to_scrape_ieee,
    get_business_score_ieee,
    add_columns_score_justification_created_on_ieee,
    add_papers_to_db_ieee
)

def scrape_data_from_the_science_direct_first_half():
    total_links = get_links_from_issues_science_direct()
    total_links_issues = actual_paper_links(total_links)
    filtered_links = filter_links(total_links_issues)
    unique_links = get_unique_link(filtered_links)
    time.sleep(10)
    return unique_links

def scrape_data_from_the_science_direct_second_half(unique_links):
    data, link_ignored = send_links_to_scrape(unique_links)
    print(f"\nTotal Data Length for Business score: {len(data)}\n")
    abstract_list = [item['abstract'] for item in data if 'abstract' in item]
    parsed_data = get_business_score(abstract_list)
    updated_data = add_columns_score_justification_created_on(data, parsed_data)
    add_papers_to_db(updated_data)

def scrape_data_from_the_science_direct():
    unique_links = scrape_data_from_the_science_direct_first_half()
    scrape_data_from_the_science_direct_second_half(unique_links)
    

def scrape_data_from_ieee():
    total_links = get_links_from_issues_ieee()
    filtered_links = filter_links_ieee(total_links)
    unique_links = get_unique_link_ieee(filtered_links)
    data, link_ignored = send_links_to_scrape_ieee(unique_links)
    abstract_list = [item['abstract'] for item in data if 'abstract' in item]
    parsed_data = get_business_score_ieee(abstract_list)
    updated_data = add_columns_score_justification_created_on_ieee(data, parsed_data)
    add_papers_to_db_ieee(updated_data)

if __name__ == "__main__":
    scrape_data_from_ieee()
    scrape_data_from_the_science_direct()
    
