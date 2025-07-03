import os
import logging
import pandas as pd
import psycopg2
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Get database configuration from environment variables
db_config = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}

# A utility function to split long content into chunks with overlap
def split_content(content, chunk_size=3000, overlap=30):
    """
    Splits content into smaller chunks of specified size with overlap.
    
    Args:
    content (str): The content to be split.
    chunk_size (int): The size of each chunk.
    overlap (int): The overlap between consecutive chunks.

    Returns:
    list: A list of content chunks.
    """
    chunks = []
    start = 0
    while start < len(content):
        if start + chunk_size > len(content):
            chunks.append(content[start:])
        else:
            end = start + chunk_size
            if end + overlap < len(content):
                end += overlap
            chunks.append(content[start:end])
        start += chunk_size
    return chunks

# A utility function for logging errors
def log_error(message, exception, debug_mode=False):
    """
    Logs an error message with exception details.
    
    Args:
    message (str): The error message to log.
    exception (Exception): The exception object to log.
    debug_mode (bool): Whether to log the error in debug mode.
    """
    if debug_mode:
        logging.error(f"{message}: {exception}")
    else:
        print(f"{message}: {exception}")

def file_feedback(feedbacks):
    """
    Aggregates feedback from both KeywordGuard and LlamaGuard modules.

    Args:
    feedbacks (list): A list of feedback tuples from content chunks.

    Returns:
    tuple: A tuple containing overall safety (1 for safe, 0 for unsafe) and detected labels.
    """
    labels = {}
    overall_safe = 1  # Assume safe until proven otherwise

    for safe, classification in feedbacks:
        if safe != 1:
            overall_safe = 0
        
        # Check if classification is a dict
        if isinstance(classification, dict):
            for key, value in classification.items():
                labels[key] = value
        elif classification:
            labels[classification] = []  # Handle non-dict classifications

    # Create a formatted string for the labels, excluding empty lists
    formatted_labels = '<br>'.join(
        f"{key}: {value}" if value else key for key, value in labels.items()
    )

    # Return the overall safety and the formatted labels
    return overall_safe, formatted_labels


def get_keywords_from_db(db_config):
    """
    Fetches the keyword data from a PostgreSQL database.

    Args:
    db_config (dict): A dictionary containing PostgreSQL connection details.

    Returns:
    pd.DataFrame: A DataFrame containing the keyword data.
    """
    try:
        conn = psycopg2.connect(
            dbname=db_config['dbname'],
            user=db_config['user'],
            password=db_config['password'],
            host=db_config['host'],
            port=db_config['port']
        )
        query = """
        SELECT id, created_time, label, keyword, created_by FROM keywords;
        """  # Replace with your actual table name
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Error fetching data from PostgreSQL: {e}")
        return None

