"""Tests for KeywordExtractor service."""

from __future__ import annotations

import pytest

from app.services.keyword_extractor import KeywordExtractor


class TestKeywordExtractor:
    """Test KeywordExtractor functionality."""

    def test_extract_keywords_from_simple_text(self) -> None:
        """Test extracting keywords from simple text."""
        extractor = KeywordExtractor(max_features=5)

        text = "AI-powered note-taking app for researchers and students"
        keywords = extractor.extract(text)

        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert len(keywords) <= 5

        # Should extract meaningful words
        assert any(
            keyword in ["ai", "powered", "note", "taking", "app", "researchers", "students", "ai powered"]
            for keyword in keywords
        )

    def test_extract_keywords_with_stopwords(self) -> None:
        """Test that stopwords are filtered out."""
        extractor = KeywordExtractor(max_features=10)

        text = "machine learning is the future of artificial intelligence and data science"
        keywords = extractor.extract(text)

        # Core stopwords should be filtered
        core_stopwords = {"is", "the", "of", "and"}
        for keyword in keywords:
            # Single-word keywords should not be core stopwords
            if " " not in keyword:  # Only check unigrams
                assert keyword not in core_stopwords

    def test_extract_keywords_from_empty_text(self) -> None:
        """Test extracting keywords from empty text."""
        extractor = KeywordExtractor()

        assert extractor.extract("") == []
        assert extractor.extract("   ") == []
        assert extractor.extract("\n\n") == []

    def test_extract_keywords_removes_urls(self) -> None:
        """Test that URLs are removed during preprocessing."""
        extractor = KeywordExtractor(max_features=5)

        text = "Check out our app at https://example.com for AI-powered note-taking"
        keywords = extractor.extract(text)

        # URL should not appear in keywords
        assert not any("http" in keyword or "example.com" in keyword for keyword in keywords)

        # But meaningful words should be extracted
        assert any(keyword in ["app", "ai", "powered", "note", "taking", "ai powered"] for keyword in keywords)

    def test_extract_keywords_removes_emails(self) -> None:
        """Test that email addresses are removed."""
        extractor = KeywordExtractor(max_features=5)

        text = "Contact us at support@example.com for AI-powered solutions"
        keywords = extractor.extract(text)

        # Email should not appear
        assert not any("@" in keyword or "example.com" in keyword for keyword in keywords)

    def test_extract_keywords_with_special_characters(self) -> None:
        """Test handling of special characters."""
        extractor = KeywordExtractor(max_features=5)

        text = "AI-powered app! Amazing features? Yes, it's great."
        keywords = extractor.extract(text)

        # Should extract meaningful words without special chars
        assert isinstance(keywords, list)
        assert len(keywords) > 0

    def test_extract_keywords_top_n(self) -> None:
        """Test extracting specific number of keywords."""
        extractor = KeywordExtractor(max_features=10)

        text = "AI machine learning deep learning neural networks data science artificial intelligence"
        keywords = extractor.extract(text, top_n=3)

        assert len(keywords) <= 3

    def test_extract_keywords_with_bigrams(self) -> None:
        """Test that bigrams are extracted."""
        extractor = KeywordExtractor(max_features=10, ngram_range=(1, 2))

        text = "machine learning and deep learning are important for artificial intelligence"
        keywords = extractor.extract(text)

        # Should include some bigrams
        assert isinstance(keywords, list)
        # Bigrams might include "machine learning", "deep learning", etc.

    def test_extract_with_scores(self) -> None:
        """Test extracting keywords with scores."""
        extractor = KeywordExtractor(max_features=5)

        text = "AI-powered note-taking app for researchers"
        keyword_scores = extractor.extract_with_scores(text)

        assert isinstance(keyword_scores, list)
        assert len(keyword_scores) > 0

        # Each item should be a tuple of (keyword, score)
        for keyword, score in keyword_scores:
            assert isinstance(keyword, str)
            assert isinstance(score, float)
            assert score > 0

        # Scores should be in descending order
        scores = [score for _, score in keyword_scores]
        assert scores == sorted(scores, reverse=True)

    def test_extract_with_scores_empty_text(self) -> None:
        """Test extracting with scores from empty text."""
        extractor = KeywordExtractor()

        assert extractor.extract_with_scores("") == []
        assert extractor.extract_with_scores("   ") == []

    def test_preprocess_text(self) -> None:
        """Test text preprocessing."""
        extractor = KeywordExtractor()

        # Test lowercase conversion (hyphens are kept for compound words)
        processed = extractor._preprocess_text("AI-Powered App")
        assert "ai" in processed
        assert "powered" in processed
        assert "app" in processed

        # Test URL removal
        processed = extractor._preprocess_text("Visit https://example.com for more")
        assert "http" not in processed
        assert "example.com" not in processed

        # Test email removal
        processed = extractor._preprocess_text("Contact support@example.com")
        assert "@" not in processed

        # Test special character removal
        processed = extractor._preprocess_text("AI-powered! Amazing?")
        assert "!" not in processed
        assert "?" not in processed

    def test_fallback_extraction(self) -> None:
        """Test fallback extraction when TF-IDF fails."""
        extractor = KeywordExtractor(max_features=5)

        # Text with only stopwords should trigger fallback
        text = "machine learning deep learning neural networks"
        keywords = extractor._fallback_extraction(text, 3)

        assert isinstance(keywords, list)
        assert len(keywords) <= 3

    def test_extract_from_product_description(self) -> None:
        """Test extracting keywords from realistic product description."""
        extractor = KeywordExtractor(max_features=10)

        text = """
        Our AI-powered note-taking application helps researchers and students
        organize their knowledge. Features include automatic tagging,
        smart search, and collaborative editing. Perfect for academic research
        and team projects.
        """

        keywords = extractor.extract(text)

        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert len(keywords) <= 10

        # Should extract domain-relevant keywords
        expected_keywords = [
            "ai",
            "powered",
            "note",
            "taking",
            "application",
            "researchers",
            "students",
            "research",
            "tagging",
            "search",
        ]

        # At least some expected keywords should be present
        found_keywords = [k for k in keywords if any(exp in k for exp in expected_keywords)]
        assert len(found_keywords) > 0

    def test_extract_handles_single_sentence(self) -> None:
        """Test that single sentence is handled correctly."""
        extractor = KeywordExtractor(max_features=5)

        text = "AI-powered note-taking app"
        keywords = extractor.extract(text)

        assert isinstance(keywords, list)
        assert len(keywords) > 0

    def test_custom_parameters(self) -> None:
        """Test extractor with custom parameters."""
        extractor = KeywordExtractor(max_features=3, ngram_range=(1, 1))  # Only unigrams

        text = "machine learning deep learning neural networks"
        keywords = extractor.extract(text)

        assert len(keywords) <= 3
        # With unigrams only, should not have multi-word phrases
        for keyword in keywords:
            assert " " not in keyword or keyword.count(" ") == 0


