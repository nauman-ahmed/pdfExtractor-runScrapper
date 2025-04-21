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
import json
import random
from datetime import date
from webdriver_manager.chrome import ChromeDriverManager
import os


def get_links_from_issues_science_direct():
    
    total_links = []
    url_list  = ['https://www.sciencedirect.com/journal/information-and-software-technology/issues',
                 'https://www.sciencedirect.com/journal/journal-of-business-venturing/issues',
                 'https://www.sciencedirect.com/journal/journal-of-business-venturing-insights/issues'
                ]

    try:
        for url in url_list:
            options = Options()
            #options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(url)
            
            year_to_keep = ["2019","2020","2021","2022","2023","2024","2025","2026","2027"]
            
            # Accept cookies if the button appears
            accept_cookies_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept all cookies')]"))
            )
            accept_cookies_button.click()
        
            # Wait for the `ol` element with the class to load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.accordion-container.u-font-sans.js-accordion-container'))
            )
        
            # Locate the `ol` element with the specific class
            ol_element = driver.find_element(By.CSS_SELECTOR, '.accordion-container.u-font-sans.js-accordion-container')
        
            # Get all `li` elements within this `ol`
            li_elements = ol_element.find_elements(By.TAG_NAME, 'li')
        
            # Retrieve and print the HTML or text content of each `li` element
            for index, li in enumerate(li_elements):
                try:
                    li_text = li.text
                    first_part = li_text.split('—')[0].strip()
                    if first_part in year_to_keep:
                        if index != 0:
                            button = li.find_element(By.TAG_NAME, 'button')
                            button.click()
                            time.sleep(3)
                        
                        div_content = li.find_element(By.CLASS_NAME, 'accordion-panel-content')
        
                        section = div_content.find_element(By.TAG_NAME, 'section')
        
                        inner_divs = section.find_elements(By.TAG_NAME, 'div')
        
                        for idx, div in enumerate(inner_divs):
        
                            try:
                                anchor = div.find_element(By.TAG_NAME, 'a')
                                href = anchor.get_attribute('href')
                                total_links.append(href)
        
                            except Exception as e:
                                print(f"No anchor found in Div {idx + 1}: {e}")
                except Exception as e:
                    print(f"Could not click on this <li>: {e}")
            
            driver.quit()
                        
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("\n total_links", total_links)
        return total_links
    
def actual_paper_links(total_links):
    
    options = Options()
    #options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.headless = True
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    total_links_issues = []
    
    try:
        # Iterate over each link
        for index, link in enumerate(total_links):
            print(f"Opening link {index + 1}/{len(total_links)}: {link}")
    
            # Navigate to the link
            driver.get(link)
    
            # Optional: Wait for a specific element to load on the page
            try:
                if index == 0:
                    accept_cookies_button = WebDriverWait(driver, 30).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept all cookies')]"))
                    )
                    accept_cookies_button.click()
    
                # Wait for the `body` tag to load
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'body'))
                )
    
                # Locate the `ol` element containing the list of articles
                ol_element = driver.find_element(By.CSS_SELECTOR, '.js-article-list.article-list-items')
    
                # Get all `li` elements within this `ol`
                li_elements = ol_element.find_elements(By.TAG_NAME, 'li')
    
                # Process each `li` element
                for idx, li in enumerate(li_elements):
                    try:
                        # Locate the `dt` tag within the current `li`
                        dt_tag = li.find_element(By.TAG_NAME, 'dl')
    
                        # Locate the `dl` tag within the `dt`
                        dl_tag = dt_tag.find_element(By.TAG_NAME, 'dt')
    
                        # Locate the anchor tag within the `dl`
                        anchor = dl_tag.find_element(By.TAG_NAME, 'a')
    
                        # Get the `href` attribute of the anchor tag
                        href = anchor.get_attribute('href')
                        total_links_issues.append(href)
    
                    except Exception as e:
                        print(f"Error processing LI {idx + 1}: {e}")
    
    
            except Exception as e:
                print(f"Error loading {link}: {e}\n")
    
            time.sleep(random.uniform(2, 10))
    
    except Exception as e:
        print(f"An error occurred during iteration: {e}")
    
    finally:
        print("\n total_links_issues", total_links_issues)
        driver.quit()
        return total_links_issues
    
def filter_links(total_links_issues):
    filtered_links = []
    url = f"{os.getenv("DJANGO_URL", "http://127.0.0.1:8000")}/check-link"
    editor_url = f"{os.getenv("DJANGO_URL", "http://127.0.0.1:8000")}/check-editor-link"
    
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

def get_unique_link(filtered_links):
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

