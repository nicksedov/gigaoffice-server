"""
Example usage of the prompt_examples knowledge base table

This script demonstrates how to query and retrieve examples from
the knowledge base table after it has been populated.
"""
import os
import psycopg2
import json
from typing import List, Dict, Any, Optional

# Database configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "gigaoffice")
DB_USER = os.getenv("DB_USER", "gigaoffice")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_SCHEMA = os.getenv("DB_SCHEMA", "")


def get_db_connection():
    """Create and return a database connection"""
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )


def get_examples_by_category(category: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieve examples by category
    
    Args:
        category: Category name (e.g., 'spreadsheet-generation')
        limit: Maximum number of examples to return
        
    Returns:
        List of example dictionaries
    """
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cur:
            if DB_SCHEMA:
                cur.execute(f"SET search_path TO {DB_SCHEMA};")
            
            cur.execute("""
                SELECT id, category, prompt_text, request_json, response_json, 
                       language, source_file, created_at
                FROM prompt_examples
                WHERE category = %s
                ORDER BY id
                LIMIT %s
            """, (category, limit))
            
            results = []
            for row in cur.fetchall():
                results.append({
                    'id': row[0],
                    'category': row[1],
                    'prompt_text': row[2],
                    'request_json': row[3],
                    'response_json': row[4],
                    'language': row[5],
                    'source_file': row[6],
                    'created_at': row[7]
                })
            
            return results
    finally:
        conn.close()


def search_by_text(search_term: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search examples by text in lemmatized prompt
    
    Args:
        search_term: Search term
        limit: Maximum number of results
        
    Returns:
        List of matching examples
    """
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cur:
            if DB_SCHEMA:
                cur.execute(f"SET search_path TO {DB_SCHEMA};")
            
            cur.execute("""
                SELECT id, category, prompt_text, language, source_file
                FROM prompt_examples
                WHERE lemmatized_prompt ILIKE %s
                ORDER BY id
                LIMIT %s
            """, (f'%{search_term}%', limit))
            
            results = []
            for row in cur.fetchall():
                results.append({
                    'id': row[0],
                    'category': row[1],
                    'prompt_text': row[2],
                    'language': row[3],
                    'source_file': row[4]
                })
            
            return results
    finally:
        conn.close()


def get_statistics() -> Dict[str, Any]:
    """
    Get statistics about the knowledge base
    
    Returns:
        Dictionary with statistics
    """
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cur:
            if DB_SCHEMA:
                cur.execute(f"SET search_path TO {DB_SCHEMA};")
            
            # Total count
            cur.execute("SELECT COUNT(*) FROM prompt_examples")
            result = cur.fetchone()
            total = result[0] if result else 0
            
            # By category
            cur.execute("""
                SELECT category, COUNT(*) 
                FROM prompt_examples 
                GROUP BY category 
                ORDER BY category
            """)
            by_category = {row[0]: row[1] for row in cur.fetchall()}
            
            # By language
            cur.execute("""
                SELECT language, COUNT(*) 
                FROM prompt_examples 
                GROUP BY language
            """)
            by_language = {row[0]: row[1] for row in cur.fetchall()}
            
            # With/without request
            cur.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE request_json IS NOT NULL) as with_request,
                    COUNT(*) FILTER (WHERE request_json IS NULL) as without_request
                FROM prompt_examples
            """)
            req_stats = cur.fetchone()
            with_req = req_stats[0] if req_stats else 0
            without_req = req_stats[1] if req_stats else 0
            
            return {
                'total_examples': total,
                'by_category': by_category,
                'by_language': by_language,
                'with_request': with_req,
                'without_request': without_req
            }
    finally:
        conn.close()


def get_example_by_id(example_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve a single example by ID
    
    Args:
        example_id: Example ID
        
    Returns:
        Example dictionary or None if not found
    """
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cur:
            if DB_SCHEMA:
                cur.execute(f"SET search_path TO {DB_SCHEMA};")
            
            cur.execute("""
                SELECT id, category, prompt_text, lemmatized_prompt, 
                       request_json, response_json, language, source_file, created_at
                FROM prompt_examples
                WHERE id = %s
            """, (example_id,))
            
            row = cur.fetchone()
            if not row:
                return None
            
            return {
                'id': row[0],
                'category': row[1],
                'prompt_text': row[2],
                'lemmatized_prompt': row[3],
                'request_json': row[4],
                'response_json': row[5],
                'language': row[6],
                'source_file': row[7],
                'created_at': row[8]
            }
    finally:
        conn.close()


def main():
    """Demo usage of the query functions"""
    print("="*60)
    print("Prompt Examples Knowledge Base - Query Examples")
    print("="*60)
    
    # Get statistics
    print("\n1. Knowledge Base Statistics")
    print("-"*60)
    try:
        stats = get_statistics()
        print(f"Total examples: {stats['total_examples']}")
        print(f"\nBy category:")
        for category, count in stats['by_category'].items():
            print(f"  {category}: {count}")
        print(f"\nBy language:")
        for lang, count in stats['by_language'].items():
            print(f"  {lang}: {count}")
        print(f"\nWith request data: {stats['with_request']}")
        print(f"Without request data: {stats['without_request']}")
    except Exception as e:
        print(f"Error getting statistics: {e}")
    
    # Get examples by category
    print("\n2. Examples from 'spreadsheet-generation' category")
    print("-"*60)
    try:
        examples = get_examples_by_category('spreadsheet-generation', limit=3)
        for i, ex in enumerate(examples, 1):
            print(f"\nExample {i}:")
            print(f"  ID: {ex['id']}")
            print(f"  Prompt: {ex['prompt_text'][:60]}...")
            print(f"  Language: {ex['language']}")
            print(f"  Source: {ex['source_file']}")
    except Exception as e:
        print(f"Error getting examples: {e}")
    
    # Search by text
    print("\n3. Search for examples containing 'таблица'")
    print("-"*60)
    try:
        results = search_by_text('таблица', limit=3)
        for i, result in enumerate(results, 1):
            print(f"\nResult {i}:")
            print(f"  Category: {result['category']}")
            print(f"  Prompt: {result['prompt_text'][:60]}...")
    except Exception as e:
        print(f"Error searching: {e}")
    
    # Get specific example
    print("\n4. Get example by ID (ID=1)")
    print("-"*60)
    try:
        example = get_example_by_id(1)
        if example:
            print(f"Category: {example['category']}")
            print(f"Prompt: {example['prompt_text']}")
            print(f"Language: {example['language']}")
            print(f"Has request: {example['request_json'] is not None}")
            print(f"Response keys: {list(example['response_json'].keys())}")
        else:
            print("Example not found")
    except Exception as e:
        print(f"Error getting example: {e}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
