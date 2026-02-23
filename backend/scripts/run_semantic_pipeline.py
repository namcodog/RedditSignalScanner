#!/usr/bin/env python3
"""
Semantic Pipeline Runner
------------------------
Standardized entry point for the Human Needs Graph tagging system (Phase 3.6).

Usage:
    python backend/scripts/run_semantic_pipeline.py --limit 1000
    python backend/scripts/run_semantic_pipeline.py --refresh-all
"""
import argparse
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.semantic.smart_tagger import SemanticTagger
from sqlalchemy import text


def main():
    parser = argparse.ArgumentParser(description="Reddit Signal Scanner - Semantic Pipeline")
    parser.add_argument("--limit", type=int, default=1000, help="Number of posts to process (for incremental runs)")
    parser.add_argument("--refresh-all", action="store_true", help="Force refresh ALL existing labels (Full Re-tagging)")
    parser.add_argument("--verbose", action="store_true", help="Show detailed progress")
    args = parser.parse_args()

    print("🚀 Initializing Semantic Tagger (Phase 3.6 Engine)...")
    start_time = time.time()
    
    try:
        tagger = SemanticTagger()
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        sys.exit(1)
        
    print(f"✅ Engine ready. Loaded rules and VADER sentiment analyzer.")

    if args.refresh_all:
        print("⚠️  Starting FULL REFRESH of all semantic labels...")
        
        # 1. Fetch all IDs
        with tagger._engine.connect() as conn:
            # We fetch from post_semantic_labels to update existing ones, 
            # or posts_raw if we want to ensure 100% coverage. 
            # Let's fetch from posts_raw to be safe (coverage guarantee).
            print("   Fetching post IDs from posts_raw...")
            rows = conn.execute(
                text("SELECT id FROM posts_raw WHERE is_current = true ORDER BY id DESC")
            ).scalars().all()
        
        total = len(rows)
        print(f"   Found {total} active posts to process.")
        
        # 2. Process Loop
        processed = 0
        errors = 0
        
        for i, pid in enumerate(rows):
            try:
                tagger.process_single(pid)
                processed += 1
            except Exception as e:
                errors += 1
                if args.verbose:
                    print(f"   Error processing post {pid}: {e}")
            
            if (i + 1) % 1000 == 0:
                elapsed = time.time() - start_time
                rate = processed / elapsed
                print(f"   [{i+1}/{total}] Processed. Rate: {rate:.1f} posts/sec. Errors: {errors}")
                
        print(f"✅ Full refresh completed in {time.time() - start_time:.1f}s.")
        print(f"   Total: {total}, Errors: {errors}")

    else:
        print(f"▶️  Starting BATCH TAGGING (Limit: {args.limit})...")
        result = tagger.process_batch(limit=args.limit)
        print(f"✅ Batch completed in {time.time() - start_time:.1f}s.")
        print(f"   Stats: {result}")


if __name__ == "__main__":
    main()
