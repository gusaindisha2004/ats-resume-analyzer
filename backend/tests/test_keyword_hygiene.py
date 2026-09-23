"""Keyword filtering.

Every string here came out of a real analysis. An LLM asked for "keywords"
returns requirement sentences among them, and those can never fuzzy-match a
resume term — so each one inflates the missing count, which drives the score
penalty. One real resume was shown as missing 92% of the posting's terms and
took the maximum 15-point deduction, largely for failing to match strings that
were never matchable.
"""

import pytest

from backend.utils.matching import clean_keywords, is_usable_keyword

# Verbatim from the job description parse that exposed this.
REQUIREMENT_SENTENCES = [
    '1-3 years experience with insurance claims and EHR databases '
    '(e.g., IQVIA, Komodo, Forian, Compile)',
    "Bachelor's degree in Statistics, Mathematics, Machine Learning, Physics, "
    'or related field',
    'Experience with life science APIs and public datasets '
    '(e.g., PubMed, OpenTrials, CMS, CDC)',
]

# Verbatim from the skills-gap output, which mined spaCy noun chunks.
NOUN_CHUNK_NOISE = ['("cv', 'a commitment', 'a related field']

# Short generic phrases this filter deliberately does NOT catch. They are
# structurally identical to real multi-word skills ("natural language
# processing"), so rejecting them would reject those too. They were only ever
# produced by mining spaCy noun chunks, which analyze_skills_gap no longer
# does — the fix for these is the source, not the filter.
UNCAUGHT_BY_DESIGN = ['Detail-oriented analytical mindset', 'a non-technical manner']

REAL_SKILLS = [
    'Python', 'SQL', 'machine learning', 'Data Analyst', 'Power BI',
    'scikit-learn', 'time series forecasting', 'EHR databases', 'Tableau',
]


class TestRejectsProse:
    @pytest.mark.parametrize('text', REQUIREMENT_SENTENCES)
    def test_requirement_sentences_are_not_keywords(self, text):
        assert not is_usable_keyword(text)

    @pytest.mark.parametrize('text', NOUN_CHUNK_NOISE)
    def test_noun_chunk_noise_is_rejected(self, text):
        assert not is_usable_keyword(text)

    def test_parenthetical_examples_are_rejected(self):
        assert not is_usable_keyword('databases (e.g., Postgres)')

    def test_comma_separated_lists_are_rejected(self):
        assert not is_usable_keyword('Statistics, Mathematics, Physics')

    def test_punctuation_only_input_is_rejected(self):
        assert not is_usable_keyword('---')
        assert not is_usable_keyword('')
        assert not is_usable_keyword('   ')

    def test_pure_boilerplate_is_rejected(self):
        assert not is_usable_keyword('years experience')
        assert not is_usable_keyword('the role')

    @pytest.mark.parametrize('text', UNCAUGHT_BY_DESIGN)
    def test_short_generic_phrases_survive_the_filter(self, text):
        """Documents the limit: length and punctuation can't separate these
        from real multi-word skills. Handled by not mining noun chunks."""
        assert is_usable_keyword(text)


class TestKeepsRealSkills:
    @pytest.mark.parametrize('text', REAL_SKILLS)
    def test_genuine_skills_survive(self, text):
        assert is_usable_keyword(text), f'{text!r} should be kept'

    def test_hyphenated_and_dotted_names_survive(self):
        assert is_usable_keyword('scikit-learn')
        assert is_usable_keyword('Node.js')

    def test_multi_word_skills_up_to_the_limit_survive(self):
        assert is_usable_keyword('natural language processing')


class TestCleanKeywords:
    def test_strips_leading_articles(self):
        assert clean_keywords(['a growth mindset']) == ['growth mindset']

    def test_drops_duplicates_case_insensitively(self):
        assert clean_keywords(['Python', 'python', 'PYTHON']) == ['Python']

    def test_preserves_order_of_first_appearance(self):
        assert clean_keywords(['SQL', 'Python', 'SQL']) == ['SQL', 'Python']

    def test_filters_a_realistic_mixed_list(self):
        result = clean_keywords(REQUIREMENT_SENTENCES + REAL_SKILLS)
        assert 'Python' in result
        assert not any(len(k.split()) > 4 for k in result)
        assert not any('(' in k for k in result)

    def test_ignores_non_strings(self):
        assert clean_keywords(['Python', None, 42, {'a': 1}]) == ['Python']

    def test_empty_input_is_empty_output(self):
        assert clean_keywords([]) == []


class TestScoreImpact:
    """The filter exists because unmatched prose was corrupting the score."""

    def test_prose_no_longer_counts_toward_the_missing_total(self):
        from backend.utils.matching import fuzzy_match_keywords

        resume = ['Python', 'SQL', 'Power BI', 'machine learning']
        raw_jd = REQUIREMENT_SENTENCES + ['Python', 'SQL', 'Power BI']

        unfiltered = fuzzy_match_keywords(resume, raw_jd)
        filtered = fuzzy_match_keywords(resume, clean_keywords(raw_jd))

        def penalty_for(missing, total):
            """The deduction the scorer would apply, by its own thresholds."""
            from backend.core.config import JD_MISSING_PENALTIES

            pct = missing / max(total, 1)
            for threshold, points in JD_MISSING_PENALTIES:
                if pct > threshold:
                    return points
            return 0.0

        before = penalty_for(len(unfiltered['missing']), len(raw_jd))
        after = penalty_for(len(filtered['missing']), len(clean_keywords(raw_jd)))

        # This resume holds every skill the posting actually named, yet the
        # unmatchable sentences alone were enough to earn a deduction.
        assert before > 0, 'unfiltered prose should have triggered a penalty'
        assert after == 0.0, 'with prose removed, nothing is genuinely missing'

    def test_matched_skills_are_still_found_after_filtering(self):
        from backend.utils.matching import fuzzy_match_keywords

        resume = ['Python', 'SQL', 'Power BI']
        raw_jd = REQUIREMENT_SENTENCES + ['Python', 'SQL', 'Power BI']
        result = fuzzy_match_keywords(resume, clean_keywords(raw_jd))

        assert set(result['matched']) == {'Python', 'SQL', 'Power BI'}
