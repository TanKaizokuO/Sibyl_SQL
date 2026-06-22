/**
 * Cognitive Database Agent - Schema-Aware Query Suggestion Chips
 * =============================================================
 *
 * Renders a horizontal row of clickable suggestion chips below each assistant
 * response. Each chip carries a category icon and triggers a new query when
 * clicked — transforming the UI from reactive to proactive.
 *
 * Category icons:
 *   drill-down → 🔍  (more detail on the current result)
 *   compare    → ⚖️  (compare two values or time periods)
 *   trend      → 📈  (show over time)
 *   filter     → 🎯  (narrow the scope)
 *
 * @component SuggestionChips
 */

import './SuggestionChips.css';

const CATEGORY_ICONS = {
  'drill-down': '🔍',
  'compare':    '⚖️',
  'trend':      '📈',
  'filter':     '🎯',
};

const CATEGORY_LABELS = {
  'drill-down': 'Drill Down',
  'compare':    'Compare',
  'trend':      'Trend',
  'filter':     'Filter',
};

/**
 * SuggestionChips Component
 *
 * @param {Object}   props
 * @param {Array}    props.suggestions        - Array of {question, category} objects
 * @param {Function} props.onSuggestionClick  - Called with the suggestion question string
 */
const SuggestionChips = ({ suggestions, onSuggestionClick }) => {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div className="suggestion-chips" role="list" aria-label="Suggested follow-up questions">
      <div className="suggestion-chips__label">
        <span className="suggestion-chips__label-icon">💡</span>
        Try asking:
      </div>

      <div className="suggestion-chips__row">
        {suggestions.map((s, idx) => {
          const icon  = CATEGORY_ICONS[s.category]  ?? '💬';
          const label = CATEGORY_LABELS[s.category] ?? s.category;

          return (
            <button
              key={idx}
              id={`suggestion-chip-${idx}`}
              className={`suggestion-chip suggestion-chip--${s.category ?? 'default'}`}
              onClick={() => onSuggestionClick(s.question)}
              role="listitem"
              title={`${label}: ${s.question}`}
              aria-label={`Suggestion: ${s.question}`}
            >
              <span className="suggestion-chip__icon" aria-hidden="true">
                {icon}
              </span>
              <span className="suggestion-chip__text">
                <span className="tactical-prefix">EXECUTE_QUERY_0{idx + 1} // {(s.category || 'ACTION').toUpperCase()} // </span>
                <span className="question-text">{s.question}</span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default SuggestionChips;