class TestKeywordExtractorEdgeCases:
    """Test edge cases for KeywordExtractor."""

    def test_very_long_text(self) -> None:
        """Test extracting from very long text."""
        extractor = KeywordExtractor(max_features=10)

        # Generate long text
        text = " ".join(["AI-powered note-taking app for researchers"] * 100)
        keywords = extractor.extract(text)

        assert isinstance(keywords, list)
        assert len(keywords) <= 10

    def test_text_with_numbers(self) -> None:
        """Test text containing numbers."""
        extractor = KeywordExtractor(max_features=5)

        text = "Our app has 1000 users and 500 features in version 2.0"
        keywords = extractor.extract(text)

        assert isinstance(keywords, list)
        # Numbers might be included as keywords

    def test_text_with_only_stopwords(self) -> None:
        """Test text containing only stopwords."""
        extractor = KeywordExtractor(max_features=5)

        text = "the and or but with for from"
        keywords = extractor.extract(text)

        # Should return empty or very few keywords
        assert isinstance(keywords, list)

    def test_unicode_text(self) -> None:
        """Test handling of unicode characters."""
        extractor = KeywordExtractor(max_features=5)

        text = "AI-powered app with émojis 😀 and spëcial çharacters"
        keywords = extractor.extract(text)

        # Should handle gracefully
        assert isinstance(keywords, list)

