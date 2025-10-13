"""
Chart Prompt Builder Service
Service for loading YAML templates and building structured prompts for chart generation
"""

import os
import json
import yaml
import glob
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
from difflib import SequenceMatcher


class ChartPromptBuilder:
    """Service for building prompts for chart generation with template matching"""
    
    PROMPT_DIR = 'data-chart'
    
    def __init__(self, resources_dir: str = 'resources/prompts/'):
        """
        Initialize the prompt builder
        
        Args:
            resources_dir: Base directory for prompt resources
        """
        self.resources_dir = resources_dir
        self.category_dir = os.path.join(resources_dir, self.PROMPT_DIR)
        self._template_cache: Dict[str, Any] = {}
        self._system_prompt_cache: Optional[str] = None
        
    def load_system_prompt(self) -> str:
        """
        Load system prompt from system_prompt.txt file
        
        Returns:
            System prompt string
        """
        if self._system_prompt_cache is not None:
            return self._system_prompt_cache
            
        prompt_path = os.path.join(self.category_dir, 'system_prompt.txt')
        
        if not os.path.exists(prompt_path):
            logger.error(f"System prompt file not found: {prompt_path}")
            raise FileNotFoundError(f"System prompt file not found: {prompt_path}")
            
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                self._system_prompt_cache = f.read().strip()
                logger.info("System prompt loaded successfully")
                return self._system_prompt_cache
        except Exception as e:
            logger.error(f"Error loading system prompt: {e}")
            raise
    
    def load_examples(self) -> List[Dict[str, Any]]:
        """
        Load examples from example_*.yaml files
        
        Returns:
            List of example dictionaries with task, request_table, and response_table
        """
        if self._template_cache:
            return list(self._template_cache.values())
            
        if not os.path.exists(self.category_dir):
            logger.error(f"Examples directory not found: {self.category_dir}")
            raise FileNotFoundError(f"Examples directory not found: {self.category_dir}")
            
        example_files = glob.glob(os.path.join(self.category_dir, 'example_*.yaml'))
        example_files.sort()  # Ensure consistent ordering
        
        examples = []
        for example_file in example_files:
            try:
                with open(example_file, 'r', encoding='utf-8') as f:
                    example_data = yaml.safe_load(f)
                    
                    # Validate example structure
                    if not all(key in example_data for key in ['task', 'request_table', 'response_table']):
                        logger.warning(f"Example file {example_file} missing required fields")
                        continue
                    
                    example_id = os.path.basename(example_file)
                    example = {
                        'id': example_id,
                        'task': example_data.get('task', ''),
                        'request_table': example_data.get('request_table', ''),
                        'response_table': example_data.get('response_table', '')
                    }
                    
                    examples.append(example)
                    self._template_cache[example_id] = example
                    
            except Exception as e:
                logger.error(f"Error loading example file {example_file}: {e}")
                continue
        
        logger.info(f"Loaded {len(examples)} example templates")
        return examples
    
    def select_best_template(
        self, 
        user_query: str, 
        chart_type: Optional[str] = None,
        data_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Select the most appropriate template based on user query and data characteristics
        
        Args:
            user_query: User's natural language request
            chart_type: Requested chart type (if specified)
            data_pattern: Data pattern type (time_series, categorical, multi_series, statistical)
            
        Returns:
            Best matching template dictionary
        """
        examples = self.load_examples()
        
        if not examples:
            logger.warning("No templates available for matching")
            return {}
        
        # Calculate similarity scores for each template
        scores = []
        for example in examples:
            score = self.calculate_similarity(user_query, example['task'])
            
            # Boost score if chart type matches
            if chart_type:
                try:
                    response_data = json.loads(example['response_table'])
                    if response_data.get('chart_config', {}).get('chart_type') == chart_type:
                        score += 0.2
                except:
                    pass
            
            # Boost score based on data pattern
            if data_pattern:
                pattern_keywords = {
                    'time_series': ['время', 'дата', 'изменение', 'динамика', 'тренд'],
                    'categorical': ['категория', 'распределение', 'доля', 'процент'],
                    'multi_series': ['сравнение', 'несколько', 'продукт', 'квартал'],
                    'statistical': ['статистик', 'анализ', 'размах', 'распределение']
                }
                
                keywords = pattern_keywords.get(data_pattern, [])
                task_lower = example['task'].lower()
                
                if any(kw in task_lower for kw in keywords):
                    score += 0.15
            
            scores.append((score, example))
        
        # Sort by score descending
        scores.sort(key=lambda x: x[0], reverse=True)
        
        best_template = scores[0][1]
        best_score = scores[0][0]
        
        logger.info(f"Selected template '{best_template['id']}' with similarity score {best_score:.3f}")
        
        return best_template
    
    def calculate_similarity(self, query1: str, query2: str) -> float:
        """
        Calculate semantic similarity between two queries
        
        Args:
            query1: First query string
            query2: Second query string
            
        Returns:
            Similarity score between 0 and 1
        """
        # Normalize strings
        q1 = query1.lower().strip()
        q2 = query2.lower().strip()
        
        # Use SequenceMatcher for basic similarity
        base_similarity = SequenceMatcher(None, q1, q2).ratio()
        
        # Keyword matching for better semantic understanding
        keywords_mapping = {
            'график': ['график', 'диаграмма', 'chart', 'визуализ'],
            'линейный': ['линейн', 'line', 'тренд', 'изменен'],
            'круговой': ['кругов', 'pie', 'доля', 'процент'],
            'столбч': ['столбч', 'column', 'сравнен', 'гистограмм'],
            'точечн': ['точечн', 'scatter', 'корреляц', 'зависимост'],
            'площад': ['площад', 'area', 'накопител'],
            'ящик': ['ящик', 'box', 'размах', 'статистик']
        }
        
        # Extract keywords from both queries
        q1_keywords = set()
        q2_keywords = set()
        
        for key, synonyms in keywords_mapping.items():
            if any(syn in q1 for syn in synonyms):
                q1_keywords.add(key)
            if any(syn in q2 for syn in synonyms):
                q2_keywords.add(key)
        
        # Calculate keyword overlap
        if q1_keywords and q2_keywords:
            keyword_similarity = len(q1_keywords & q2_keywords) / len(q1_keywords | q2_keywords)
            # Weighted average: 60% base similarity, 40% keyword similarity
            return 0.6 * base_similarity + 0.4 * keyword_similarity
        
        return base_similarity
    
    def build_prompt(
        self, 
        user_query: str,
        chart_data: Dict[str, Any],
        selected_template: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build complete prompt with system instructions, examples, and user request
        
        Args:
            user_query: User's natural language request
            chart_data: Chart data structure
            selected_template: Pre-selected template (optional, will auto-select if None)
            
        Returns:
            Complete formatted prompt string
        """
        # Load system prompt
        system_prompt = self.load_system_prompt()
        
        # Load all examples
        examples = self.load_examples()
        
        # Build prompt parts
        prompt_parts = [system_prompt, "", "## Примеры:"]
        
        # Add examples
        for idx, example in enumerate(examples[:4], 1):  # Limit to 4 examples to save tokens
            prompt_parts.append(f"\n### Пример {idx}:")
            prompt_parts.append(f"ЗАДАЧА: {example['task']}")
            prompt_parts.append(f"ДАННЫЕ: {example['request_table']}")
            prompt_parts.append(f"Твой ответ:")
            prompt_parts.append(example['response_table'])
        
        # Add user request
        prompt_parts.append("\n## Текущий запрос:")
        prompt_parts.append(f"ЗАДАЧА: {user_query}")
        prompt_parts.append(f"ДАННЫЕ: {json.dumps(chart_data, ensure_ascii=False, indent=2)}")
        prompt_parts.append("\nТвой ответ:")
        
        return "\n".join(prompt_parts)
    
    def inject_context(
        self, 
        template: Dict[str, Any], 
        user_data: Dict[str, Any]
    ) -> str:
        """
        Inject user-specific context into a template
        
        Args:
            template: Template dictionary
            user_data: User's data to inject
            
        Returns:
            Template with injected context
        """
        # For now, simple replacement of data
        # In future, could support template variables like {{data_range}}
        
        try:
            response_template = template.get('response_table', '{}')
            response_data = json.loads(response_template)
            
            # Update with user-specific data if needed
            # This is a placeholder for future template variable support
            
            return json.dumps(response_data, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"Error injecting context into template: {e}")
            return template.get('response_table', '{}')
    
    def clear_cache(self):
        """Clear cached templates and system prompt"""
        self._template_cache.clear()
        self._system_prompt_cache = None
        logger.info("Template cache cleared")
    
    def get_template_stats(self) -> Dict[str, Any]:
        """
        Get statistics about loaded templates
        
        Returns:
            Dictionary with template statistics
        """
        examples = self.load_examples()
        
        chart_types = {}
        for example in examples:
            try:
                response_data = json.loads(example['response_table'])
                chart_type = response_data.get('chart_config', {}).get('chart_type', 'unknown')
                chart_types[chart_type] = chart_types.get(chart_type, 0) + 1
            except:
                pass
        
        return {
            'total_templates': len(examples),
            'chart_types_coverage': chart_types,
            'cache_size': len(self._template_cache),
            'system_prompt_loaded': self._system_prompt_cache is not None
        }


# Global instance
chart_prompt_builder = ChartPromptBuilder()
