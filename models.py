from sqlalchemy import Table, Boolean, Column, ForeignKey, Integer, String, DateTime, Float, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

paper_authors = Table(
    "paper_authors",
    Base.metadata,
    Column("id_paper", Integer, ForeignKey("papers.id"), primary_key=True),
    Column("id_author", Integer, ForeignKey("authors.id"), primary_key=True),
)

class Author(Base):
    __tablename__ = "authors"

    id = Column(Integer, primary_key=True, index=True)
    firstname = Column(String, nullable=False)
    lastname = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    papers = relationship("Paper", secondary=paper_authors, back_populates="authors")


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    abstract = Column(Text, nullable=True)
    source = Column(String, nullable=True)  
    pdf = Column(String, nullable=True)  
    journal = Column(String, nullable=True)
    publication_year = Column(String, nullable=True)
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False)
    email = Column(String, nullable=True)  # Add email field

    # Relationship to BusinessScore
    authors = relationship("Author", secondary=paper_authors, back_populates="papers")
    business_scores = relationship("BusinessScore", back_populates="paper")
    keywords = relationship("Keyword", back_populates="paper")


class BusinessScore(Base):
    __tablename__ = "business_scores"

    id = Column(Integer, primary_key=True, index=True)
    id_paper = Column(Integer, ForeignKey("papers.id"), nullable=False)
    business_score = Column(Float, nullable=True)  
    business_score_adjusted = Column(Float, nullable=True)  
    business_score_justification = Column(Text, nullable=True)  

    paper = relationship("Paper", back_populates="business_scores")

class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True)
    id_paper = Column(Integer, ForeignKey("papers.id"), nullable=False)
    keyword = Column(String, nullable=False)

    paper = relationship("Paper", back_populates="keywords")

class EditorPaper(Base):
    __tablename__ = "editor_papers"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=True)

class IgnoredLink(Base):
    __tablename__ = "ignored_links"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=True)

class Newsletter(Base):
    __tablename__ = "newsletters"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, unique=True)
    subscribed_on = Column(DateTime, default=datetime.utcnow, nullable=False)

class Waitlist(Base):
    __tablename__ = "waitlist"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, unique=True)
    joined_on = Column(DateTime, default=datetime.utcnow, nullable=False)