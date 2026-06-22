"""
Phase 3 Unit Tests - LLM Chart Detection & Schema-Aware Suggestions
====================================================================

Tests for:
3.1 - _parse_viz_hint() function in cognitive_agent.py
3.1 - determineChartTypeWithHint() in AutoChartLogic (via backend simulation)
3.2 - generate_follow_up_suggestions() in suggestion_engine.py
3.2 - _parse_suggestions_json() helper
"""

import unittest
import sys
import os

# Add project root to path so we can import backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from backend.app.agent.cognitive_agent import _parse_viz_hint
from backend.app.agent.suggestion_engine import (
    _parse_suggestions_json,
    _validate_suggestions,
    _extract_result_summary,
)


# ===========================================================================
# Tests for _parse_viz_hint()
# ===========================================================================

class TestParseVizHint(unittest.TestCase):
    """Unit tests for the _parse_viz_hint() helper in cognitive_agent.py"""

    def _make_output(self, hint_block: str, prefix: str = "Here are the results.") -> str:
        return f"{prefix}\n{hint_block}"

    def test_valid_complete_hint_parsed(self):
        """A well-formed VIZ_HINT block should be fully parsed."""
        output = """
Total sales by region:
[VIZ_HINT]
chart_type: bar
x_axis: region
y_axis: total_sales
reasoning: Comparing categorical regional data
[/VIZ_HINT]
        """.strip()

        clean, hint = _parse_viz_hint(output)

        self.assertIsNotNone(hint)
        self.assertEqual(hint['chart_type'], 'bar')
        self.assertEqual(hint['x_axis'], 'region')
        self.assertEqual(hint['y_axis'], 'total_sales')
        self.assertIn('Comparing', hint['reasoning'])
        self.assertNotIn('[VIZ_HINT]', clean)
        self.assertNotIn('[/VIZ_HINT]', clean)

    def test_line_chart_hint(self):
        """line chart type should be accepted."""
        output = "[VIZ_HINT]\nchart_type: line\nx_axis: year\ny_axis: revenue\nreasoning: Trend over time\n[/VIZ_HINT]"
        _, hint = _parse_viz_hint(output)
        self.assertEqual(hint['chart_type'], 'line')

    def test_area_chart_hint(self):
        """area chart type should be accepted."""
        output = "[VIZ_HINT]\nchart_type: area\nx_axis: month\ny_axis: sales, profit\nreasoning: Stacked trend\n[/VIZ_HINT]"
        _, hint = _parse_viz_hint(output)
        self.assertEqual(hint['chart_type'], 'area')

    def test_pie_chart_hint(self):
        """pie chart type should be accepted."""
        output = "[VIZ_HINT]\nchart_type: pie\nx_axis: category\ny_axis: percentage\nreasoning: Distribution\n[/VIZ_HINT]"
        _, hint = _parse_viz_hint(output)
        self.assertEqual(hint['chart_type'], 'pie')

    def test_table_chart_hint(self):
        """table chart type should be accepted."""
        output = "[VIZ_HINT]\nchart_type: table\nx_axis: id\ny_axis: name, amount, date\nreasoning: Complex structure\n[/VIZ_HINT]"
        _, hint = _parse_viz_hint(output)
        self.assertEqual(hint['chart_type'], 'table')

    def test_choropleth_is_valid_hint(self):
        """choropleth is a valid chart type in Phase 4."""
        output = "[VIZ_HINT]\nchart_type: choropleth\nx_axis: country\ny_axis: gdp\nreasoning: Geographic\n[/VIZ_HINT]"
        _, hint = _parse_viz_hint(output)
        self.assertEqual(hint['chart_type'], 'choropleth')

    def test_missing_chart_type_returns_none(self):
        """VIZ_HINT without chart_type should return None hint."""
        output = "[VIZ_HINT]\nx_axis: region\ny_axis: sales\n[/VIZ_HINT]"
        _, hint = _parse_viz_hint(output)
        self.assertIsNone(hint)

    def test_no_viz_hint_returns_original_text(self):
        """When no VIZ_HINT block, output should be returned unchanged."""
        output = "There are 5 records in the sales table."
        clean, hint = _parse_viz_hint(output)
        self.assertEqual(clean, output)
        self.assertIsNone(hint)

    def test_clean_output_strips_hint_block(self):
        """The returned clean_output should not contain the VIZ_HINT block."""
        prefix = "The data shows quarterly performance."
        output = f"{prefix}\n[VIZ_HINT]\nchart_type: bar\nx_axis: q\ny_axis: val\nreasoning: test\n[/VIZ_HINT]"
        clean, _ = _parse_viz_hint(output)
        self.assertIn(prefix, clean)
        self.assertNotIn('[VIZ_HINT]', clean)

    def test_multiline_output_with_hint(self):
        """VIZ_HINT block embedded in multi-line response should parse correctly."""
        output = (
            "Sales summary:\n"
            "- North: $1M\n"
            "- South: $2M\n\n"
            "[VIZ_HINT]\n"
            "chart_type: bar\n"
            "x_axis: region\n"
            "y_axis: amount\n"
            "reasoning: Compare regional totals\n"
            "[/VIZ_HINT]\n"
            "Please review above."
        )
        clean, hint = _parse_viz_hint(output)
        self.assertIsNotNone(hint)
        self.assertEqual(hint['chart_type'], 'bar')
        self.assertIn('Sales summary', clean)
        self.assertIn('Please review', clean)

    def test_uppercase_chart_type_normalised(self):
        """chart_type value should be lowercased during parsing."""
        output = "[VIZ_HINT]\nchart_type: Bar\nx_axis: x\ny_axis: y\nreasoning: test\n[/VIZ_HINT]"
        _, hint = _parse_viz_hint(output)
        self.assertEqual(hint['chart_type'], 'bar')


