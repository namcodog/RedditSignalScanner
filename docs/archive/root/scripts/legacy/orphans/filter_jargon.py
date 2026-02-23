#!/usr/bin/env python3
"""
Filter noise from jargon_candidates.csv to reveal true gems.
"""
import csv
import re
from pathlib import Path

INPUT_FILE = Path("backend/backend/reports/jargon_candidates.csv")
OUTPUT_FILE = Path("backend/reports/jargon_clean.csv")

# 1. Hard Kill List (Bot & Reddit Meta)
BLACKLIST = {
    "bot", "moderator", "subreddit", "message", "compose", "question", "concern",
    "remove", "delete", "thread", "wiki", "sidebar", "rule", "megathread",
    "discord", "server", "link", "click", "check", "read", "guy", "thanks",
    "video", "gif", "giphy", "submission", "guideline", "contact", "automatically",
    "performed", "action", "am", "pm", "st", "nd", "rd", "th"
}

# 2. Grammar Junk (Verbs/Pronouns starts/ends)
# We remove phrases starting/ending with these
BAD_STARTS = {"we", "i", "you", "he", "she", "it", "they", "my", "your", "our", "this", "that", "these", "those", "is", "are", "was", "were", "be", "been", "do", "does", "did", "can", "could", "will", "would", "should", "ve", "re", "ll", "don", "didn", "doesn", "isn", "aren", "wasn", "weren", "haven", "hasn", "hadn", "won", "wouldn", "any", "some", "many", "much", "more", "less", "few", "lot", "bit", "other", "another", "same", "different", "such", "own", "very", "really", "just", "even", "still", "back", "now", "here", "there", "where", "when", "why", "how", "what", "who", "which"}
BAD_ENDS = BAD_STARTS | {"on", "in", "at", "to", "for", "of", "with", "about", "by", "from", "up", "down", "out", "off", "over", "under", "again", "then", "once", "too", "also", "either", "neither", "well", "sure", "enough", "able", "done", "seen", "gone", "got", "had", "made", "said", "told", "thought", "knew", "wanted", "needed", "used", "tried"}

# 3. Business Boost (Keep these even if they look weak, unless blacklisted)
BUSINESS_KEYWORDS = {
    "tax", "fee", "cost", "pay", "money", "cash", "profit", "margin", "loss",
    "ship", "deliver", "return", "refund", "track", "logistics", "customs",
    "account", "verify", "suspend", "ban", "risk", "scam", "fraud",
    "sell", "buy", "product", "item", "stock", "inventory", "source",
    "brand", "label", "private", "white", "retail", "wholesale",
    "client", "customer", "supplier", "vendor", "agent", "service",
    "plan", "policy", "invoice", "receipt", "document"
}

def is_junk(phrase: str) -> bool:
    words = phrase.lower().split()
    if not words: return True
    
    # Check blacklist
    for w in words:
        if w in BLACKLIST:
            return True
            
    # Check starts/ends
    if words[0] in BAD_STARTS or words[-1] in BAD_ENDS:
        return True
        
    # Check single letters
    if any(len(w) < 2 for w in words):
        return True
        
    return False

def has_business_value(phrase: str) -> bool:
    for w in phrase.lower().split():
        for kw in BUSINESS_KEYWORDS:
            if kw in w:
                return True
    return False

def clean_jargon():
    if not INPUT_FILE.exists():
        print(f"❌ Input file not found: {INPUT_FILE}")
        # Try fallback path just in case
        fallback = Path("backend/reports/jargon_candidates.csv")
        if fallback.exists():
            input_path = fallback
        else:
            return

    print(f"🧹 Cleaning {INPUT_FILE}...")
    
    cleaned_rows = []
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            phrase = row["phrase"]
            freq = int(row["frequency"])
            
            if is_junk(phrase):
                continue
                
            # If not junk, we keep it.
            # Optionally: boost rank if business value?
            # For now, just filtering.
            
            cleaned_rows.append(row)
    
    # Sort output (should already be sorted, but just in case)
    # We can also prioritize business keywords here
    cleaned_rows.sort(key=lambda x: (not has_business_value(x["phrase"]), -int(x["frequency"])))
    
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["phrase", "frequency", "is_known"])
        writer.writeheader()
        writer.writerows(cleaned_rows)
        
    print(f"✨ Cleaned list saved to {OUTPUT_FILE}. Count: {len(cleaned_rows)}")

if __name__ == "__main__":
    clean_jargon()
