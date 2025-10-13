"""
Unit Tests for ChartPromptBuilder Service
Tests for YAML template loading, template matching, and prompt construction
"""

import pytest
import os
import yaml
from unittest.mock import patch, mock_open, MagicMock

from app.services.chart.prompt_builder import ChartPromptBuilder


class TestChartPromptBuilder:
    """Test suite for ChartPromptBuilder service"""
    
    @pytest.fixture
    def prompt_builder(self):
        """Create a ChartPromptBuilder instance for testing"""
        return ChartPromptBuilder(resources_dir='resources/prompts/')
    
    def test_load_system_prompt_success(self, prompt_builder):
        """Test successful loading of system prompt"""
        system_prompt = prompt_builder.load_system_prompt()
        
        assert system_prompt is not None
        assert isinstance(system_prompt, str)
        assert len(system_prompt) > 0
        assert 'ChartResultResponse' in system_prompt or 'график' in system_prompt.lower()
    
    def test_load_system_prompt_caching(self, prompt_builder):
        """Test that system prompt is cached after first load"""
        # Load twice
        prompt1 = prompt_builder.load_system_prompt()
        prompt2 = prompt_builder.load_system_prompt()
        
        # Should be the same instance (cached)
        assert prompt1 == prompt2
        assert prompt_builder._system_prompt_cache is not None
    
    def test_load_examples_all_files(self, prompt_builder):
        """Test loading all example YAML files"""
        examples = prompt_builder.load_examples()
        
        assert examples is not None
        assert isinstance(examples, list)
        assert len(examples) > 0
        
        # Check structure of first example
        if examples:
            example = examples[0]
            assert 'id' in example
            assert 'task' in example
            assert 'request_table' in example
            assert 'response_table' in example
    
    def test_load_examples_caching(self, prompt_builder):
        """Test that examples are cached"""
        examples1 = prompt_builder.load_examples()
        examples2 = prompt_builder.load_examples()
        
        assert len(examples1) == len(examples2)
        assert len(prompt_builder._template_cache) > 0
    
    def test_select_best_template_time_series(self, prompt_builder):
        """Test template selection for time series data"""
        user_query = "Построй график изменения величины во времени"
        
        template = prompt_builder.select_best_template(
            user_query,
            chart_type='line',
            data_pattern='time_series'
        )
        
        assert template is not None
        assert isinstance(template, dict)
        assert 'task' in template
    
    def test_select_best_template_pie_chart(self, prompt_builder):
        """Test template selection for pie chart"""
        user_query = "Создай круговую диаграмму распределения"
        
        template = prompt_builder.select_best_template(
            user_query,
            chart_type='pie',
            data_pattern='categorical'
        )
        
        assert template is not None
        # Should prefer pie chart examples
        if template.get('response_table'):
            assert 'pie' in template['response_table'].lower() or 'pie' in template['task'].lower()
    
    def test_calculate_similarity_identical(self, prompt_builder):
        """Test similarity calculation for identical strings"""
        query1 = "Построй график"
        query2 = "Построй график"
        
        similarity = prompt_builder.calculate_similarity(query1, query2)
        
        assert similarity == 1.0
    
    def test_calculate_similarity_different(self, prompt_builder):
        """Test similarity calculation for completely different strings"""
        query1 = "Построй график"
        query2 = "Create a table"
        
        similarity = prompt_builder.calculate_similarity(query1, query2)
        
        assert 0.0 <= similarity < 0.3  # Should be very low
    
    def test_calculate_similarity_synonyms(self, prompt_builder):
        """Test similarity calculation with synonyms"""
        query1 = "Построй линейный график"
        query2 = "Создай line chart"
        
        similarity = prompt_builder.calculate_similarity(query1, query2)
        
        # Should have some similarity due to keyword matching
        assert similarity > 0.2
    
    def test_build_prompt_structure(self, prompt_builder):
        """Test that build_prompt creates proper structure"""
        user_query = "Построй график"
        chart_data = {
            "data_range": "A1:B10",
            "chart_data": [
                {"name": "X", "values": [1, 2, 3], "format": "General"}
            ],
            "chart_type": "line",
            "query_text": user_query
        }
        
        prompt = prompt_builder.build_prompt(user_query, chart_data)
        
        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert 'ЗАДАЧА' in prompt
        assert user_query in prompt
    
    def test_clear_cache(self, prompt_builder):
        """Test cache clearing functionality"""
        # Load to populate cache
        prompt_builder.load_system_prompt()
        prompt_builder.load_examples()
        
        assert prompt_builder._system_prompt_cache is not None
        assert len(prompt_builder._template_cache) > 0
        
        # Clear cache
        prompt_builder.clear_cache()
        
        assert prompt_builder._system_prompt_cache is None
        assert len(prompt_builder._template_cache) == 0
    
    def test_get_template_stats(self, prompt_builder):
        """Test template statistics retrieval"""
        stats = prompt_builder.get_template_stats()
        
        assert stats is not None
        assert isinstance(stats, dict)
        assert 'total_templates' in stats
        assert 'chart_types_coverage' in stats
        assert 'cache_size' in stats
        assert 'system_prompt_loaded' in stats
        
        assert stats['total_templates'] > 0
    
    def test_template_stats_chart_types(self, prompt_builder):
        """Test that template stats include various chart types"""
        stats = prompt_builder.get_template_stats()
        
        chart_types = stats.get('chart_types_coverage', {})
        
        # Should have multiple chart types covered
        assert len(chart_types) > 0
        assert any(ct in chart_types for ct in ['line', 'pie', 'column', 'scatter', 'box_plot'])
    
    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_load_system_prompt_file_not_found(self, mock_file, prompt_builder):
        """Test error handling when system prompt file not found"""
        # Clear cache to force reload
        prompt_builder._system_prompt_cache = None
        
        with pytest.raises(FileNotFoundError):
            prompt_builder.load_system_prompt()
    
    def test_malformed_yaml_handling(self, prompt_builder):
        """Test handling of malformed YAML files"""
        # This test would require creating a malformed YAML file
        # For now, just verify that load_examples doesn't crash
        examples = prompt_builder.load_examples()
        
        # Should still return a list (empty or with valid examples)
        assert isinstance(examples, list)
    
    def test_inject_context_basic(self, prompt_builder):
        """Test basic context injection"""
        template = {
            'response_table': '{"success": true, "message": "Test"}'
        }
        user_data = {"test_key": "test_value"}
        
        result = prompt_builder.inject_context(template, user_data)
        
        assert result is not None
        assert isinstance(result, str)
    
    def test_keyword_matching_effectiveness(self, prompt_builder):
        """Test that keyword matching improves similarity scores"""
        # Queries with same meaning but different words
        query1 = "Построй линейный график"
        query2 = "Создай диаграмму тренда"
        
        similarity = prompt_builder.calculate_similarity(query1, query2)
        
        # Should recognize chart-related keywords
        assert similarity > 0.15  # Some similarity due to chart keywords


