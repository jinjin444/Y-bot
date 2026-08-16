import os
import datetime
import random
import string
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

# MongoDB Connection
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb+srv://Tyr6hij:gufutihhh@cluster0.hdfqxfu.mongodb.net/?appName=Cluster0")
USE_MONGODB = os.environ.get("USE_MONGODB", "false").lower() == "true"

# MongoDB Client
_mongo_client = None
_db = None

async def get_mongo_db():
    global _mongo_client, _db
    if USE_MONGODB and MONGODB_URI:
        if _mongo_client is None:
            _mongo_client = AsyncIOMotorClient(MONGODB_URI)
            _db = _mongo_client["razorbot"]
        return _db
    return None

# ============ USER FUNCTIONS ============

def _coerce_user_id(value):
    """Return a valid Telegram numeric user ID, or None for invalid values."""
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "null", "nan"}:
        return None
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


async def ensure_user(user_id):
    user_id = _coerce_user_id(user_id)
    if user_id is None:
        return
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            existing = await db.users.find_one({"_id": str(user_id)})
            if not existing:
                await db.users.insert_one({
                    "_id": str(user_id),
                    "plan": "Bronze",
                    "expiry": None,
                    "banned": False,
                    "used_codes": []
                })
            return
    
    # JSON fallback for development
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    
    def load_db():
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                return json.load(f)
        return {"users": {}, "cards": [], "proxies": {}, "sites": {}, "plan_codes": {}}
    
    def save_db(data):
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
    
    db = load_db()
    if str(user_id) not in db["users"]:
        db["users"][str(user_id)] = {"plan": "Bronze", "expiry": None, "banned": False, "used_codes": []}
        save_db(db)

async def get_user_plan(user_id):
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            user = await db.users.find_one({"_id": str(user_id)})
            if user:
                plan = user.get("plan", "Bronze")
                expiry = user.get("expiry")
                if expiry and plan != "Bronze":
                    if isinstance(expiry, str):
                        expiry_date = datetime.datetime.fromisoformat(expiry)
                    else:
                        expiry_date = expiry
                    if expiry_date < datetime.datetime.now():
                        await db.users.update_one(
                            {"_id": str(user_id)},
                            {"$set": {"plan": "Bronze", "expiry": None}}
                        )
                        return "Bronze"
                return plan
    # JSON fallback
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            user = data["users"].get(str(user_id), {})
            return user.get("plan", "Bronze")
    return "Bronze"

async def set_user_plan(user_id, plan, days=0):
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            expiry = None
            if days > 0:
                expiry = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()
            
            await db.users.update_one(
                {"_id": str(user_id)},
                {"$set": {"plan": plan, "expiry": expiry}},
                upsert=True
            )
            return
    
    # JSON fallback
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    
    def load_db():
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                return json.load(f)
        return {"users": {}, "cards": [], "proxies": {}, "sites": {}, "plan_codes": {}}
    
    def save_db(data):
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
    
    db = load_db()
    expiry = None
    if days > 0:
        expiry = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()
    user = db["users"].get(str(user_id), {})
    used_codes = user.get("used_codes", [])
    db["users"][str(user_id)] = {"plan": plan, "expiry": expiry, "banned": user.get("banned", False), "used_codes": used_codes}
    save_db(db)

async def is_premium_user(user_id):
    plan = await get_user_plan(user_id)
    return plan in ["Trial", "1Day", "Core", "Elite", "Root", "X"]

async def is_banned_user(user_id):
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            user = await db.users.find_one({"_id": str(user_id)})
            return user.get("banned", False) if user else False
    
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            return data["users"].get(str(user_id), {}).get("banned", False)
    return False

# ============ get_user_info (added for /info) ============
async def get_user_info(user_id):
    """Return full user info dict (plan, expiry, banned, used_codes)."""
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            user = await db.users.find_one({"_id": str(user_id)})
            if user:
                return {
                    "plan": user.get("plan", "Bronze"),
                    "expiry": user.get("expiry"),
                    "banned": user.get("banned", False),
                    "used_codes": user.get("used_codes", [])
                }
            else:
                return {"plan": "Bronze", "expiry": None, "banned": False, "used_codes": []}
    # JSON fallback
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            user = data["users"].get(str(user_id), {})
            return {
                "plan": user.get("plan", "Bronze"),
                "expiry": user.get("expiry"),
                "banned": user.get("banned", False),
                "used_codes": user.get("used_codes", [])
            }
    return {"plan": "Bronze", "expiry": None, "banned": False, "used_codes": []}

