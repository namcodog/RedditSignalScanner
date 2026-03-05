"""Tests for Phase 5.2 score_with_needs() method."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from app.services.analysis.opportunity_scorer import (
    OpportunityScorer,
    NeedEnrichedScore,
    NEED_WEIGHTS,
)


class TestScoreWithNeedsBasic:
    """Basic unit tests without database."""

    def test_empty_post_ids_returns_minimal_score(self) -> None:
        """Empty post list should return intent-only score."""
        scorer = OpportunityScorer()
        result = scorer.score_with_needs([], intent_score=0.5)
        
        assert isinstance(result, NeedEnrichedScore)
        assert result.final_score == pytest.approx(0.125, abs=0.01)  # 0.5 * 0.25
        assert result.intent_score == 0.5
        assert result.need_score == 0.0
        assert result.post_count == 0

    def test_need_weights_have_correct_values(self) -> None:
        """Verify the user-confirmed weights."""
        assert NEED_WEIGHTS["Efficiency"] == 2.5
        assert NEED_WEIGHTS["Survival"] == 1.5
        assert NEED_WEIGHTS["Growth"] == 1.2
        assert NEED_WEIGHTS["Belonging"] == 0.5
        assert NEED_WEIGHTS["Aesthetic"] == 0.5


class TestScoreWithNeedsIntegration:
    """Integration tests with mocked database."""

    @patch("app.services.analysis.opportunity_scorer.create_engine")
    @patch("app.services.analysis.opportunity_scorer.get_settings")
    def test_efficiency_posts_get_highest_score(
        self, mock_settings: MagicMock, mock_engine: MagicMock
    ) -> None:
        """Posts with Efficiency category should score higher than others."""
        # Mock settings
        mock_settings.return_value = MagicMock(
            database_url="postgresql+asyncpg://localhost/test"
        )
        
        # Mock DB rows: 100% Efficiency posts
        mock_rows = [
            {"l1_category": "Efficiency", "l1_secondary": None, "sentiment_score": 0.1},
            {"l1_category": "Efficiency", "l1_secondary": None, "sentiment_score": 0.2},
        ]
        mock_conn = MagicMock()
        mock_conn.execute.return_value.mappings.return_value.all.return_value = mock_rows
        mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
        
        scorer = OpportunityScorer()
        result = scorer.score_with_needs([1, 2], intent_score=0.5)
        
        # 100% Efficiency → need_score = 2.5/2.5 = 1.0
        # Final = 0.5*0.25 + 1.0*0.50 + 0.05*0.25 = 0.125 + 0.5 + 0.0125 = 0.6375
        assert result.need_score == pytest.approx(1.0, abs=0.01)
        assert result.final_score > 0.6
        assert result.need_breakdown.get("Efficiency") == 2
        assert result.post_count == 2

    @patch("app.services.analysis.opportunity_scorer.create_engine")
    @patch("app.services.analysis.opportunity_scorer.get_settings")
    def test_survival_posts_with_negative_sentiment_get_bonus(
        self, mock_settings: MagicMock, mock_engine: MagicMock
    ) -> None:
        """Survival posts with negative sentiment should get sentiment bonus."""
        mock_settings.return_value = MagicMock(
            database_url="postgresql+asyncpg://localhost/test"
        )
        
        # Mock DB rows: Survival posts with negative sentiment
        mock_rows = [
            {"l1_category": "Survival", "l1_secondary": None, "sentiment_score": -0.5},
            {"l1_category": "Survival", "l1_secondary": None, "sentiment_score": -0.4},
        ]
        mock_conn = MagicMock()
        mock_conn.execute.return_value.mappings.return_value.all.return_value = mock_rows
        mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
        
        scorer = OpportunityScorer()
        result = scorer.score_with_needs([1, 2], intent_score=0.3)
        
        # avg_sentiment = -0.45 < -0.3 → sentiment_mod = 0.15
        assert result.sentiment_modifier == 0.15
        assert result.avg_sentiment < -0.3

    @patch("app.services.analysis.opportunity_scorer.create_engine")
    @patch("app.services.analysis.opportunity_scorer.get_settings")
    def test_dual_label_bonus_applied(
        self, mock_settings: MagicMock, mock_engine: MagicMock
    ) -> None:
        """Posts with Survival+Efficiency combo should get dual-label bonus."""
        mock_settings.return_value = MagicMock(
            database_url="postgresql+asyncpg://localhost/test"
        )
        
        # Mock DB rows: Survival primary with Efficiency secondary
        mock_rows = [
            {"l1_category": "Survival", "l1_secondary": "Efficiency", "sentiment_score": -0.2},
            {"l1_category": "Growth", "l1_secondary": "Efficiency", "sentiment_score": 0.1},
        ]
        mock_conn = MagicMock()
        mock_conn.execute.return_value.mappings.return_value.all.return_value = mock_rows
        mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
        
        scorer = OpportunityScorer()
        result = scorer.score_with_needs([1, 2], intent_score=0.5)
        
        # Both posts have Efficiency as secondary when primary is Survival/Growth
        # dual_bonus = (2/2) * 0.1 = 0.1
        assert result.dual_label_bonus == pytest.approx(0.1, abs=0.01)

    @patch("app.services.analysis.opportunity_scorer.create_engine")
    @patch("app.services.analysis.opportunity_scorer.get_settings")
    def test_mixed_categories_weighted_correctly(
        self, mock_settings: MagicMock, mock_engine: MagicMock
    ) -> None:
        """Mixed category posts should have weighted average score."""
        mock_settings.return_value = MagicMock(
            database_url="postgresql+asyncpg://localhost/test"
        )
        
        # Mock: 50% Efficiency + 50% Belonging
        mock_rows = [
            {"l1_category": "Efficiency", "l1_secondary": None, "sentiment_score": 0.0},
            {"l1_category": "Belonging", "l1_secondary": None, "sentiment_score": 0.0},
        ]
        mock_conn = MagicMock()
        mock_conn.execute.return_value.mappings.return_value.all.return_value = mock_rows
        mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
        
        scorer = OpportunityScorer()
        result = scorer.score_with_needs([1, 2], intent_score=0.0)
        
        # raw_need = 0.5*2.5 + 0.5*0.5 = 1.25 + 0.25 = 1.5
        # need_score = 1.5 / 2.5 = 0.6
        assert result.need_score == pytest.approx(0.6, abs=0.01)
        assert result.need_breakdown.get("Efficiency") == 1
        assert result.need_breakdown.get("Belonging") == 1
