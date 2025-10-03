import requests
from dotenv import load_dotenv
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, Table, MetaData, Column, Integer, String
from pgvector.sqlalchemy import Vector
import os
load_dotenv()

url = "https://api.venice.ai/api/v1/embeddings"

def embed_text(text):
    payload = {
        "encoding_format": "float",
        "input": text,
        "model": "text-embedding-bge-m3"
    }
    headers = {
        "Authorization": f"Bearer {os.environ['VENICE_API_KEY']}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)
    response = np.array(response.json()['data'][0]['embedding'])
    return response


# 1. MUST install: pip install pgvector sqlalchemy
engine = create_engine("postgresql://cshowley@localhost/conversations")

# 2. Proper table definition using pgvector's native type
metadata = MetaData()
mother_brain = Table(
    'mother_brain',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', String),
    Column('conversation_thread_topic', String),
    Column('conversation_thread_summary', String),
    Column('conversation_thread_topic_embedding', Vector(1024)),  # SPECIFY DIMENSIONS!
    Column('conversation_thread_summary_embedding', Vector(1024))
)

# Upload row to database (using numpy arrays)
with engine.connect() as conn:
    conversation_thread_topic = "Test topic"
    conversation_thread_summary = "Test summary"
    
    conn.execute(
        mother_brain.insert(),
        {
            'user_id': 'test_user',
            'conversation_thread_topic': conversation_thread_topic,
            'conversation_thread_summary': conversation_thread_summary,
            'conversation_thread_topic_embedding': embed_text(conversation_thread_topic),
            'conversation_thread_summary_embedding': embed_text(conversation_thread_summary)
        }
    )
    conn.commit()

# Upload multiple rows
with engine.connect() as conn:
    # Prepare ALL data BEFORE database interaction
    rows_to_insert = []
    topics_and_summaries = [
        ("Test topic 1", "Test summary 1"),
        ("Test topic 2", "Test summary 2"),
        ("Test topic 3", "Test summary 3")
        # Add as many as needed
    ]
    
    for topic, summary in topics_and_summaries:
        rows_to_insert.append({
            'user_id': 'test_user',
            'conversation_thread_topic': topic,
            'conversation_thread_summary': summary,
            'conversation_thread_topic_embedding': embed_text(topic).tolist(),  # Critical: convert to list
            'conversation_thread_summary_embedding': embed_text(summary).tolist()
        })
    
    # SINGLE database command for ALL rows
    conn.execute(
        mother_brain.insert(),
        rows_to_insert  # Pass entire list here
    )
    conn.commit()  # Commit once for all inserts

# 4. RETRIEVE a single result (gets numpy arrays)
with engine.connect() as conn:
    result = conn.execute(mother_brain.select().limit(1)).fetchone()
    print(type(result.conversation_thread_topic_embedding))  # <class 'numpy.ndarray'>
    print(result.conversation_thread_topic_embedding.shape)   # (1024,)

# 5. RETRIEVE all results and write to dataframe
with engine.connect() as conn:
    result = pd.DataFrame(conn.execute(mother_brain.select()).fetchall())

# 6. Filtering example; return results where primary key `id` <= 7
with engine.connect() as conn:
    result = conn.execute(
        mother_brain.select().where(mother_brain.c.id <= 7)
    ).fetchall()

# 7. Vector similarity search example
from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pgvector.sqlalchemy import Vector

Base = declarative_base()

class MotherBrain(Base):
    __tablename__ = 'mother_brain'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    conversation_thread_topic = Column(String)
    conversation_thread_summary = Column(String)
    conversation_thread_topic_embedding = Column(Vector(1024))  # Proper vector type
    conversation_thread_summary_embedding = Column(Vector(1024))  # Proper vector type

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from pgvector.sqlalchemy import Vector
import numpy as np

# Connect to database (replace with your credentials)
engine = create_engine("postgresql+psycopg2://user:password@localhost/dbname")
Session = sessionmaker(bind=engine)
session = Session()

query_vector = np.array([0.1] * 1024)  # Must match dimension size (1024)

results = session.query(
    MotherBrain.user_id,
    MotherBrain.conversation_thread_topic,
    MotherBrain.conversation_thread_topic_embedding.cosine_distance(query_vector).label('distance')
).order_by('distance').limit(5).all()

# Print results
for r in results:
    print(f"User: {r.user_id}, Topic: {r.conversation_thread_topic}, Distance: {r.distance}")