def get_scrapped_data(link):
    
    link_index = 0
    error_found = False
    editor_link = False
    title = None
    authors_emails = {}
    abstract = None
    obj = {}

    options = Options()
    #options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.headless = False  
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
        
    obj["link"] = link

    try:
        driver.get(link)
        accept_cookies_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept all cookies')]"))
        )
        accept_cookies_button.click()
    except Exception as e:
        pass

    try:
           # Locate the span containing the publication title
            publication_title_element = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.XPATH, "//h2[@class='publication-title u-h3']//span[@class='anchor-text']"))
            )
            publication_title = publication_title_element.text.strip()
            cleaned_title = publication_title.replace("Journal of", "").strip()
            obj["publication_title"] = cleaned_title
    except Exception as e:
        print("Publication Title Error:", str(e))
        error_found = True
        driver.quit()
        return error_found, editor_link, obj 
        
        
    try:
        title_element = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CLASS_NAME, "title-text"))
        )
        title = title_element.text.strip()
        obj["title"] = title
        if title == "Editorial Board":
            editor_link = True
            return error_found, editor_link, obj
    except Exception as e:
        print("Title Error:", str(e))
        error_found = True
        driver.quit()
        return error_found, editor_link, obj 
        
    try:
        abstract_element = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".abstract.author"))
        )
        abstract_html = abstract_element.get_attribute('innerHTML')
        soup = BeautifulSoup(abstract_html, 'html.parser')
        abstract = soup.get_text(separator='\n').strip()
        obj["abstract"] = abstract
    except Exception as e:
        print("Abstract Error:", str(e))
        driver.quit()
        editor_link = True
        return error_found, editor_link, obj
        
    try:
        main_div = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CLASS_NAME, "publication-volume.u-text-center"))
        )
    
        all_text = main_div.text
       
        date_pattern = r'\b(January|February|March|April|May|June|July|August|September|October|November|December) \d{4}\b'
        match = re.search(date_pattern, all_text)
        
        # Extract the date
        if match:
            date = match.group()
            obj["published_year"] = date
        else:
            error_found = True       
    
    except Exception as e:
        print("Published Year Error:", str(e))
        error_found = True
        driver.quit()
        return error_found, editor_link, obj 
        

    try:
        keywords_section = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CLASS_NAME, "keywords-section"))
        )
        inner_divs = keywords_section.find_elements(By.TAG_NAME, "div")
        keyword_list = []
        for div in inner_divs:
            keyword_list.append(div.text)
        keywords = ", ".join(keyword_list)
        obj["keywords"] = keywords            
    except Exception as e:
        print("Keywords Error")
        obj["keywords"] = "Not Found"   
        
    try:
       
        author_buttons = driver.find_elements(By.CSS_SELECTOR, ".author-group button")
        for button in author_buttons:
            author_name = button.text.strip()
            if not author_name:
                continue
            try:
                firstName = button.find_element(By.CSS_SELECTOR, ".given-name").text.strip()
                lastName = button.find_element(By.CSS_SELECTOR, ".text.surname").text.strip()
            except Exception as e:
                print("Exception in first and last name")
                firstName = button.find_element(By.CSS_SELECTOR, ".text.surname").text.strip()
                lastName = "Not Found"
                
            button.click()
            
            sidebar = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.CLASS_NAME, "side-panel-content"))
            )

            try:
                
                email_element = sidebar.find_element(By.CSS_SELECTOR, "div.e-address a")
                email = email_element.get_attribute("href").replace("mailto:", "").strip()
                authors_emails[firstName + "=" + lastName] = email
            except Exception as e:  
                print("Exception in sidebar")
                authors_emails[firstName + "=" + lastName] = "Not Found"
        
        obj["author_email"] = authors_emails
    except Exception as e:
        print("Author Email Error:", str(e))
        error_found = True   
        driver.quit()
        return error_found, editor_link, obj 
        
    
    if not authors_emails:
        error_found = True  
    elif abstract == None:
        error_found = True  

    driver.quit()
    return error_found, editor_link, obj 
    
    

def send_links_to_scrape(unique_links):
    url_add_paper = "http://127.0.0.1:8000/add-paper"
    url_insert_ignore = "http://127.0.0.1:8000/insert-ignored-links"
    url_insert_editor = f"{os.getenv("DJANGO_URL", "http://127.0.0.1:8000")}/insert-editor-links"
    
    data = []
    link_ignored = []
    
    for link_index, link in enumerate(unique_links, start=0):  # start=1 makes index 1-based
        print(f"Opening link {link_index}/{len(unique_links)}: {unique_links[link_index]}")
        
        start_time = time.time()
        
        error_found, editor_link, obj = get_scrapped_data(unique_links[link_index])
        
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
    
            #print(f"Link: {link}")
            #print(f"published_year: {obj["publication_title"]}")
            #print(f"published_year: {obj["published_year"]}, keywords: {obj["keywords"]}")
            #print(f"Title: {obj["title"]}")
            #print("Authors and their Emails:")
            #print(f"{obj["author_email"]}")
            #print("Abstract: ",obj["abstract"].split()[:50])
        print("\n")

    return data, link_ignored

def get_business_score(abstract_list):
    url = f"{os.getenv("DJANGO_URL", "http://127.0.0.1:8000")}/get-business-score"

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

def add_columns_score_justification_created_on(data, score_justification):
    data_frame = pd.DataFrame(data)
    today_str = date.today().strftime("%d %b %Y")  # e.g., '21 Mar 2025'

    data_frame["created on"] = today_str
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

def add_papers_to_db(updated_data):
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
