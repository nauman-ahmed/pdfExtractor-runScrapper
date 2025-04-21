from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from openai import OpenAI
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import pandas as pd
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated
from datetime import datetime
import models
from database import SessionLocal, Base, engine
from models import Author, Paper, Keyword, BusinessScore, EditorPaper, IgnoredLink, Newsletter, Waitlist
from schemas import AuthorBase, PaperBase, BusinessScoreBase, KeywordBase, BusinessScoreUpdate, KeywordUpdate
import json
import shutil
import os
import fitz
from datetime import date
from pydantic import BaseModel
from dotenv import load_dotenv

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Add your frontend URL here
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Load environment variables from .env file
load_dotenv()

# Retrieve OpenAI API key from environment variable
api_key = os.getenv("OPENAI_API_KEY")
print("🔍 OPENAI_API_KEY =", os.getenv("OPENAI_API_KEY"))
if not api_key:
    raise ValueError("OpenAI API key not found. Please set it in the .env file.")

client = OpenAI(
    api_key=api_key, 
)





#Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]




def insert_authors_from_dataframe(db):
    # This function will insert the data from client's provided csv
    
    today_date = datetime.now()
    formatted_date = today_date.strftime("%d %b %Y")
    # Read the Excel file
    authors_df = pd.read_excel("/Users/naumanahmed/Desktop/Uploaded_files/Summarized.xlsx")
    # Rename columns to match Author model fields
    authors_df.columns = ['firstname', 'lastname', 'email']

    # Create a database session
    db: Session = SessionLocal()
    try:
        for _, row in authors_df.iterrows():
            # Check if the author already exists
            print("Starting 1")
            existing_author = db.query(models.Author).filter(Author.email == row['email']).first()
            print("Starting 2")
            if not existing_author:
                # Create and add a new Author
                new_author = Author(
                    firstname=row['firstname'],
                    lastname=row['lastname'],
                    email=row['email']
                )
                db.add(new_author)

        # Commit the transaction
        db.commit()
        print("Authors inserted successfully!")
    except Exception as e:
        # Rollback in case of any error
        db.rollback()
        print(f"An error occurred: {e}")
    finally:
        # Close the session
        db.close()

#insert_authors_from_dataframe(db_dependency)

def get_papers_score_Open_AI(abstract_texts):
    result = []
    abstract_to_consider = 5  # Maximum abstracts per batch
    count = 0
    all_abstracts_json = {"abstracts": []}  # Single dictionary to store results

    prompt_template = """
        Evaluate the following abstracts and provide a JSON response with a score from 1 to 10 and a short justification. 
        The score should follow a bell curve distribution and should be based on the practical value and impact on European early-stage ventures, especially startups.

        Expected JSON Output Format:
        { "abstracts": [ { "abstract_id": 1, "score": <integer>, "justification": "<justification_text>" }, { "abstract_id": 2, "score": <integer>, "justification": "<justification_text>" } ] }
        Ensure the JSON is properly formatted **without additional text**.
        \n\n
    """

    prompt = prompt_template

    for idx, abstract in enumerate(abstract_texts):
        prompt += f"Abstract {idx + 1}: {abstract}\n\n"
        count += 1

        if count == abstract_to_consider:  # Process in batches of 5 abstracts
            print("Processing batch...\n", prompt)  # Debugging output
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.choices[0].message.content

            try:
                batch_results = json.loads(response_text)  # Convert response to JSON
                all_abstracts_json["abstracts"].extend(batch_results["abstracts"])  # Append results
            except json.JSONDecodeError:
                print("Error: Model returned invalid JSON. Debug response:\n", response_text)

            # Reset for the next batch
            prompt = prompt_template
            count = 0  

    # Process remaining abstracts (if fewer than 5 remain)
    if count > 0:
        print("Processing final batch...\n", prompt)

        response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.choices[0].message.content

        try:
            batch_results = json.loads(response_text)
            all_abstracts_json["abstracts"].extend(batch_results["abstracts"])
        except json.JSONDecodeError:
            print("Error: Model returned invalid JSON. Debug response:\n", response_text)

    # Convert all results into a **single JSON object**
    json_output = json.dumps(all_abstracts_json, indent=4)

    return json_output

def get_papers_without_business_scores(db):
    # This function is responsible for getting all the papers which has no business score
    
    db: Session = SessionLocal()
    papers_without_scores = (
        db.query(Paper)
        .outerjoin(BusinessScore, Paper.id == BusinessScore.id_paper)
        .filter(BusinessScore.id == None)  
        .all()
    )

    abstract_list = [
        {
            'abstract': paper.abstract
        }
        for paper in papers_without_scores
    ]

    link_list = [
        {
            'link': paper.source
        }
        for paper in papers_without_scores
    ]

    for i in link_list[0: 10]:
        print(f"Link: {i['link']}")

    return get_papers_score_Open_AI(abstract_list[0: 10])