# ============ CARD FUNCTIONS ============

async def save_card_to_db(card, status, response, gateway, price, user_id=None):
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            await db.cards.insert_one({
                "card": card,
                "status": status,
                "response": response,
                "gateway": gateway,
                "price": price,
                "user_id": str(user_id) if user_id else None,
                "created_at": datetime.datetime.now().isoformat()
            })
            return
    
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    
    def load_db():
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                return json.load(f)
        return {"users": {}, "cards": [], "proxies": {}, "sites": {}, "plan_codes": {}}
    
    def save_db(data):
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
    
    db = load_db()
    db["cards"].append({
        "card": card, "status": status, "response": response,
        "gateway": gateway, "price": price,
        "user_id": str(user_id) if user_id else None,
        "created_at": datetime.datetime.now().isoformat()
    })
    save_db(db)

async def get_total_cards_count():
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            return await db.cards.count_documents({})
    
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            return len(data["cards"])
    return 0

async def get_charged_count():
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            return await db.cards.count_documents({"status": "CHARGED"})
    
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            return sum(1 for c in data["cards"] if c.get("status") == "CHARGED")
    return 0

async def get_approved_count():
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            return await db.cards.count_documents({"status": "APPROVED"})
    
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            return sum(1 for c in data["cards"] if c.get("status") == "APPROVED")
    return 0

async def get_user_hits(user_id, status_filter=None, limit=None):
    """Get hit cards for a specific user."""
    results = []
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            query = {"user_id": str(user_id)}
            if status_filter:
                query["status"] = status_filter.upper()
            else:
                query["status"] = {"$in": ["CHARGED", "APPROVED"]}
            cursor = db.cards.find(query).sort("created_at", -1)
            if limit:
                cursor = cursor.limit(limit)
            async for doc in cursor:
                results.append(doc)
            return results
    import json, os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
        for c in reversed(data.get("cards", [])):
            if c.get("user_id") == str(user_id):
                st = c.get("status", "").upper()
                if status_filter:
                    if st == status_filter.upper(): results.append(c)
                else:
                    if st in ["CHARGED", "APPROVED"]: results.append(c)
            if limit and len(results) >= limit: break
    return results


async def get_all_hits(status_filter=None, limit=None):
    """Get all hit cards across all users. Admin use only."""
    results = []
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            query = {}
            if status_filter:
                query["status"] = status_filter.upper()
            else:
                query["status"] = {"$in": ["CHARGED", "APPROVED"]}
            cursor = db.cards.find(query).sort("created_at", -1)
            if limit:
                cursor = cursor.limit(limit)
            async for doc in cursor:
                results.append(doc)
            return results
    import json, os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
        for c in reversed(data.get("cards", [])):
            st = c.get("status", "").upper()
            if status_filter:
                if st == status_filter.upper(): results.append(c)
            else:
                if st in ["CHARGED", "APPROVED"]: results.append(c)
            if limit and len(results) >= limit: break
    return results


# ============ PROXY FUNCTIONS ============

async def add_proxy_db(user_id, proxy_data):
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            await db.proxies.update_one(
                {"_id": str(user_id)},
                {"$push": {"proxies": proxy_data}},
                upsert=True
            )
            return
    
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    
    def load_db():
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                return json.load(f)
        return {"users": {}, "cards": [], "proxies": {}, "sites": {}, "plan_codes": {}}
    
    def save_db(data):
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
    
    db = load_db()
    if str(user_id) not in db["proxies"]:
        db["proxies"][str(user_id)] = []
    db["proxies"][str(user_id)].append(proxy_data)
    save_db(db)

async def get_all_user_proxies(user_id):
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            user_proxies = await db.proxies.find_one({"_id": str(user_id)})
            return user_proxies.get("proxies", []) if user_proxies else []
    
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            return data["proxies"].get(str(user_id), [])
    return []

async def get_proxy_count(user_id):
    proxies = await get_all_user_proxies(user_id)
    return len(proxies)

