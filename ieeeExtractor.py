from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
import time
import numpy as np
import re
import requests
from collections import Counter
import pandas as pd
from urllib.parse import urlparse, parse_qs
import json
from datetime import date
from webdriver_manager.chrome import ChromeDriverManager
import os 

def get_links_from_issues_ieee():
    options = Options()
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    url = 'https://ieeexplore.ieee.org/xpl/topAccessedArticles.jsp?punumber=6287639'
    total_links = []
    driver.get(url)
    
    try:
        
        accept_all_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@class='osano-cm-dialog__buttons osano-cm-buttons']//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept all')]"))
        )
        accept_all_button.click()
        time.sleep(2)
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/document/']")
        paper_links = set()
        for link in links:
            href = link.get_attribute("href")
            if href:
                paper_links.add(href)
    
        print("Extracted Paper Links:")
        for paper_link in paper_links:
            if "citations?tabFilter=papers#citations" in paper_link:
                print(paper_link)
            else:
                total_links.append(paper_link)
    
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print(f"Total Links: {len(total_links)}")
        driver.quit()
        return total_links
    
def filter_links_ieee(total_links_issues):
    filtered_links = []
    url = f"{os.getenv("DJANGO_URL","http://127.0.0.1:8000")}/check-link"
    editor_url = f"{os.getenv("DJANGO_URL","http://127.0.0.1:8000")}/check-editor-link"
    
    for link in total_links_issues:
        
        response = requests.get(url, params={"link": link})
        response_editor = requests.get(editor_url, params={"link": link})
        
        if response.status_code == 200 and response_editor.status_code == 200:
            response_json = response.json()
            response_editor_json = response_editor.json()
            
            if response_json['exists'] == True:
                #print("Data successfully sent to the FastAPI endpoint!")
                print(f"Response: {response_json}, link: {link}")
            elif response_editor_json['exists'] == False: ## if the link is not present in the actual paper then we will further check into
                ## editors link if it is still not present in the db then we will store it in a list for scrapping
                filtered_links.append(link)
            
        else:
            print(f"Failed to send data. HTTP Status Code: {response.status_code}")
            #print("Response:", response.text)
    return filtered_links

def get_unique_link_ieee(filtered_links):
    print(f"length of list: {len(filtered_links)}")
    link_counts = Counter(filtered_links)
    duplicates = [link for link, count in link_counts.items() if count > 1]
    print("Duplicate links:", len(duplicates))
    seen = set()
    unique_links = []
    
    for link in filtered_links:
        if link not in seen:
            unique_links.append(link)
            seen.add(link)
    
    print(len(unique_links))# Prints the count of unique links
    return unique_links

def get_scrapped_data_ieee(link):

    link_index = 0
    error_found = False
    editor_link = False
    title = None
    authors_emails = {}
    abstract = None
    obj = {}
    obj["publication_title"] = "IEEE Access"
    
    options = Options()
    options.headless = False  
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    obj["link"] = link

    
    try:
        driver.get(link)
        accept_all_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@class='osano-cm-dialog__buttons osano-cm-buttons']//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept all')]"))
        )
        accept_all_button.click()

    except Exception as e:
        pass

    try:

        title_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1.document-title span"))
        )
        
        # Extract and print the title text
        title = title_element.text.strip()
        obj["title"] = title

    except Exception as e:
        print(f"title Error")
        error_found = True
        driver.quit()
        return error_found, editor_link, obj

    try:

        authors_div = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.authors-info-container"))
        )
        author_name_spans = authors_div.find_elements(By.CSS_SELECTOR, "span.blue-tooltip span")
        author_names = [span.text.strip() for span in author_name_spans if span.text.strip()]
        for name in author_names:
            name_split = name.split(" ")
            if len(name_split) == 2:
                authors_emails[name_split[0] + "=" + name_split[1]] = "Not Found"
            else:
                first_name = name_split.pop(0)
                last_name = " ".join(name_split)
                authors_emails[first_name + "=" + last_name] = "Not Found"
                
        obj["author_email"] = authors_emails
        
    except Exception as e:
        print(f"author_email Error")
        error_found = True
        driver.quit()
        return error_found, editor_link, obj

    try:
        
        div_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[xplmathjax]"))
        )
        
        abstract = div_element.text.strip()
        obj["abstract"] = abstract
    
    except Exception as e:
        print(f"abstract Error")
        error_found = True
        driver.quit()
        return error_found, editor_link, obj

    try:
        
        pub_date_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.u-pb-1.doc-abstract-pubdate"))
        )
        full_text = pub_date_element.text.strip()
        if "Date of Publication:" in full_text:
            publication_date = full_text.split("Date of Publication:")[1].strip()
            obj["published_year"] = publication_date
        else:
            error_found = True
            driver.quit()
            return error_found, editor_link, obj
    
    except Exception as e:
        print(f"published_year Error")
        error_found = True
        driver.quit()
        return error_found, editor_link, obj

    try:

        keywords_div = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.ID, "keywords-header"))
        )
    
        keywords_div.click()
    except Exception as e:
        pass

    try:
        
        top_ul = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.doc-keywords-list.stats-keywords-list"))
        )
    
        top_li_elements = top_ul.find_elements(By.TAG_NAME, "li")
       
        anchor_texts = []
        for li in top_li_elements:
            try:
                
                nested_ul = li.find_element(By.CSS_SELECTOR, "ul.u-mt-1.u-p-0.List--no-style.List--inline")
                a_tags = WebDriverWait(nested_ul, 5).until(
                    EC.presence_of_all_elements_located((By.TAG_NAME, "a"))
                )
                for a_tag in a_tags:
                    text = a_tag.text.strip()
                    href = a_tag.get_attribute("href")
                    parsed_url = urlparse(href)

                    query_params = parse_qs(parsed_url.query)
                    
                    if "queryText" in query_params:
                        query_text = query_params["queryText"][0]  
                        keyword = query_text.replace('"Index Terms":', '').strip()
                        anchor_texts.append(keyword)
                    else:
                        print("No 'queryText' parameter found in the URL.")
                        
            except Exception as e:
                continue
    
        anchor_texts = ", ".join(anchor_texts)
        obj["keywords"] = anchor_texts      
    
    except Exception as e:
        print(f"Keyword Error")
        error_found = True
        driver.quit()
        return error_found, editor_link, obj

          
    
    driver.quit()
    return error_found, editor_link, obj
        
