import sys
import os
import psycopg2
from psycopg2.extras import execute_values

# Add backend directory to path to import utils if needed, but for this standalone script we'll just use psycopg2
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Database connection
DB_DSN = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/reddit_signal_scanner")

# Lists extracted from user feedback (OCR/Context)
# YELLOW: To be cleared (Deleted)
YELLOW_COMMUNITIES = [
    'r/amazonmerch', 'r/amazonreviews', 'r/amazonprimedeals', 'r/amazonwtf', 
    'r/peopleofwalmart', 'r/tiktokshopsellers', 'r/suppliersinusa', 'r/merchbyamazon', 
    'r/tiktok_shop_sellers', 'r/etsyuk', 'r/walmartassociates', 'r/amazonbfafornewbies', 
    'r/privatelabelsellers', 'r/amazonwarehouse', 'r/lazadareviews', 'r/bestbuyaliexpress', 
    'r/fbasourcing', 'r/achadinhosdashopeeebr', 'r/shopify_users', 'r/randomactsofetsy', 
    'r/aliexpressreviews', 'r/angelnmtaliexpress', 'r/amazonanswers', 'r/antiamazon', 
    'r/etsycirclejerk', 'r/amazonunder5', 'r/walmartworkers', 'r/wtf_amazon', 
    'r/amazonkdp', 'r/amazonflex', 'r/news_walmart', 'r/dropshippingservice', 
    'r/dropshippingninja', 'r/dropshippingbiz', 'r/anywherebutamazon', 'r/ecommercefulfillment', 
    'r/etsyadvertise', 'r/etsylistings', 'r/etsystrike', 'r/amazonwfshoppers', 
    'r/amazonsellers', 'r/walmarthealth', 'r/walmartpeople'
]

# GREEN: Valuable but 0 data. Need to be UPGRADED to Tier 2 (Medium) and ACTIVATED.
GREEN_COMMUNITIES = [
    'r/smallbusiness', 'r/startups', 'r/matcha', 'r/watchhorology', 'r/shopifydevelopment', 
    'r/sellingonamazonfba', 'r/etsyhelp', 'r/budgettravel', 'r/shoestringtravel', 
    'r/ultralightgear', 'r/kitchengadgets', 'r/coffeegear', 'r/uscreditcards', 
    'r/childfree', 'r/relationship_advice', 'r/hiking', 'r/smoking', 'r/cordlesstools', 
    'r/food', 'r/tea', 'r/espresso', 'r/frugal', 'r/leanfire', 'r/eatcheapandhealthy', 
    'r/mealprepsunday', 'r/cooking', 'r/askculinary', 'r/running', 'r/cycling', 
    'r/financialindependence', 'r/organization', 'r/buyitforlife', 'r/simpleliving', 
    'r/digitalnomad', 'r/travel', 'r/solotravel', 'r/gadgets', 'r/churning', 'r/diy', 
    'r/parenting', 'r/survival', 'r/outdoors', 'r/askwomen', 'r/homeimprovement', 
    'r/thriftstorehauls', 'r/entrepreneur', 'r/watches', 'r/3dprinting', 'r/campingandhiking', 
    'r/mommit', 'r/coffee', 'r/grilling', 'r/trueoffmychest', 'r/teachers', 'r/cleaningtips', 
    'r/mechanicadvice', 'r/ukpersonalfinance', 'r/pizza', 'r/kitchenconfidential', 
    'r/mechanicalkeyboards', 'r/homedecorating', 'r/hydrohomies', 'r/zerowaste', 
    'r/breadit', 'r/interiordesign', 'r/autodetailing', 'r/tools', 'r/cheap_meals', 
    'r/ultralight', 'r/marriage', 'r/homeowners', 'r/woodworking', 'r/landscaping', 
    'r/gardening', 'r/houseplants', 'r/homeautomation', 'r/smarthome', 'r/metalworking', 
    'r/personalfinance', 'r/frugalmalefashion', 'r/minimalism', 'r/bicycling', 
    'r/climbing', 'r/backpacking', 'r/onebag'
]

def main():
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()

    try:
        print("--- Starting Tier Mismatch Fix ---")

        # 1. DELETE Yellow Communities
        # We will Delete them from community_pool. 
        # (Cascade will handle cache/discovered, but we might want to be careful if they have posts).
        # User said "directly cleared", implying DELETE.
        
        print(f"\n1. Cleaning {len(YELLOW_COMMUNITIES)} Yellow (Noise) communities...")
        
        # Check if they have data first (Just for logging)
        cur.execute("SELECT community_name, posts_cached FROM community_cache WHERE community_name = ANY(%s)", (YELLOW_COMMUNITIES,))
        existing_data = cur.fetchall()
        for name, count in existing_data:
            if count > 0:
                print(f"  - Warning: {name} has {count} cached posts. Deleting anyway per user request.")

        # Execute DELETE
        cur.execute("DELETE FROM community_pool WHERE name = ANY(%s)", (YELLOW_COMMUNITIES,))
        deleted_count = cur.rowcount
        print(f"  - Deleted {deleted_count} communities from pool.")


        # 2. UPGRADE Green Communities
        print(f"\n2. Upgrading {len(GREEN_COMMUNITIES)} Green (Valuable) communities...")
        
        # Update Logic:
        # - Set tier = 'medium' (Tier 2)
        # - Set is_active = true
        # - Set priority = 'high'
        # - Ensure they exist (if some are missing, we might need to insert them, but assuming they exist for now)
        
        cur.execute("""
            UPDATE community_pool
            SET tier = 'medium',
                is_active = true,
                priority = 'high',
                updated_at = NOW()
            WHERE name = ANY(%s)
        """, (GREEN_COMMUNITIES,))
        
        updated_count = cur.rowcount
        print(f"  - Updated {updated_count} communities in pool.")

        # 3. FORCE RE-CRAWL
        # Reset last_crawled_at in cache to NULL to trigger immediate pickup
        cur.execute("""
            UPDATE community_cache
            SET last_crawled_at = NULL,
                crawl_priority = 1,
                is_active = true
            WHERE community_name = ANY(%s)
        """, (GREEN_COMMUNITIES,))
        
        cache_updated = cur.rowcount
        print(f"  - Reset crawl timer for {cache_updated} communities in cache.")
        
        conn.commit()
        print("\n--- SUCCESS: Fix Complete ---")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