async def get_random_proxy(user_id):
    proxies = await get_all_user_proxies(user_id)
    return random.choice(proxies) if proxies else None

async def remove_proxy_by_index(user_id, index):
    proxies = await get_all_user_proxies(user_id)
    if 0 <= index < len(proxies):
        removed = proxies.pop(index)
        if USE_MONGODB and MONGODB_URI:
            db = await get_mongo_db()
            if db:
                await db.proxies.update_one(
                    {"_id": str(user_id)},
                    {"$set": {"proxies": proxies}}
                )
        else:
            import json
            import os
            DB_FILE = "razor_bot_data.json"
            with open(DB_FILE, "r") as f:
                data = json.load(f)
            data["proxies"][str(user_id)] = proxies
            with open(DB_FILE, "w") as f:
                json.dump(data, f, indent=2, default=str)
        return removed
    return None

async def remove_proxy_by_url(user_id, proxy_url):
    proxies = await get_all_user_proxies(user_id)
    for i, p in enumerate(proxies):
        if p.get("proxy_url") == proxy_url:
            proxies.pop(i)
            if USE_MONGODB and MONGODB_URI:
                db = await get_mongo_db()
                if db:
                    await db.proxies.update_one(
                        {"_id": str(user_id)},
                        {"$set": {"proxies": proxies}}
                    )
            else:
                import json
                import os
                DB_FILE = "razor_bot_data.json"
                with open(DB_FILE, "r") as f:
                    data = json.load(f)
                data["proxies"][str(user_id)] = proxies
                with open(DB_FILE, "w") as f:
                    json.dump(data, f, indent=2, default=str)
            return True
    return False

async def clear_all_proxies(user_id):
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            user = await db.proxies.find_one({"_id": str(user_id)})
            count = len(user.get("proxies", [])) if user else 0
            await db.proxies.update_one(
                {"_id": str(user_id)},
                {"$set": {"proxies": []}}
            )
            return count
    
    proxies = await get_all_user_proxies(user_id)
    count = len(proxies)
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            await db.proxies.update_one(
                {"_id": str(user_id)},
                {"$set": {"proxies": []}}
            )
    else:
        import json
        import os
        DB_FILE = "razor_bot_data.json"
        with open(DB_FILE, "r") as f:
            data = json.load(f)
        data["proxies"][str(user_id)] = []
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
    return count

# ============ GLOBAL SITE FUNCTIONS ============

async def add_global_site(site, gateway="Shopify", price="0"):
    """Add a site to the global pool (admin only)."""
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            await db.globalsites.update_one(
                {"_id": "global"},
                {"$set": {f"sites.{site}": {"gateway": gateway, "price": price}}},
                upsert=True
            )
            return True
    
    # JSON fallback
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    def load_db():
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                return json.load(f)
        return {"users": {}, "cards": [], "proxies": {}, "sites": {}, "plan_codes": {}, "global_sites": {}}
    def save_db(data):
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
    db = load_db()
    if "global_sites" not in db:
        db["global_sites"] = {}
    db["global_sites"][site] = {"gateway": gateway, "price": price}
    save_db(db)
    return True

async def get_global_sites():
    """Return list of global site domains."""
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            doc = await db.globalsites.find_one({"_id": "global"})
            if doc and "sites" in doc:
                return list(doc["sites"].keys())
            return []
    
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            return list(data.get("global_sites", {}).keys())
    return []

async def remove_global_site(site):
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            await db.globalsites.update_one(
                {"_id": "global"},
                {"$unset": {f"sites.{site}": ""}}
            )
            return True
    
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    def load_db():
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                return json.load(f)
        return {"users": {}, "cards": [], "proxies": {}, "sites": {}, "plan_codes": {}, "global_sites": {}}
    def save_db(data):
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
    db = load_db()
    if site in db.get("global_sites", {}):
        del db["global_sites"][site]
        save_db(db)
        return True
    return False

async def clear_global_sites():
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            await db.globalsites.update_one(
                {"_id": "global"},
                {"$set": {"sites": {}}}
            )
            return True
    
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    def load_db():
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                return json.load(f)
        return {"users": {}, "cards": [], "proxies": {}, "sites": {}, "plan_codes": {}, "global_sites": {}}
    def save_db(data):
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
    db = load_db()
    db["global_sites"] = {}
    save_db(db)
    return True

