
import asyncio
import sys
from pathlib import Path
from sqlalchemy import text
from backend.app.db.session import SessionFactory

# Ensure backend is in pythonpath
sys.path.append(str(Path.cwd()))

# Priority Order: Check specific verticals first to avoid generic overlaps
VERTICALS_ORDERED = [
    ("Ecommerce_Business", ["shopify", "amazon", "ecommerce", "dropship", "fba", "marketing", "business", "entrepreneur", "sales", "seo", "ppc", "advertising", "smallbusiness", "startup", "freelance", "sideproject", "saas", "productmanagement", "growthhacking"]),
    ("Tools_EDC", ["edc", "knife", "knives", "flashlight", "tool", "gear", "carry", "leatherman", "multitool", "tactical", "watch", "pen", "gadgets", "lockpicking", "preppers", "3dprinting"]),
    ("Minimal_Outdoor", ["camping", "hiking", "ultralight", "onebag", "outdoors", "wilderness", "survival", "bushcraft", "backpacking", "travel", "vanlife", "mountaineering", "trailrunning", "cycling", "bicycling", "bikepacking", "running", "climbing"]),
    ("Family_Parenting", ["parenting", "mom", "dad", "baby", "pregnancy", "kid", "toddler", "daddit", "mommit", "family", "child", "marriage", "divorce", "relationship", "education", "homeschool"]),
    ("Food_Coffee_Lifestyle", ["coffee", "espresso", "barista", "food", "cooking", "baking", "tea", "kitchen", "recipe", "grilling", "sousvide", "bbq", "beer", "wine", "cocktails", "breadit", "fermentation", "matcha", "pourover", "smoking"]),
    ("Frugal_Living", ["frugal", "povertyfinance", "buyitforlife", "budget", "saving", "finance", "money", "deal", "coupon", "thrift", "fire", "leanfire", "financialindependence", "personalfinance", "eatcheap", "zerowaste", "minimalism", "simpleliving"]),
    ("Home_Lifestyle", ["home", "cleaning", "organizing", "interior", "decor", "diy", "gardening", "house", "furniture", "living", "homestead", "appliances", "carpentry", "electricians", "plumbing", "remodel", "woodworking", "fixit", "handyman", "solar", "smarthome", "houseplants", "landscaping"])
]