# ===========================================================================
# Tests for suggestion_engine helpers
# ===========================================================================

class TestParseSuggestionsJson(unittest.TestCase):
    """Tests for the JSON-parsing helper in suggestion_engine.py"""

    def test_valid_json_array_parsed(self):
        """A well-formed JSON array should parse correctly."""
        text = '[{"question": "Show by region?", "category": "compare"}, {"question": "Trend over time?", "category": "trend"}]'
        result = _parse_suggestions_json(text)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['question'], 'Show by region?')
        self.assertEqual(result[0]['category'], 'compare')

    def test_json_array_embedded_in_text(self):
        """JSON array embedded in prose should still be extracted."""
        text = 'Here are some suggestions:\n[{"question": "Q1?", "category": "drill-down"}]\nEnd.'
        result = _parse_suggestions_json(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['question'], 'Q1?')

    def test_max_3_suggestions_enforced(self):
        """Returns at most 3 suggestions even if more are provided."""
        text = '[{"question": "Q1", "category": "filter"}, {"question": "Q2", "category": "trend"}, {"question": "Q3", "category": "compare"}, {"question": "Q4", "category": "drill-down"}]'
        result = _parse_suggestions_json(text)
        self.assertLessEqual(len(result), 3)

    def test_invalid_json_returns_empty(self):
        """Invalid JSON should return empty list (graceful degradation)."""
        result = _parse_suggestions_json("Not JSON at all")
        self.assertEqual(result, [])

    def test_missing_question_key_filtered_out(self):
        """Suggestions without a 'question' key should be filtered."""
        text = '[{"category": "filter"}, {"question": "Valid?", "category": "trend"}]'
        result = _parse_suggestions_json(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['question'], 'Valid?')

    def test_invalid_category_defaults_to_drill_down(self):
        """An unknown category should default to 'drill-down'."""
        text = '[{"question": "Something?", "category": "nonsense"}]'
        result = _parse_suggestions_json(text)
        self.assertEqual(result[0]['category'], 'drill-down')

    def test_empty_question_filtered_out(self):
        """Empty question strings should be filtered."""
        text = '[{"question": "", "category": "trend"}, {"question": "Good question?", "category": "compare"}]'
        result = _parse_suggestions_json(text)
        self.assertEqual(len(result), 1)

    def test_all_valid_categories_accepted(self):
        """All four valid category values should be accepted."""
        categories = ['drill-down', 'compare', 'trend', 'filter']
        for cat in categories:
            text = f'[{{"question": "Q?", "category": "{cat}"}}]'
            result = _parse_suggestions_json(text)
            self.assertEqual(result[0]['category'], cat)


class TestExtractResultSummary(unittest.TestCase):
    """Tests for the result summary extraction helper."""

    def test_strips_viz_hint_block(self):
        """VIZ_HINT block should be removed from summary."""
        text = "Sales are $100K.\n[VIZ_HINT]\nchart_type: bar\n[/VIZ_HINT]\nDone."
        summary = _extract_result_summary(text)
        self.assertNotIn('[VIZ_HINT]', summary)
        self.assertIn('Sales are', summary)

    def test_truncates_to_400_chars(self):
        """Summary should not exceed 400 characters."""
        long_text = "A" * 1000
        summary = _extract_result_summary(long_text)
        self.assertLessEqual(len(summary), 400)

    def test_empty_string(self):
        """Empty input should return empty string."""
        self.assertEqual(_extract_result_summary(""), "")


if __name__ == '__main__':
    unittest.main()