# ============ PER-USER SITE FUNCTIONS (redirect to global) ============

async def add_site_db(user_id, site, gateway="Unknown", price="0"):
    return await add_global_site(site, gateway, price)

async def get_user_sites(user_id):
    return await get_global_sites()

async def get_user_sites_with_info(user_id):
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            doc = await db.globalsites.find_one({"_id": "global"})
            if doc and "sites" in doc:
                result = []
                for site, info in doc["sites"].items():
                    result.append({
                        "site": site,
                        "gateway": info.get("gateway", "Unknown"),
                        "price": info.get("price", "0")
                    })
                return result
            return []
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            gs = data.get("global_sites", {})
            result = []
            for site, info in gs.items():
                if isinstance(info, dict):
                    result.append({
                        "site": site,
                        "gateway": info.get("gateway", "Unknown"),
                        "price": info.get("price", "0")
                    })
                else:
                    result.append({
                        "site": site,
                        "gateway": "Unknown",
                        "price": "0"
                    })
            return result
    return []

async def remove_site_db(user_id, site):
    return await remove_global_site(site)

async def update_site_info(user_id, site, gateway, price):
    return await add_global_site(site, gateway, price)

# ============ PLAN CODE FUNCTIONS ============

def _normalise_code_limit(value, default=1):
    """Return a safe code redemption limit between 1 and 1000."""
    try:
        limit = int(value)
    except (TypeError, ValueError):
        limit = default
    return max(1, min(limit, 1000))


def _get_code_used_count(code_data):
    """Read usage count while remaining compatible with legacy boolean-only records."""
    try:
        used_count = int(code_data.get("used_count", 0) or 0)
    except (TypeError, ValueError):
        used_count = 0
    if code_data.get("used", False):
        used_count = max(used_count, 1)
    return max(0, used_count)


async def generate_plan_code(plan_key, count=1, max_uses=1):
    max_uses = _normalise_code_limit(max_uses)

    codes = []
    plan_prefixes = {
        "trial": "SHOPIFY_TRIAL",
        "1day": "SHOPIFY_1DAY",
        "plan1": "SHOPIFY_CORE",
        "plan2": "SHOPIFY_ELITE",
        "plan3": "SHOPIFY_ROOT",
        "plan4": "SHOPIFY_X"
    }
    prefix = plan_prefixes.get(plan_key, plan_key.upper())
    
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            for _ in range(count):
                random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
                code = f"{prefix}_{random_suffix}"
                existing = await db.codes.find_one({"_id": code})
                while existing:
                    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
                    code = f"{prefix}_{random_suffix}"
                    existing = await db.codes.find_one({"_id": code})
                
                await db.codes.insert_one({
                    "_id": code,
                    "plan": plan_key,
                    "created_at": datetime.datetime.now().isoformat(),
                    "max_uses": max_uses,
                    "used_count": 0,
                    "used": False,
                    "used_by": None,
                    "used_users": [],
                    "used_at": None
                })
                codes.append(code)
            return codes
    
    # JSON fallback
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    
    def load_db():
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                return json.load(f)
        return {"users": {}, "cards": [], "proxies": {}, "sites": {}, "plan_codes": {}}
    
    def save_db(data):
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
    
    db = load_db()
    if "plan_codes" not in db:
        db["plan_codes"] = {}
    
    for _ in range(count):
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        code = f"{prefix}_{random_suffix}"
        while code in db["plan_codes"]:
            random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            code = f"{prefix}_{random_suffix}"
        
        db["plan_codes"][code] = {
            "plan": plan_key,
            "created_at": datetime.datetime.now().isoformat(),
            "max_uses": max_uses,
            "used_count": 0,
            "used": False,
            "used_by": None,
            "used_users": [],
            "used_at": None
        }
        codes.append(code)
    save_db(db)
    return codes