# Explicit overrides for known tricky ones
OVERRIDES = {
    "r/digitalnomad": "Minimal_Outdoor", # Travel focus
    "r/askwomen": "Home_Lifestyle", # Broad lifestyle/relationships
    "r/bestaliexpressfinds": "Ecommerce_Business", # Product sourcing
    "r/workbenches": "Tools_EDC",
    "r/metalworking": "Tools_EDC",
    "r/mechanicalkeyboards": "Tools_EDC", # Gear/Tech
    # --- New Fixes for 35 Unknowns ---
    "r/aliexpress": "Ecommerce_Business",
    "r/aliexpressbr": "Ecommerce_Business",
    "r/etsy": "Ecommerce_Business",
    "r/etsysellers": "Ecommerce_Business",
    "r/stickerstore": "Ecommerce_Business",
    "r/printondemand": "Ecommerce_Business",
    "r/facebookads": "Ecommerce_Business",
    "r/tiktokshop": "Ecommerce_Business",
    "r/tiktokshopsellersclub": "Ecommerce_Business",
    "r/logistics": "Ecommerce_Business",
    "r/flipping": "Ecommerce_Business",
    "r/legomarket": "Ecommerce_Business",
    "r/walmartsellers": "Ecommerce_Business",
    "r/walmart_rx": "Ecommerce_Business", # Pharmacy business/work
    "r/instacartshoppers": "Frugal_Living", # Gig economy/earning
    "r/walmart": "Frugal_Living", # Shopping/General
    "r/walmartcanada": "Frugal_Living",
    "r/walmartemployees": "Frugal_Living", # Work/Life
    "r/peopleofwalmart": "Frugal_Living", # Humor/Lifestyle
    "r/mechanicadvice": "Tools_EDC",
    "r/autodetailing": "Tools_EDC",
    "r/askculinary": "Food_Coffee_Lifestyle",
    "r/cheap_meals": "Food_Coffee_Lifestyle", # Or Frugal, but Food is stronger
    "r/hydrohomies": "Food_Coffee_Lifestyle",
    "r/beyondthebump": "Family_Parenting",
    "r/blendedfamilies": "Family_Parenting",
    "r/stepparents": "Family_Parenting",
    "r/raisedbynarcissists": "Family_Parenting",
    "r/amitheasshole": "Family_Parenting", # Relationships
    "r/askmen": "Family_Parenting", # Relationships/Advice
    "r/trueoffmychest": "Family_Parenting", # Emotional/Life
    "r/vent": "Family_Parenting",
    "r/spellcasterreviews": "Home_Lifestyle", # Esoteric/Niche
    "r/overlanding": "Minimal_Outdoor",
    "r/ikeahacks": "Home_Lifestyle",
    # --------------------------------
    "r/churning": "Frugal_Living",
    "r/1200isplenty": "Food_Coffee_Lifestyle",
    "r/loseit": "Food_Coffee_Lifestyle",
    "r/nutrition": "Food_Coffee_Lifestyle",
    "r/sourdough": "Food_Coffee_Lifestyle",
    "r/castiron": "Food_Coffee_Lifestyle",
    "r/airfryer": "Food_Coffee_Lifestyle",
    "r/instantpot": "Food_Coffee_Lifestyle",
    "r/slowcooking": "Food_Coffee_Lifestyle",
    "r/mealprep": "Frugal_Living",
    "r/mealprepsunday": "Frugal_Living",
    "r/eatcheapandhealthy": "Frugal_Living",
    "r/budgetfood": "Frugal_Living",
    "r/beermoney": "Frugal_Living",
    "r/cordcutters": "Frugal_Living",
    "r/upcycling": "Frugal_Living",
    "r/declutter": "Home_Lifestyle",
    "r/konmari": "Home_Lifestyle",
    "r/hoarding": "Home_Lifestyle",
    "r/cleaning": "Home_Lifestyle",
    "r/laundry": "Home_Lifestyle",
    "r/roomporn": "Home_Lifestyle",
    "r/amateurroomporn": "Home_Lifestyle",
    "r/male101": "Home_Lifestyle", # Often decor/living
    "r/malelivingspace": "Home_Lifestyle",
    "r/femalelivingspace": "Home_Lifestyle",
    "r/cozyplaces": "Home_Lifestyle",
    "r/gardening": "Home_Lifestyle",
    "r/indoorplants": "Home_Lifestyle",
    "r/plantclinic": "Home_Lifestyle",
    "r/succulents": "Home_Lifestyle",
    "r/lawncare": "Home_Lifestyle",
    "r/landscaping": "Home_Lifestyle",
    "r/permaculture": "Home_Lifestyle",
    "r/homestead": "Home_Lifestyle",
    "r/offgrid": "Home_Lifestyle",
    "r/renovation": "Home_Lifestyle",
    "r/homerenovation": "Home_Lifestyle",
    "r/realestate": "Frugal_Living", # Investment/Finance
    "r/realestateinvesting": "Frugal_Living",
    "r/landlord": "Frugal_Living",
    "r/airbnb": "Ecommerce_Business", # Hosting business
    "r/construction": "Home_Lifestyle",
    "r/contractor": "Home_Lifestyle",
    "r/decks": "Home_Lifestyle",
    "r/roofing": "Home_Lifestyle",
    "r/hvac": "Home_Lifestyle",
    "r/flooring": "Home_Lifestyle",
    "r/tile": "Home_Lifestyle",
    "r/paint": "Home_Lifestyle",
    "r/drywall": "Home_Lifestyle",
    "r/concrete": "Home_Lifestyle",
    "r/masonry": "Home_Lifestyle",
    "r/welding": "Tools_EDC",
    "r/machinists": "Tools_EDC",
    "r/blacksmith": "Tools_EDC",
    "r/bladesmith": "Tools_EDC",
    "r/knifemaking": "Tools_EDC",
    "r/sharpening": "Tools_EDC",
    "r/axes": "Tools_EDC",
    "r/swords": "Tools_EDC",
    "r/archery": "Minimal_Outdoor",
    "r/fishing": "Minimal_Outdoor",
    "r/flyfishing": "Minimal_Outdoor",
    "r/hunting": "Minimal_Outdoor",
    "r/camping": "Minimal_Outdoor",
    "r/campinggear": "Minimal_Outdoor",
    "r/canoecamping": "Minimal_Outdoor",
    "r/kayaking": "Minimal_Outdoor",
    "r/canoeing": "Minimal_Outdoor",
    "r/sup": "Minimal_Outdoor",
    "r/sailing": "Minimal_Outdoor",
    "r/boating": "Minimal_Outdoor",
    "r/scuba": "Minimal_Outdoor",
    "r/freediving": "Minimal_Outdoor",
    "r/spearfishing": "Minimal_Outdoor",
    "r/surfing": "Minimal_Outdoor",
    "r/climbing": "Minimal_Outdoor",
    "r/bouldering": "Minimal_Outdoor",
    "r/alpinism": "Minimal_Outdoor",
    "r/canyoneering": "Minimal_Outdoor",
    "r/caving": "Minimal_Outdoor",
    "r/skimo": "Minimal_Outdoor",
    "r/skiing": "Minimal_Outdoor",
    "r/snowboarding": "Minimal_Outdoor",
    "r/xcountryskiing": "Minimal_Outdoor",
    "r/iceclimbing": "Minimal_Outdoor",
    "r/trailrunning": "Minimal_Outdoor",
    "r/ultramarathon": "Minimal_Outdoor",
    "r/triathlon": "Minimal_Outdoor",
    "r/running": "Minimal_Outdoor",
    "r/jogging": "Minimal_Outdoor",
    "r/barefootrunning": "Minimal_Outdoor",
    "r/walking": "Minimal_Outdoor",
    "r/hiking": "Minimal_Outdoor",
    "r/backpacking": "Minimal_Outdoor",
    "r/mountaineering": "Minimal_Outdoor",
    "r/geology": "Minimal_Outdoor",
    "r/rockhounds": "Minimal_Outdoor",
    "r/fossilid": "Minimal_Outdoor",
    "r/astronomy": "Minimal_Outdoor",
    "r/stargazing": "Minimal_Outdoor",
    "r/telescopes": "Minimal_Outdoor",
    "r/binoculars": "Minimal_Outdoor",
    "r/birding": "Minimal_Outdoor",
    "r/ornithology": "Minimal_Outdoor",
    "r/whatsthisbird": "Minimal_Outdoor",
    "r/wildlife": "Minimal_Outdoor",
    "r/animaltracking": "Minimal_Outdoor",
    "r/botany": "Minimal_Outdoor",
    "r/whatsthisplant": "Minimal_Outdoor",
    "r/mycology": "Minimal_Outdoor",
    "r/shroomid": "Minimal_Outdoor",
    "r/foraging": "Minimal_Outdoor",
    "r/bushcraft": "Minimal_Outdoor",
    "r/survival": "Minimal_Outdoor", # Changed from Tools_EDC
    "r/preppers": "Frugal_Living", # Preparedness/Stockpiling often overlaps with Frugal/Bulk
    "r/bugout": "Minimal_Outdoor",
    "r/homestead": "Home_Lifestyle",
    "r/offgrid": "Home_Lifestyle",
    "r/selfsufficiency": "Home_Lifestyle",
    "r/solar": "Home_Lifestyle",
    "r/windenergy": "Home_Lifestyle",
    "r/hydroponics": "Home_Lifestyle",
    "r/aquaponics": "Home_Lifestyle",
    "r/aeroponics": "Home_Lifestyle",
    "r/urbanfarming": "Home_Lifestyle",
    "r/beekeeping": "Home_Lifestyle",
    "r/chickens": "Home_Lifestyle",
    "r/backyardchickens": "Home_Lifestyle",
    "r/quail": "Home_Lifestyle",
    "r/ducks": "Home_Lifestyle",
    "r/geese": "Home_Lifestyle",
    "r/goats": "Home_Lifestyle",
    "r/sheep": "Home_Lifestyle",
    "r/pigs": "Home_Lifestyle",
    "r/cows": "Home_Lifestyle",
    "r/horses": "Home_Lifestyle",
    "r/livestock": "Home_Lifestyle",
    "r/farming": "Home_Lifestyle",
    "r/agriculture": "Home_Lifestyle",
    "r/tractors": "Home_Lifestyle",
    "r/heavyequipment": "Home_Lifestyle",
}

