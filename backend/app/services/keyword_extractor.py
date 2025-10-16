"""Keyword Extraction Service using TF-IDF.

Extracts relevant keywords from product descriptions for community discovery.
"""

from __future__ import annotations

import re
from typing import List

from sklearn.feature_extraction.text import TfidfVectorizer


class KeywordExtractor:
    """Extract keywords from text using TF-IDF algorithm."""

    def __init__(
        self,
        max_features: int = 10,
        min_df: int = 1,
        max_df: float = 0.8,
        ngram_range: tuple[int, int] = (1, 2),
    ) -> None:
        """Initialize keyword extractor.

        Args:
            max_features: Maximum number of keywords to extract
            min_df: Minimum document frequency (ignore terms that appear in fewer documents)
            max_df: Maximum document frequency (ignore terms that appear in more than this fraction)
            ngram_range: Range of n-grams to consider (1, 2) means unigrams and bigrams
        """
        self.max_features = max_features
        self.min_df = min_df
        self.max_df = max_df
        self.ngram_range = ngram_range

        # English stopwords (common words to ignore)
        self.stopwords = {
            "a",
            "an",
            "and",
            "are",
            "as",
            "at",
            "be",
            "by",
            "for",
            "from",
            "has",
            "he",
            "in",
            "is",
            "it",
            "its",
            "of",
            "on",
            "that",
            "the",
            "to",
            "was",
            "will",
            "with",
            "we",
            "our",
            "you",
            "your",
            "this",
            "can",
            "have",
            "or",
            "but",
            "not",
            "they",
            "their",
            "what",
            "which",
            "who",
            "when",
            "where",
            "why",
            "how",
        }

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for keyword extraction.

        Args:
            text: Raw text to preprocess

        Returns:
            Preprocessed text
        """
        # Convert to lowercase
        text = text.lower()

        # Remove URLs
        text = re.sub(r"http\S+|www\S+", "", text)

        # Remove email addresses
        text = re.sub(r"\S+@\S+", "", text)

        # Remove special characters but keep spaces and hyphens
        text = re.sub(r"[^a-z0-9\s\-]", " ", text)

        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def extract(self, text: str, top_n: int | None = None) -> List[str]:
        """Extract keywords from text using TF-IDF.

        Args:
            text: Text to extract keywords from
            top_n: Number of top keywords to return (defaults to max_features)

        Returns:
            List of extracted keywords
        """
        if not text or not text.strip():
            return []

        # Preprocess text
        processed_text = self._preprocess_text(text)

        if not processed_text:
            return []

        # For single document, we need to split into sentences to create a corpus
        # This allows TF-IDF to work properly
        sentences = [s.strip() for s in re.split(r"[.!?]+", processed_text) if s.strip()]

        if not sentences:
            return []

        # If only one sentence, duplicate it to make TF-IDF work
        if len(sentences) == 1:
            sentences = sentences * 2

        try:
            # Create TF-IDF vectorizer
            vectorizer = TfidfVectorizer(
                max_features=top_n or self.max_features,
                min_df=self.min_df,
                max_df=self.max_df,
                ngram_range=self.ngram_range,
                stop_words=list(self.stopwords),
            )

            # Fit and transform
            tfidf_matrix = vectorizer.fit_transform(sentences)

            # Get feature names (keywords)
            feature_names = vectorizer.get_feature_names_out()

            # Calculate average TF-IDF scores across all sentences
            avg_scores = tfidf_matrix.mean(axis=0).A1

            # Sort by score
            sorted_indices = avg_scores.argsort()[::-1]

            # Get top keywords
            keywords = [feature_names[i] for i in sorted_indices if avg_scores[i] > 0]

            return keywords[: top_n or self.max_features]

        except ValueError:
            # If TF-IDF fails (e.g., all stopwords), fall back to simple word frequency
            return self._fallback_extraction(processed_text, top_n or self.max_features)

    def _fallback_extraction(self, text: str, top_n: int) -> List[str]:
        """Fallback keyword extraction using simple word frequency.

        Args:
            text: Preprocessed text
            top_n: Number of keywords to return

        Returns:
            List of keywords
        """
        # Split into words
        words = text.split()

        # Filter stopwords and short words
        words = [w for w in words if w not in self.stopwords and len(w) > 2]

        # Count frequency
        word_freq: dict[str, int] = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1

        # Sort by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

        # Return top N
        return [word for word, _ in sorted_words[:top_n]]

    def extract_with_scores(self, text: str, top_n: int | None = None) -> List[tuple[str, float]]:
        """Extract keywords with their TF-IDF scores.

        Args:
            text: Text to extract keywords from
            top_n: Number of top keywords to return

        Returns:
            List of (keyword, score) tuples
        """
        if not text or not text.strip():
            return []

        processed_text = self._preprocess_text(text)

        if not processed_text:
            return []

        sentences = [s.strip() for s in re.split(r"[.!?]+", processed_text) if s.strip()]

        if not sentences:
            return []

        if len(sentences) == 1:
            sentences = sentences * 2

        try:
            vectorizer = TfidfVectorizer(
                max_features=top_n or self.max_features,
                min_df=self.min_df,
                max_df=self.max_df,
                ngram_range=self.ngram_range,
                stop_words=list(self.stopwords),
            )

            tfidf_matrix = vectorizer.fit_transform(sentences)
            feature_names = vectorizer.get_feature_names_out()
            avg_scores = tfidf_matrix.mean(axis=0).A1

            # Create list of (keyword, score) tuples
            keyword_scores = [(feature_names[i], float(avg_scores[i])) for i in range(len(feature_names))]

            # Sort by score
            keyword_scores.sort(key=lambda x: x[1], reverse=True)

            # Filter out zero scores
            keyword_scores = [(k, s) for k, s in keyword_scores if s > 0]

            return keyword_scores[: top_n or self.max_features]

        except ValueError:
            # Fallback: return words with frequency as score
            words = self._fallback_extraction(processed_text, top_n or self.max_features)
            return [(word, 1.0) for word in words]


__all__ = ["KeywordExtractor"]