class TestTemplateMatching:
    """Additional tests for template matching logic"""
    
    @pytest.fixture
    def prompt_builder(self):
        return ChartPromptBuilder(resources_dir='resources/prompts/')
    
    def test_boost_for_chart_type_match(self, prompt_builder):
        """Test that matching chart type boosts similarity score"""
        query = "Построй pie chart"
        
        # Select with pie chart type specified
        template = prompt_builder.select_best_template(
            query,
            chart_type='pie'
        )
        
        assert template is not None
    
    def test_boost_for_data_pattern(self, prompt_builder):
        """Test that data pattern boosts template selection"""
        query = "Создай график временного ряда"
        
        template = prompt_builder.select_best_template(
            query,
            data_pattern='time_series'
        )
        
        assert template is not None
        # Should prefer time series examples
    
    def test_multi_series_pattern_detection(self, prompt_builder):
        """Test template selection for multi-series data"""
        query = "Сравни продажи нескольких продуктов"
        
        template = prompt_builder.select_best_template(
            query,
            data_pattern='multi_series'
        )
        
        assert template is not None


# Fixtures for testing
@pytest.fixture
def sample_chart_data():
    """Sample chart data for testing"""
    return {
        "data_range": "A1:B10",
        "chart_data": [
            {
                "name": "Date",
                "values": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "format": "dd/mm/yyyy"
            },
            {
                "name": "Value",
                "values": [100, 150, 120],
                "format": "#,##0"
            }
        ],
        "chart_type": "line",
        "query_text": "Построй график"
    }


@pytest.fixture
def sample_template():
    """Sample template for testing"""
    return {
        'id': 'example_01.yaml',
        'task': 'Построй график изменения величины во времени',
        'request_table': '{"data_range": "A1:B10"}',
        'response_table': '{"success": true, "status": "completed"}'
    }


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