# print(get_papers_without_business_scores(db_dependency))

# @app.post("/insert-ignored-links", response_model=dict)
# def add_ignored_link(link: str, db: db_dependency):
#     # Check if the link already exists
#     existing_link = db.query(IgnoredLink).filter(IgnoredLink.source == link).first()
    
#     if existing_link:
#         raise HTTPException(status_code=400, detail="This link is already ignored.")

#     # Create a new entry
#     new_link = IgnoredLink(source=link)
#     db.add(new_link)
#     db.commit()
#     db.refresh(new_link)

#     return {"message": "Link added to ignored list", "source": new_link.source}

# @app.get("/get-ignored-links")
# def ignored_links(db: db_dependency):
  
#     links = db.query(IgnoredLink).all()
#     return {"ignored_links": [link.source for link in links]}




## This route will be used to take pdf file, and process it and get stored in the db

def add_paper_from_pdf(paper_data: dict, db):
    try:

        title = paper_data.get("title")
        abstract = paper_data.get("abstract")
        author_email = paper_data.get("author_email", {})
        source = paper_data.get("link")
        keywords = paper_data.get("keywords", [])  
        publication_year = paper_data.get("published_year", " ")  
        created_on = paper_data.get("created_on", " ")  
        journal = paper_data.get("publication_title", " ")  
        business_score = float(paper_data.get("business_score", 0))
        business_score_justification = paper_data.get("business_score_justification", " ")
        email = paper_data.get("email")  # Get email from paper_data
        print("Created On", created_on)
        existing_paper = db.query(Paper).filter(Paper.title == title).first()
        if existing_paper:
            raise HTTPException(status_code=400, detail="Paper already exists.")
        
        new_paper = Paper(
            title=title,
            abstract=abstract,
            source=source,
            publication_year= publication_year,
            journal= journal,
            created_on = created_on,
            email=email  # Save email in the Paper model
        )
        db.add(new_paper)
        db.flush()  

        for fullname, email in author_email.items():
            if email == "Not Found":
                continue
            
            firstname, lastname = fullname.split("=")
            author = db.query(Author).filter_by(email=email).first()
            if not author:
                author = Author(firstname=firstname, lastname=lastname, email=email, created_on = created_on)
                db.add(author)
                db.flush()
            new_paper.authors.append(author)

        for keyword in keywords:
            if keyword.strip():  
                keyword_obj = Keyword(id_paper=new_paper.id, keyword=keyword.strip())
                db.add(keyword_obj)
        
        if business_score is not None or business_score_justification is not None:
            business_score_entry = BusinessScore(
                id_paper=new_paper.id,
                business_score=business_score if business_score is not None else None,
                business_score_justification=business_score_justification if business_score_justification is not None else None
            )
            db.add(business_score_entry)

        db.commit()
        paper_id = new_paper.id
        author_ids = [author.id for author in new_paper.authors]
        return {
            "message": "Paper and related entities added successfully.",
            "paper_id": paper_id,
            "author_ids": author_ids
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

def extract_single_paper_metadata_OpenAI(paper_text):

    prompt = """
You are a highly accurate academic metadata extractor.

Extract and return the following from the academic article text in proper JSON format.

Required fields:
- paper_title: string
- abstract: string (must be the full original abstract text, verbatim as written in the article)
- journal_name: string
- publication_year: string
- keywords: list of strings (if none found, return ["Not Found"])
- authors: list of objects, each with:
    - firstname: string null 
    - lastname: string or null
    - email: string or null

JSON Example:
{
  "paper_title": "...",
  "abstract": "...",
  "journal_name": "...",
  "publication_year": "March 2025",
  "keywords": ["..."] or ["Not Found"],
  "authors": [
    {
      "firstname": "Alice",
      "lastname": "Johnson",
      "email": "alice@example.com"
    },
    {
      "firstname": "Bob",
      "lastname": "Smith",
      "email": "Not Found"
    },
    {
      "firstname": "Not Found",
      "lastname": "Johnson nau",
      "email": "alice_nau@example.com"
    },
    {
      "firstname": "Bob ahm",
      "lastname": "Not Found",
      "email": "bob_ahm@example.com"
    },
  ]
}

Only return valid JSON. Do not include extra text.

Here is the paper text:
\"\"\"%s\"\"\"
""" % paper_text

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = response.choices[0].message.content

        metadata = json.loads(response_text)

        # Ensure 'keywords' is a non-empty list
        if not isinstance(metadata.get("keywords"), list) or not metadata["keywords"]:
            metadata["keywords"] = ["Not Found"]

        return metadata

    except json.JSONDecodeError:
        print("Error: OpenAI returned invalid JSON. Raw response:\n", response_text)
        return None

def extract_text_from_first_page(file_path: str) -> str:
    try:
        with fitz.open(file_path) as doc:
            if doc.page_count > 0:
                first_page = doc.load_page(0)  # 0-based index
                return first_page.get_text()
            else:
                return ""
    except Exception as e:
        print(f"Error while extracting text from PDF: {e}")
        return ""

@app.get("/")
def root():
    return {
        "message": "PDFExtractor API is live!",
        "status": "ok",
        "endpoints": [
            "/upload-pdf/",
            "/add-paper",
            "/get-business-score",
            "/authors/",
            "/papers/",
            "/newsletter/subscribe",
            "/waitlist/subscribe"
        ]
    }


@app.post("/upload-pdf/")
async def upload_pdf(
    file: UploadFile = File(...), 
    email: str = Form(...),  # Accept email as a form field
    db: Session = Depends(get_db)
):
    today_str = date.today().strftime("%d %b %Y")

    # Check if the uploaded file is a PDF
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    
    # Save the file
    upload_dir = "uploaded_files"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    text = extract_text_from_first_page(file_path)

    paper_json_data = extract_single_paper_metadata_OpenAI(text)
    business_dic = json.loads(get_papers_score_Open_AI([paper_json_data.get("abstract")]))

    business_dic_abstract = business_dic.get("abstracts")
    author_email_dict = {}

    for author in paper_json_data.get("authors"):
        firstname = author.get("firstname") or "Unknown"  # Default to "Unknown" if None
        lastname = author.get("lastname") or "Unknown"    # Default to "Unknown" if None
        key = firstname + "=" + lastname
        author_email = author.get("email") or "Not Found"  # Use "Not Found" if email is None
        author_email_dict[key] = author_email

    combined = {
        "link": file_path,
        "title": paper_json_data.get("paper_title"),
        "author_email": author_email_dict,
        "abstract": paper_json_data.get("abstract"),
        "published_year": paper_json_data.get("publication_year", ""),
        "keywords": paper_json_data.get("keywords", []),
        "publication_title": paper_json_data.get("journal_name", ""),
        "created_on": today_str,  
        "business_score": business_dic_abstract[0]["score"],
        "business_score_justification": business_dic_abstract[0]["justification"],
        "email": email  # Include email in the combined data
    }

    added_paper_response = add_paper_from_pdf(combined, db)

    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "email": email,  # Ensure this remains unchanged
        "message": "PDF uploaded successfully.",
        "saved_path": file_path,
        "pdf_text": text,
        "json": paper_json_data,
        "business_dic": business_dic,
        "combined_data": combined,
        "added_paper_response": added_paper_response
    }