def send_links_to_scrape_ieee(unique_links):
    url_add_paper = "http://127.0.0.1:8000/add-paper"
    url_insert_ignore = "http://127.0.0.1:8000/insert-ignored-links"
    url_insert_editor = f"{os.getenv("DJANGO_URL","http://127.0.0.1:8000")}/insert-editor-links"
    
    data = []
    link_ignored = []
    
    for link_index, link in enumerate(unique_links, start=0):  # start=1 makes index 1-based
        print(f"Opening link {link_index}/{len(unique_links)}: {unique_links[link_index]}")
        
        start_time = time.time()
        
        error_found, editor_link, obj = get_scrapped_data_ieee(unique_links[link_index])
        
        end_time = time.time()
        duration = end_time - start_time
        print(f"Time taken for this iteration: {duration:.2f} seconds")
        
        if error_found:
            link_ignored.append(link)
                
        elif editor_link:
            
            response = requests.get(url_insert_editor, params={"link": unique_links[link_index]})
        
            if response.status_code == 200:
                print("Data successfully sent to the FastAPI endpoint!")
                #print("Response:", response.json())
            else:
                print(f"Failed to send data. HTTP Status Code: {response.status_code}")
                #print("Response:", response.text)
                
        else:
            data.append(obj)
        print("\n")
    
    print(f"Total Data Length: {len(data)}")
    return data, link_ignored

def get_business_score_ieee(abstract_list):
    url = f"{os.getenv("DJANGO_URL","http://127.0.0.1:8000")}/get-business-score"

    # Prepare the request payload
    #abstract_list = data_frame["abstract"].tolist()
    
    # Send POST request to API
    response = requests.post(url, json={"abstract": abstract_list})
    
    if response.status_code == 200:
            print("Data successfully sent to the FastAPI endpoint!")
            #print("Response:", response.json())
    else:
        print(f"Failed to send data. HTTP Status Code: {response.status_code}")
        #print("Response:", response.text)
    response_data = response.json()
    parsed_data = json.loads(response_data)
    return parsed_data

def add_columns_score_justification_created_on_ieee(data, score_justification):
    data_frame = pd.DataFrame(data)
    today_str = date.today().strftime("%d %b %Y")  # e.g., '21 Mar 2025'

    data_frame["created_on"] = today_str
    data_frame["score"] = None
    data_frame["justification"] = None
    
    abstract_mapping = {item["abstract_id"]: (item["score"], item["justification"]) for item in score_justification["abstracts"]}

    for index, row in data_frame.iterrows():
        abstract_id = index + 1  # Assuming abstract IDs match DataFrame index + 1
    
        if abstract_id in abstract_mapping:
            data_frame.at[index, "score"] = abstract_mapping[abstract_id][0]
            data_frame.at[index, "justification"] = abstract_mapping[abstract_id][1]
    
    #data_frame.to_csv("/Users/naumanahmed/Desktop/Programming/pdfExtractor/csv/journal_5.csv", index=False)
    return data_frame

def add_papers_to_db_ieee(updated_data):
    url = f"{os.getenv("DJANGO_URL","http://127.0.0.1:8000")}/add-paper"

    for index, row in updated_data.iterrows():
        
        author_email_str = "; ".join([f"{k}: {v}" for k, v in row["author_email"].items()])
        author_entries = author_email_str.split("; ") ## author_emails , and author_email ;
        
        author_email_dict = {}
        for entry in author_entries:
            name, email = entry.split(": ")
            author_email_dict[name] = email
        
        data = {
            "link": row["link"],
            "title": row["title"],
            "author_email": author_email_dict,
            "abstract": row["abstract"],
            "published_year": row["published_year"],
            "keywords": row["keywords"].split(","),
            "publication_title": row["publication_title"],
            "created_on": row["created_on"],
            "business_score":row["score"],
            "business_score_justification": row["justification"],
        }
    
        response = requests.post(url, json=data)
        
        if response.status_code == 200:
            print("Data successfully sent to the FastAPI endpoint!")
            #print("Response:", response.json())
        else:
            print(f"Failed to send data. HTTP Status Code: {response.status_code}")
            #print("Response:", response.text)
        print("\n")