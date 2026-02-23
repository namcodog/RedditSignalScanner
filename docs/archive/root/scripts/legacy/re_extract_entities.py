#!/usr/bin/env python3
"""
Phase D: Re-extract brand entities from all posts using competitor_layers.yml.

SAFETY: Only TRUNCATES `content_entities`. Other tables are untouched.
"""
import asyncio
import re
import yaml
from pathlib import Path
from sqlalchemy import text

from app.db.session import SessionFactory


# Ambiguous brand names that are also common English words (False Positive magnets)
AMBIGUOUS_BRANDS = {
    # Common words
    "kind", "case", "spot", "fellow", "brother", "heart", "material", "route",
    "flow", "zip", "can do", "medium", "signal", "bloom", "prime", "one",
    "element", "target", "nest", "anchor", "beam", "level", "peak", "core",
    "edge", "shift", "base", "frame", "blend", "balance", "focus", "drive",
    "orbit", "wave", "spark", "glow", "rise", "pure", "clear", "fresh",
    "smart", "live", "home", "simple", "modern", "classic", "standard",
    "digital", "video", "audio", "mobile", "cloud", "link", "connect",
    # Platforms/Channels that should stay separate (don't duplicate)
    "walmart", "target", "costco",  # These are in platforms, not brands
    # Generic tech terms
    "api", "app", "software", "tool", "machine", "system",
}


def load_entities_from_competitor_layers() -> dict[str, list[tuple[str, re.Pattern]]]:
    """Load brands, platforms, channels from competitor_layers.yml."""
    config_path = Path(__file__).parent.parent / "config" / "entity_dictionary" / "competitor_layers.yml"
    
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    layers = data.get("layers", {})
    
    result: dict[str, list[tuple[str, re.Pattern]]] = {
        "brand": [],
        "platform": [],
        "channel": [],
    }
    
    def build_patterns(aliases: list, entity_type: str) -> list[tuple[str, re.Pattern]]:
        patterns = []
        for alias in aliases:
            if not isinstance(alias, str) or len(alias) < 2:
                continue
            alias_lower = alias.lower()
            # Skip ambiguous brands (common words)
            if alias_lower in AMBIGUOUS_BRANDS:
                continue
            # Word boundary regex (case insensitive)
            escaped = re.escape(alias_lower)
            pat = re.compile(rf"\b{escaped}\b", re.IGNORECASE)
            patterns.append((alias_lower, pat))
        return patterns
    
    # Brands
    brands_section = layers.get("brands", {})
    brand_aliases = brands_section.get("aliases", [])
    result["brand"] = build_patterns(brand_aliases, "brand")
    print(f"  Loaded {len(result['brand'])} brand patterns.")
    
    # Platforms
    platforms_section = layers.get("platforms", {})
    platform_aliases = platforms_section.get("aliases", [])
    result["platform"] = build_patterns(platform_aliases, "platform")
    print(f"  Loaded {len(result['platform'])} platform patterns.")
    
    # Channels
    channels_section = layers.get("channels", {})
    channel_aliases = channels_section.get("aliases", [])
    result["channel"] = build_patterns(channel_aliases, "channel")
    print(f"  Loaded {len(result['channel'])} channel patterns.")
    
    return result


def extract_entities(text_content: str, patterns: dict[str, list[tuple[str, re.Pattern]]]) -> list[tuple[str, str]]:
    """Extract entities from text using precompiled patterns."""
    if not text_content:
        return []
    
    results: list[tuple[str, str]] = []
    text_lower = text_content.lower()
    
    for entity_type, pattern_list in patterns.items():
        for name, pat in pattern_list:
            if pat.search(text_lower):
                results.append((name, entity_type))
    
    return results


async def main():
    print("Phase D: Re-extracting brand entities from all posts and comments...")
    print("=" * 60)
    
    # 1. Load patterns
    print("Loading entity patterns from competitor_layers.yml...")
    patterns = load_entities_from_competitor_layers()
    total_patterns = sum(len(v) for v in patterns.values())
    print(f"Total patterns: {total_patterns}")
    
    async with SessionFactory() as session:
        # 2. TRUNCATE content_entities ONLY (Safety)
        print("\n⚠️ Truncating content_entities (ONLY this table)...")
        await session.execute(text("TRUNCATE TABLE content_entities RESTART IDENTITY CASCADE"))
        await session.commit()
        print("✅ Truncated. Other tables are safe.")
        
        # 3. Process posts_raw
        print("\n📄 Processing posts_raw...")
        posts_result = await session.execute(text("""
            SELECT id, COALESCE(title, '') || ' ' || COALESCE(body, '') AS text
            FROM posts_raw
            WHERE is_current = true
        """))
        posts = posts_result.fetchall()
        print(f"  Found {len(posts)} posts to process.")
        
        post_entities = 0
        for i, row in enumerate(posts):
            post_id = row.id
            text_content = row.text
            
            entities = extract_entities(text_content, patterns)
            for name, entity_type in entities:
                await session.execute(text("""
                    INSERT INTO content_entities (content_type, content_id, entity, entity_type, count)
                    VALUES ('post', :pid, :name, :etype, 1)
                    ON CONFLICT DO NOTHING
                """), {"pid": post_id, "name": name, "etype": entity_type})
                post_entities += 1
            
            if (i + 1) % 10000 == 0:
                await session.commit()
                print(f"  Processed {i + 1}/{len(posts)} posts, {post_entities} entities...")
        
        await session.commit()
        print(f"  ✅ Posts: {len(posts)} processed, {post_entities} entities extracted.")
        
        # 4. Process comments (optional, can be slow)
        print("\n💬 Processing comments...")
        comments_result = await session.execute(text("""
            SELECT id, COALESCE(body, '') AS text
            FROM comments
            LIMIT 500000
        """))
        comments = comments_result.fetchall()
        print(f"  Found {len(comments)} comments to process.")
        
        comment_entities = 0
        for i, row in enumerate(comments):
            comment_id = row.id
            text_content = row.text
            
            entities = extract_entities(text_content, patterns)
            for name, entity_type in entities:
                await session.execute(text("""
                    INSERT INTO content_entities (content_type, content_id, entity, entity_type, count)
                    VALUES ('comment', :cid, :name, :etype, 1)
                    ON CONFLICT DO NOTHING
                """), {"cid": comment_id, "name": name, "etype": entity_type})
                comment_entities += 1
            
            if (i + 1) % 50000 == 0:
                await session.commit()
                print(f"  Processed {i + 1}/{len(comments)} comments, {comment_entities} entities...")
        
        await session.commit()
        print(f"  ✅ Comments: {len(comments)} processed, {comment_entities} entities extracted.")
    
    print("\n" + "=" * 60)
    print(f"✅ Phase D Complete. Total entities: {post_entities + comment_entities}")


if __name__ == "__main__":
    asyncio.run(main())