async def generate_sql():
    async with SessionFactory() as session:
        query = text("SELECT name FROM community_pool ORDER BY name")
        rows = await session.execute(query)
        communities = [r.name for r in rows]
        
        updates = []
        unknowns = []
        
        for sub in communities:
            sub_lower = sub.lower()
            vertical = None
            
            # 1. Override
            if sub_lower in OVERRIDES:
                vertical = OVERRIDES[sub_lower]
            elif sub in OVERRIDES:
                vertical = OVERRIDES[sub]
            
            # 2. Heuristic
            if not vertical:
                for v, keywords in VERTICALS_ORDERED:
                    for k in keywords:
                        if k in sub_lower:
                            vertical = v
                            break
                    if vertical:
                        break
            
            # 3. Default fallback (if still unknown)
            if not vertical:
                # Based on user's known set, if it doesn't match, default to 'Home_Lifestyle' or 'Ecommerce_Business' based on probability?
                # Safer: 'Home_Lifestyle' as a catch-all for "Lifestyle" or leave NULL for manual check.
                # User said "一口气干完", so I should assign something.
                # Let's inspect the unknowns.
                unknowns.append(sub)
                vertical = "Home_Lifestyle" # Provisional Default
            
            json_val = f'["{vertical}"]'
            updates.append(f"UPDATE community_pool SET vertical = '{vertical}', categories = '{json_val}'::jsonb WHERE name = '{sub}';")

        # Write SQL file
        with open("update_verticals.sql", "w") as f:
            f.write("BEGIN;\n")
            f.write("\n".join(updates))
            f.write("\nCOMMIT;\n")
            
        print(f"Generated {len(updates)} update statements.")
        if unknowns:
            print(f"⚠️ {len(unknowns)} communities fell back to default 'Home_Lifestyle':")
            print(unknowns)

if __name__ == "__main__":
    asyncio.run(generate_sql())