async def redeem_plan_code(user_id, code):
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            code_data = await db.codes.find_one({"_id": code})
            if not code_data:
                return False, "invalid"
            max_uses = _normalise_code_limit(code_data.get("max_uses", 1))
            used_count = _get_code_used_count(code_data)
            if used_count >= max_uses:
                return False, "used"
            used_users = code_data.get("used_users", [])
            if not isinstance(used_users, list):
                used_users = []
            if any(str(existing_user) == str(user_id) for existing_user in used_users):
                return False, "already_used"
            
            plan_key = code_data.get("plan")
            from bot import PLANS
            if plan_key not in PLANS:
                return False, "invalid"
            
            plan_info = PLANS[plan_key]
            user_plan = await get_user_plan(user_id)
            if user_plan != "Bronze":
                return False, "has_plan"
            
            expiry = (datetime.datetime.now() + datetime.timedelta(days=plan_info["duration_days"])).isoformat()
            
            await db.users.update_one(
                {"_id": str(user_id)},
                {"$set": {"plan": plan_info["tier"], "expiry": expiry}}
            )
            
            next_used_count = used_count + 1
            next_used_users = used_users + [user_id]
            await db.codes.update_one(
                {"_id": code},
                {"$set": {
                    "used": next_used_count >= max_uses,
                    "used_count": next_used_count,
                    "used_by": user_id,
                    "used_users": next_used_users,
                    "used_at": datetime.datetime.now().isoformat()
                }}
            )
            
            return True, "success"
    
    # JSON fallback
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    
    def load_db():
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                return json.load(f)
        return {"users": {}, "cards": [], "proxies": {}, "sites": {}, "plan_codes": {}}
    
    def save_db(data):
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
    
    db = load_db()
    if code not in db.get("plan_codes", {}):
        return False, "invalid"
    code_data = db["plan_codes"][code]
    max_uses = _normalise_code_limit(code_data.get("max_uses", 1))
    used_count = _get_code_used_count(code_data)
    if used_count >= max_uses:
        return False, "used"
    used_users = code_data.get("used_users", [])
    if not isinstance(used_users, list):
        used_users = []
    if any(str(existing_user) == str(user_id) for existing_user in used_users):
        return False, "already_used"
    
    plan_key = code_data.get("plan")
    from bot import PLANS
    if plan_key not in PLANS:
        return False, "invalid"
    plan_info = PLANS[plan_key]
    user_plan = await get_user_plan(user_id)
    if user_plan != "Bronze":
        return False, "has_plan"
    
    expiry = (datetime.datetime.now() + datetime.timedelta(days=plan_info["duration_days"])).isoformat()
    user = db["users"].get(str(user_id), {})
    used_codes = user.get("used_codes", [])
    db["users"][str(user_id)] = {"plan": plan_info["tier"], "expiry": expiry, "banned": user.get("banned", False), "used_codes": used_codes}
    next_used_count = used_count + 1
    next_used_users = used_users + [user_id]
    db["plan_codes"][code]["max_uses"] = max_uses
    db["plan_codes"][code]["used_count"] = next_used_count
    db["plan_codes"][code]["used"] = next_used_count >= max_uses
    db["plan_codes"][code]["used_by"] = user_id
    db["plan_codes"][code]["used_users"] = next_used_users
    db["plan_codes"][code]["used_at"] = datetime.datetime.now().isoformat()
    if "used_codes" not in db["users"][str(user_id)]:
        db["users"][str(user_id)]["used_codes"] = []
    db["users"][str(user_id)]["used_codes"].append(code)
    save_db(db)
    return True, "success"

def is_valid_code(code):
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            code_data = data.get("plan_codes", {}).get(code)
            if code_data:
                return not code_data.get("used", False)
    return False

def get_code_info(code):
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            return data.get("plan_codes", {}).get(code)
    return None

async def remove_code(code):
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            await db.codes.delete_one({"_id": code})
            return True
    
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    
    def load_db():
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                return json.load(f)
        return {"users": {}, "cards": [], "proxies": {}, "sites": {}, "plan_codes": {}}
    
    def save_db(data):
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
    
    db = load_db()
    if code in db.get("plan_codes", {}):
        del db["plan_codes"][code]
        save_db(db)
        return True
    return False

async def get_all_active_codes():
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            codes = {}
            cursor = db.codes.find({"used": False})
            async for doc in cursor:
                codes[doc["_id"]] = doc
            return codes
    
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            codes = {}
            for code, info in data.get("plan_codes", {}).items():
                if not info.get("used", False):
                    codes[code] = info
            return codes
    return {}

