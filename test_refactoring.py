"""
Test script to verify the prompt examples loading refactoring.
Tests both classification and categorized prompt search services.
"""
import sys
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stdout, level="INFO")

from app.services.database.vector_search import (
    classification_prompt_search,
    categorized_prompt_search
)

def test_classification_examples():
    """Test loading classification examples"""
    logger.info("=" * 60)
    logger.info("Testing Classification Prompt Search")
    logger.info("=" * 60)
    
    query = "Найди минимальное значение"
    
    try:
        examples = classification_prompt_search.search_examples(
            query=query,
            search_mode="fulltext",
            limit=3
        )
        
        logger.info(f"Query: {query}")
        logger.info(f"Found {len(examples)} examples")
        
        for i, example in enumerate(examples, 1):
            logger.info(f"\nExample {i}:")
            logger.info(f"  Task: {example['task'][:80]}...")
            logger.info(f"  Has request_table: {len(example['request_table']) > 0}")
            logger.info(f"  Has response_table: {len(example['response_table']) > 0}")
        
        return len(examples) > 0
    except Exception as e:
        logger.error(f"Error testing classification examples: {e}")
        return False

def test_categorized_examples():
    """Test loading categorized examples for various categories"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Categorized Prompt Search")
    logger.info("=" * 60)
    
    test_cases = [
        ("spreadsheet-analysis", "Посчитай среднюю зарплату"),
        ("data-chart", "Построй график"),
        ("spreadsheet-generation", "Создай таблицу"),
        ("spreadsheet-formatting", "Выдели жирным"),
        ("spreadsheet-transformation", "Преобразуй данные")
    ]
    
    results = []
    
    for category, query in test_cases:
        logger.info(f"\n--- Testing category: {category} ---")
        
        try:
            examples = categorized_prompt_search.search_examples(
                query=query,
                category=category,
                search_mode="fulltext",
                limit=3
            )
            
            logger.info(f"Query: {query}")
            logger.info(f"Found {len(examples)} examples")
            
            if examples:
                example = examples[0]
                logger.info(f"First example task: {example['task'][:60]}...")
                logger.info(f"Has request_table: {len(example['request_table']) > 0}")
                logger.info(f"Has response_table: {len(example['response_table']) > 0}")
                results.append(True)
            else:
                logger.warning(f"No examples found for {category}")
                results.append(False)
                
        except Exception as e:
            logger.error(f"Error testing {category}: {e}")
            results.append(False)
    
    return all(results)

def test_prompt_builder_integration():
    """Test the prompt builder integration"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Prompt Builder Integration")
    logger.info("=" * 60)
    
    from app.services.gigachat.prompt_builder import prompt_builder
    
    try:
        # Test classifier
        logger.info("\n--- Testing classifier category ---")
        system_prompt = prompt_builder.prepare_system_prompt(
            prompt_type='classifier',
            user_query='Найди максимум'
        )
        logger.info(f"Classifier prompt length: {len(system_prompt)} characters")
        logger.info(f"Contains examples: {'Пример' in system_prompt}")
        
        # Test regular category
        logger.info("\n--- Testing spreadsheet-analysis category ---")
        system_prompt = prompt_builder.prepare_system_prompt(
            prompt_type='spreadsheet-analysis',
            user_query='Посчитай среднее'
        )
        logger.info(f"Analysis prompt length: {len(system_prompt)} characters")
        logger.info(f"Contains examples: {'Пример' in system_prompt}")
        
        return True
    except Exception as e:
        logger.error(f"Error testing prompt builder: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("Starting refactoring validation tests\n")
    
    # Run tests
    test1_passed = test_classification_examples()
    test2_passed = test_categorized_examples()
    test3_passed = test_prompt_builder_integration()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Classification search: {'✓ PASSED' if test1_passed else '✗ FAILED'}")
    logger.info(f"Categorized search: {'✓ PASSED' if test2_passed else '✗ FAILED'}")
    logger.info(f"Prompt builder integration: {'✓ PASSED' if test3_passed else '✗ FAILED'}")
    
    all_passed = test1_passed and test2_passed and test3_passed
    logger.info(f"\nOverall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    
    sys.exit(0 if all_passed else 1)