## END HERE



## From here, these endpoints are being used in the scrapper

@app.get("/insert-editor-links")
def add_editor_link(link: str, db: db_dependency):
    # Check if the link already exists
    existing_link = db.query(IgnoredLink).filter(IgnoredLink.source == link).first()
    
    if existing_link:
        raise HTTPException(status_code=400, detail="This link is already ignored.")

    # Create a new entry
    new_link = IgnoredLink(source=link)
    db.add(new_link)
    db.commit()
    db.refresh(new_link)

    return {"message": "Link added to ignored list", "source": new_link.source}

@app.get("/check-editor-link")
def check_link(link: str, db: db_dependency):
    
    paper = db.query(IgnoredLink).filter(IgnoredLink.source == link).first()
    return {"exists": paper is not None}


@app.get("/check-link")
def check_link(link: str, db: db_dependency):
    
    paper = db.query(Paper).filter(Paper.source == link).first()
    return {"exists": paper is not None}

@app.post("/get-business-score")
def getBusinessScore(data: dict):
    return get_papers_score_Open_AI(data.get("abstract"))

@app.post("/add-paper")
def add_paper(paper_data: dict, db: db_dependency):
    try:

        title = paper_data.get("title")
        abstract = paper_data.get("abstract")
        author_email = paper_data.get("author_email", {})
        source = paper_data.get("link")
        keywords = paper_data.get("keywords", [])  
        publication_year = paper_data.get("published_year", " ")  
        created_on = paper_data.get("created_on", " ")  
        journal = paper_data.get("publication_title", " ")  
        business_score = float(paper_data.get("business_score", 0))
        business_score_justification = paper_data.get("business_score_justification", " ")

        print("Created On", created_on)
        existing_paper = db.query(Paper).filter(Paper.title == title).first()
        if existing_paper:
            raise HTTPException(status_code=400, detail="Paper already exists.")
        
        new_paper = Paper(
            title=title,
            abstract=abstract,
            source=source,
            publication_year= publication_year,
            journal= journal,
            created_on = created_on
        )
        db.add(new_paper)
        db.flush()  

        for fullname, email in author_email.items():
            if email == "Not Found":
                continue
            
            firstname, lastname = fullname.split("=")
            author = db.query(Author).filter_by(email=email).first()
            if not author:
                author = Author(firstname=firstname, lastname=lastname, email=email, created_on = created_on)
                db.add(author)
                db.flush()
            new_paper.authors.append(author)

        for keyword in keywords:
            if keyword.strip():  
                keyword_obj = Keyword(id_paper=new_paper.id, keyword=keyword.strip())
                db.add(keyword_obj)
        
        if business_score is not None or business_score_justification is not None:
            business_score_entry = BusinessScore(
                id_paper=new_paper.id,
                business_score=business_score if business_score is not None else None,
                business_score_justification=business_score_justification if business_score_justification is not None else None
            )
            db.add(business_score_entry)

        db.commit()
        paper_id = new_paper.id
        author_ids = [author.id for author in new_paper.authors]
        return {
            "message": "Paper and related entities added successfully.",
            "paper_id": paper_id,
            "author_ids": author_ids
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

##### END #####










## These four endpoints below are being used for manual insertion starts here

@app.post("/authors/")
async def create_author(author: AuthorBase, db: db_dependency):
    existing_author = db.query(models.Author).filter(models.Author.email == author.email).first()
    if existing_author:
        raise HTTPException(status_code=400, detail="Author with this email already exists.")

    db_author = models.Author(
        firstname=author.firstname,
        lastname=author.lastname,
        email=author.email
    )
    db.add(db_author)
    db.commit()
    db.refresh(db_author)
    
    return {
        "message": "Author added successfully",
        "author_id": db_author.id,
        "author": {
            "firstname": db_author.firstname,
            "lastname": db_author.lastname,
            "email": db_author.email
        }
    }

@app.post("/papers/")
async def create_paper(paper: PaperBase, db: db_dependency):
    authors = db.query(models.Author).filter(models.Author.id.in_(paper.author_ids)).all()
    if len(authors) != len(paper.author_ids):
        raise HTTPException(status_code=400, detail="One or more authors do not exist.")

    db_paper = models.Paper(
        title=paper.title,
        abstract=paper.abstract,
        source=paper.source,
        #pdf=paper.pdf,
        journal=paper.journal,
        publication_year=paper.publication_year,
    )
    db_paper.authors = authors
    db.add(db_paper)
    db.commit()
    db.refresh(db_paper)

    return {
        "message": "Paper added successfully",
        "paper_id": db_paper.id,
        "paper": {
            "title": db_paper.title,
            "source": db_paper.source,
            "publication_year": db_paper.publication_year
        }
    }

@app.post("/business-scores/")
async def create_business_score(business_score: BusinessScoreBase, db: db_dependency):
    paper = db.query(models.Paper).filter(models.Paper.id == business_score.id_paper).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")

    db_score = models.BusinessScore(
        id_paper=business_score.id_paper,
        business_score=business_score.business_score,
        business_score_adjusted=business_score.business_score_adjusted,
        business_score_justification=business_score.business_score_justification,
    )
    db.add(db_score)
    db.commit()
    db.refresh(db_score)
    
    return {"message": "Business score added successfully", "business_score": business_score}

@app.post("/keywords/")
async def create_keywords(keyword_data: KeywordBase, db: db_dependency):
    paper = db.query(models.Paper).filter(models.Paper.id == keyword_data.id_paper).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")

    inserted_keywords = []
    for kw in keyword_data.keywords:
        if kw.strip():  # Skip empty strings
            db_keyword = models.Keyword(
                id_paper=keyword_data.id_paper,
                keyword=kw.strip()
            )
            db.add(db_keyword)
            inserted_keywords.append(kw.strip())

    db.commit()
    
    return {
        "message": f"{len(inserted_keywords)} keyword(s) added successfully",
        "keywords": inserted_keywords
    }
    

##### END #####






## These endpoints are being used for updatation of business score and keywords

@app.put("/papers/{paper_id}/business-score", response_model=dict)
def update_business_score(paper_id: int, score_data: BusinessScoreUpdate, db: Session = Depends(get_db)):
    business_score = db.query(BusinessScore).filter(BusinessScore.id_paper == paper_id).first()

    if not business_score:
        raise HTTPException(status_code=404, detail="Business score not found for this paper")

    for field, value in score_data.dict(exclude_unset=True).items():
        setattr(business_score, field, value)

    db.commit()
    return {"message": "Business score updated successfully"}

@app.put("/papers/{paper_id}/keywords", response_model=dict)
def update_keywords(paper_id: int, keyword_data: KeywordUpdate, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    # Delete existing keywords
    db.query(Keyword).filter(Keyword.id_paper == paper_id).delete()

    # Add new keywords
    for kw in keyword_data.keywords:
        new_keyword = Keyword(id_paper=paper_id, keyword=kw)
        db.add(new_keyword)

    db.commit()
    return {"message": "Keywords updated successfully"}

##### END #####







## These endpoints are being used for getting details

@app.get("/authors/{author_id}/papers")
def get_papers_by_author(author_id: int, db: db_dependency):
    author = db.query(models.Author).filter(models.Author.id == author_id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found.")
    return author.papers

@app.get("/papers/{paper_id}/authors")
def get_authors_by_paper(paper_id: int, db: db_dependency):
    paper = db.query(models.Paper).filter(models.Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    return paper.authors

@app.get("/papers/{paper_id}/business-scores")
def get_business_scores_by_paper(paper_id: int, db: db_dependency):
    paper = db.query(models.Paper).filter(models.Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    
    scores = db.query(models.BusinessScore).filter(models.BusinessScore.id_paper == paper_id).all()
    return scores

@app.get("/papers/{paper_id}/keywords")
def get_keywords_by_paper(paper_id: int, db: db_dependency):
    paper = db.query(models.Paper).filter(models.Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    
    keywords = db.query(models.Keyword).filter(models.Keyword.id_paper == paper_id).all()
    return keywords


##### END #####


@app.get("/export-papers", response_model=list)
def export_papers(db: db_dependency):
    papers = db.query(Paper).all()
    export_data = []

    for paper in papers:
        # Flatten keywords into a comma-separated string
        keywords = ", ".join([kw.keyword for kw in paper.keywords])

        # Format authors as: First=Last: email; ...
        author_email_list = []
        for author in paper.authors:
            key = f"{author.firstname}={author.lastname}"
            email = author.email or "Not Found"
            author_email_list.append(f"{key}: {email}")
        author_email_str = "; ".join(author_email_list)

        # Business score
        business_score_obj = (
            db.query(BusinessScore).filter(BusinessScore.id_paper == paper.id).first()
        )

        export_data.append({
            "link": paper.source,
            "title": paper.title,
            "author_email": author_email_str,
            "abstract": paper.abstract,
            "published_year": paper.publication_year,
            "keywords": keywords,
            "publication_title": paper.journal,
            "created_on": paper.created_on,
            "business_score": business_score_obj.business_score if business_score_obj else None,
            "business_score_justification": business_score_obj.business_score_justification if business_score_obj else None,
        })

    return export_data


class NewsletterSubscription(BaseModel):
    email: str

@app.post("/newsletter/subscribe")
def subscribe_to_newsletter(subscription: NewsletterSubscription, db: Session = Depends(get_db)):
    email = subscription.email  # Extract email from the request body
    # Check if email already exists
    existing_subscription = db.query(Newsletter).filter(Newsletter.email == email).first()
    if existing_subscription:
        raise HTTPException(status_code=400, detail="Email is already subscribed.")

    # Add new subscription
    new_subscription = Newsletter(email=email)
    db.add(new_subscription)
    db.commit()
    db.refresh(new_subscription)
    return {"message": "Subscription successful", "email": new_subscription.email}

class WaitlistSubscription(BaseModel):
    email: str
 
@app.post("/waitlist/subscribe")
def subscribe_to_waitlist(subscription: WaitlistSubscription, db: Session = Depends(get_db)):
    email = subscription.email  # Extract email from the request body
    # Check if email already exists
    existing_entry = db.query(models.Waitlist).filter(models.Waitlist.email == email).first()
    if existing_entry:
        raise HTTPException(status_code=400, detail="Email is already on the waitlist.")

    # Add new waitlist entry
    new_entry = models.Waitlist(email=email)
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return {"message": "Successfully added to the waitlist", "email": new_entry.email}

@app.get("/waitlist/check")
def check_waitlist(email: str, db: Session = Depends(get_db)):
    # Check if the email exists in the waitlist
    existing_entry = db.query(models.Waitlist).filter(models.Waitlist.email == email).first()
    return {"exists": existing_entry is not None}