async def get_all_codes():
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            codes = {}
            cursor = db.codes.find({})
            async for doc in cursor:
                codes[doc["_id"]] = doc
            return codes
    
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            return data.get("plan_codes", {})
    return {}

# ============ STATISTICS FUNCTIONS ============

async def get_total_users():
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            return await db.users.count_documents({})
    
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            users = data.get("users", {})
            return sum(1 for uid in users if _coerce_user_id(uid) is not None)
    return 0

async def get_premium_count():
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            return await db.users.count_documents({"plan": {"$in": ["Trial", "1Day", "Core", "Elite", "Root", "X"]}})
    
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            return sum(1 for u in data["users"].values() if u.get("plan") in ["Trial", "1Day", "Core", "Elite", "Root", "X"])
    return 0

async def get_all_premium_users():
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            result = []
            cursor = db.users.find({"plan": {"$in": ["Trial", "1Day", "Core", "Elite", "Root", "X"]}})
            async for doc in cursor:
                result.append({"user_id": int(doc["_id"]), "plan": doc.get("plan")})
            return result
    
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            result = []
            for uid, udata in data["users"].items():
                if udata.get("plan") in ["Trial", "1Day", "Core", "Elite", "Root", "X"]:
                    result.append({"user_id": int(uid), "plan": udata.get("plan")})
            return result
    return []

async def get_total_sites_count():
    sites = await get_global_sites()
    return len(sites)

async def get_users_with_sites():
    sites = await get_global_sites()
    return 1 if sites else 0

async def get_sites_per_user():
    sites = await get_global_sites()
    return [{"user_id": "global", "cnt": len(sites)}]

async def get_all_sites_detail():
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            doc = await db.globalsites.find_one({"_id": "global"})
            if doc and "sites" in doc:
                result = []
                for site, info in doc["sites"].items():
                    result.append({
                        "user_id": "global",
                        "site": site,
                        "gateway": info.get("gateway", "Unknown"),
                        "price": info.get("price", "0")
                    })
                return result
            return []
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            gs = data.get("global_sites", {})
            result = []
            for site, info in gs.items():
                result.append({
                    "user_id": "global",
                    "site": site,
                    "gateway": info.get("gateway", "Unknown"),
                    "price": info.get("price", "0")
                })
            return result
    return []

# ============ INIT DATABASE ============

async def init_db():
    if USE_MONGODB and MONGODB_URI:
        try:
            db = await get_mongo_db()
            if db:
                # Create indexes
                await db.users.create_index("_id")
                await db.cards.create_index("created_at")
                await db.codes.create_index("used")
                await db.globalsites.create_index("_id")
                print("✅ MongoDB connected!")
                return True
        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")
            print("⚠️ Falling back to JSON storage...")
    
    print("✅ Using JSON file storage")
    return True

# ============ JOIN CACHE ============

_joined_cache = set()

async def mark_user_joined(user_id):
    _joined_cache.add(user_id)

async def is_user_marked_joined(user_id):
    return user_id in _joined_cache

async def remove_joined_mark(user_id):
    _joined_cache.discard(user_id)

async def get_all_user_ids():
    """Return list of all user IDs (used by /broadcast in JSON mode)."""
    if USE_MONGODB and MONGODB_URI:
        db_conn = await get_mongo_db()
        if db_conn:
            result = []
            async for doc in db_conn.users.find({}, {"_id": 1}):
                user_id = _coerce_user_id(doc.get("_id"))
                if user_id is not None:
                    result.append(user_id)
            return result
    # JSON fallback
    import json as _json
    import os as _os
    DB_FILE = "razor_bot_data.json"
    if _os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = _json.load(f)
            result = []
            for raw_user_id in data.get("users", {}).keys():
                user_id = _coerce_user_id(raw_user_id)
                if user_id is not None:
                    result.append(user_id)
            return result
    return []

# Database wrapper
class DatabaseWrapper:
    def __init__(self):
        self.users = {}

    async def find_one(self, collection, query):
        return None

    def __getitem__(self, key):
        return self

db = DatabaseWrapper()

print(f"📦 MongoDB Mode: {USE_MONGODB and MONGODB_URI}")
