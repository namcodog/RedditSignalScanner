import pytest
from sqlalchemy import text
from app.services.analysis.opportunity_scorer import OpportunityScorer

@pytest.mark.asyncio
async def test_score_with_needs_integration(db_session):
    """
    Integration test for score_with_needs using a real (test) database.
    Verifies that Human Needs Graph logic correctly prioritizes Efficiency > Survival.
    """
    # 1. Setup: Insert test data
    # We need to insert into posts_raw first (FK constraint), then post_semantic_labels
    
    # Use raw SQL to bypass ORM complexity for setup
    await db_session.execute(text("DELETE FROM post_semantic_labels"))
    await db_session.execute(text("DELETE FROM posts_raw"))
    await db_session.execute(text("DELETE FROM authors"))
    
    # Create dummy author
    await db_session.execute(text("""
        INSERT INTO authors (author_id, author_name) VALUES ('test_auth', 'Test User')
    """))
    
    # Create 3 posts
    # 1: Efficiency (High Value)
    # 2: Survival (Medium Value)
    # 3: Belonging (Low Value)
    await db_session.execute(text("""
        INSERT INTO posts_raw (id, subreddit, title, author_id, is_current, version, source_post_id, created_at) 
        VALUES 
        (101, 'r/test', 'Need tool', 'test_auth', true, 1, 't3_101', NOW()),
        (102, 'r/test', 'I hate this', 'test_auth', true, 1, 't3_102', NOW()),
        (103, 'r/test', 'Look at my cat', 'test_auth', true, 1, 't3_103', NOW())
    """))
    
    # Create labels
    await db_session.execute(text("""
        INSERT INTO post_semantic_labels (post_id, l1_category, sentiment_score)
        VALUES 
        (101, 'Efficiency', 0.1),
        (102, 'Survival', -0.5),  -- Negative sentiment should boost score slightly
        (103, 'Belonging', 0.8)
    """))
    
    await db_session.commit()
    
    # 2. Execute: Call score_with_needs
    scorer = OpportunityScorer()
    
    # Test A: Score the Efficiency post
    res_eff = scorer.score_with_needs([101], intent_score=0.5)
    
    # Test B: Score the Survival post
    res_surv = scorer.score_with_needs([102], intent_score=0.5)
    
    # Test C: Score the Belonging post
    res_bel = scorer.score_with_needs([103], intent_score=0.5)
    
    # 3. Verify
    print(f"\nEfficiency Score: {res_eff.final_score} (Need: {res_eff.need_score})")
    print(f"Survival Score: {res_surv.final_score} (Need: {res_surv.need_score})")
    print(f"Belonging Score: {res_bel.final_score} (Need: {res_bel.need_score})")
    
    # Logic Check:
    # Efficiency (Weight 2.5) should be > Survival (Weight 1.5)
    assert res_eff.need_score > res_surv.need_score, "Efficiency should outscore Survival"
    
    # Survival (Weight 1.5) should be > Belonging (Weight 0.5)
    assert res_surv.need_score > res_bel.need_score, "Survival should outscore Belonging"
    
    # Sentiment Check:
    # Survival post has -0.5 sentiment -> should get sentiment bonus (+0.15)
    # Efficiency post has 0.1 sentiment -> no bonus (0.0)
    assert res_surv.sentiment_modifier == 0.15
    assert res_eff.sentiment_modifier == 0.0
    
    # Final Score Logic Check
    # Even with sentiment bonus, Efficiency * 2.5 is so strong it likely still wins or is close
    # Let's check the math:
    # Eff: Need(2.5/2.5=1.0)*0.5 + Intent(0.5)*0.25 + Sent(0)*0.25 = 0.5 + 0.125 + 0 = 0.625
    # Surv: Need(1.5/2.5=0.6)*0.5 + Intent(0.5)*0.25 + Sent(0.15)*0.25 = 0.3 + 0.125 + 0.0375 = 0.4625
    assert res_eff.final_score > res_surv.final_score

    # 4. Cleanup (Optional, fixture usually handles transaction rollback)
    await db_session.execute(text("DELETE FROM post_semantic_labels WHERE post_id IN (101, 102, 103)"))
    await db_session.execute(text("DELETE FROM posts_raw WHERE id IN (101, 102, 103)"))
    await db_session.commit()
