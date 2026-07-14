# MongoDB Database - Full Safe Storage
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

async def ensure_user(user_id):
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
    return plan in ["Trial", "Core", "Elite", "Root", "X"]

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

# ============ CARD FUNCTIONS ============

async def save_card_to_db(card, status, response, gateway, price):
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            await db.cards.insert_one({
                "card": card,
                "status": status,
                "response": response,
                "gateway": gateway,
                "price": price,
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
        "gateway": gateway, "price": price, "created_at": datetime.datetime.now().isoformat()
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

# ============ SITE FUNCTIONS ============

async def add_site_db(user_id, site, gateway="Unknown", price="0"):
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            await db.sites.update_one(
                {"_id": str(user_id)},
                {"$set": {f"sites.{site}": {"gateway": gateway, "price": price}}},
                upsert=True
            )
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
    if str(user_id) not in db["sites"]:
        db["sites"][str(user_id)] = {}
    db["sites"][str(user_id)][site] = {"gateway": gateway, "price": price}
    save_db(db)
    return True

async def get_user_sites(user_id):
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            user_sites = await db.sites.find_one({"_id": str(user_id)})
            if user_sites and "sites" in user_sites:
                return list(user_sites["sites"].keys())
            return []
    
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            sites_dict = data["sites"].get(str(user_id), {})
            return list(sites_dict.keys())
    return []

async def get_user_sites_with_info(user_id):
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            user_sites = await db.sites.find_one({"_id": str(user_id)})
            if user_sites and "sites" in user_sites:
                result = []
                for site, info in user_sites["sites"].items():
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
    
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            sites_data = data["sites"].get(str(user_id), {})
            result = []
            if isinstance(sites_data, dict):
                for site, info in sites_data.items():
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
            elif isinstance(sites_data, list):
                for site in sites_data:
                    result.append({
                        "site": site,
                        "gateway": "Unknown",
                        "price": "0"
                    })
            return result
    return []

async def remove_site_db(user_id, site):
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            await db.sites.update_one(
                {"_id": str(user_id)},
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
        return {"users": {}, "cards": [], "proxies": {}, "sites": {}, "plan_codes": {}}
    
    def save_db(data):
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
    
    db = load_db()
    sites_dict = db["sites"].get(str(user_id), {})
    if site in sites_dict:
        del sites_dict[site]
        save_db(db)
        return True
    return False

async def update_site_info(user_id, site, gateway, price):
    return await add_site_db(user_id, site, gateway, price)

# ============ PLAN CODE FUNCTIONS ============

async def generate_plan_code(plan_key, count=1):
    codes = []
    plan_prefixes = {
        "plan0": "SHOPIFY_TRIAL",
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
                    "used": False,
                    "used_by": None,
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
            "used": False,
            "used_by": None,
            "used_at": None
        }
        codes.append(code)
    save_db(db)
    return codes

async def redeem_plan_code(user_id, code):
    """
    Returns (success, status, plan_key)
    status: 'success', 'invalid', 'used', 'has_plan'
    """
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            code_data = await db.codes.find_one({"_id": code})
            if not code_data:
                return False, "invalid", None
            if code_data.get("used", False):
                return False, "used", None
            
            plan_key = code_data.get("plan")
            # Import PLANS dynamically to avoid circular import
            from bot import PLANS
            if plan_key not in PLANS:
                return False, "invalid", None
            
            user_plan = await get_user_plan(user_id)
            if user_plan != "Bronze":
                return False, "has_plan", None
            
            plan_info = PLANS[plan_key]
            expiry = (datetime.datetime.now() + datetime.timedelta(days=plan_info["duration_days"])).isoformat()
            
            await db.users.update_one(
                {"_id": str(user_id)},
                {"$set": {"plan": plan_info["tier"], "expiry": expiry}}
            )
            
            await db.codes.update_one(
                {"_id": code},
                {"$set": {"used": True, "used_by": user_id, "used_at": datetime.datetime.now().isoformat()}}
            )
            
            return True, "success", plan_key
    
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
        return False, "invalid", None
    code_data = db["plan_codes"][code]
    if code_data.get("used", False):
        return False, "used", None
    
    plan_key = code_data.get("plan")
    from bot import PLANS
    if plan_key not in PLANS:
        return False, "invalid", None
    plan_info = PLANS[plan_key]
    user_plan = await get_user_plan(user_id)
    if user_plan != "Bronze":
        return False, "has_plan", None
    
    expiry = (datetime.datetime.now() + datetime.timedelta(days=plan_info["duration_days"])).isoformat()
    user = db["users"].get(str(user_id), {})
    used_codes = user.get("used_codes", [])
    db["users"][str(user_id)] = {"plan": plan_info["tier"], "expiry": expiry, "banned": user.get("banned", False), "used_codes": used_codes}
    db["plan_codes"][code]["used"] = True
    db["plan_codes"][code]["used_by"] = user_id
    db["plan_codes"][code]["used_at"] = datetime.datetime.now().isoformat()
    if "used_codes" not in db["users"][str(user_id)]:
        db["users"][str(user_id)]["used_codes"] = []
    db["users"][str(user_id)]["used_codes"].append(code)
    save_db(db)
    return True, "success", plan_key

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
            return len(data["users"])
    return 0

async def get_premium_count():
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            return await db.users.count_documents({"plan": {"$in": ["Trial", "Core", "Elite", "Root", "X"]}})
    
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            return sum(1 for u in data["users"].values() if u.get("plan") in ["Trial", "Core", "Elite", "Root", "X"])
    return 0

async def get_all_premium_users():
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            result = []
            cursor = db.users.find({"plan": {"$in": ["Trial", "Core", "Elite", "Root", "X"]}})
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
                if udata.get("plan") in ["Trial", "Core", "Elite", "Root", "X"]:
                    result.append({"user_id": int(uid), "plan": udata.get("plan")})
            return result
    return []

async def get_total_sites_count():
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            total = 0
            cursor = db.sites.find({})
            async for doc in cursor:
                total += len(doc.get("sites", {}))
            return total
    
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            total = 0
            for sites_dict in data["sites"].values():
                total += len(sites_dict)
            return total
    return 0

async def get_users_with_sites():
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            return await db.sites.count_documents({})
    
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            return len(data["sites"])
    return 0

async def get_sites_per_user():
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            result = []
            cursor = db.sites.find({})
            async for doc in cursor:
                result.append({"user_id": int(doc["_id"]), "cnt": len(doc.get("sites", {}))})
            return result
    
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            return [{"user_id": int(uid), "cnt": len(sites)} for uid, sites in data["sites"].items()]
    return []

async def get_all_sites_detail():
    if USE_MONGODB and MONGODB_URI:
        db = await get_mongo_db()
        if db:
            result = []
            cursor = db.sites.find({})
            async for doc in cursor:
                uid = int(doc["_id"])
                for site, info in doc.get("sites", {}).items():
                    result.append({
                        "user_id": uid,
                        "site": site,
                        "gateway": info.get("gateway", "Unknown"),
                        "price": info.get("price", "0")
                    })
            return result
    
    import json
    import os
    DB_FILE = "razor_bot_data.json"
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            result = []
            for uid, sites_dict in data["sites"].items():
                for site, info in sites_dict.items():
                    result.append({
                        "user_id": int(uid),
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

# ============ GLOBAL SITES ============

async def add_global_site(site):
    return True

async def get_global_sites():
    return []

async def remove_global_site(site):
    return True

# Database wrapper
class DatabaseWrapper:
    def __init__(self):
        self.users = {}
    
    async def find_one(self, collection, query):
        return None
    
    async def __getitem__(self, key):
        return self

db = DatabaseWrapper()

print(f"📦 MongoDB Mode: {USE_MONGODB and MONGODB_URI}")
