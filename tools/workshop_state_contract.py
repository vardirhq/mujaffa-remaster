DEFAULTS = {
    "free_purchases": True,
    "money": 5000,
    "street_cred": 0,
    "bmw_count": 1,
}
CATEGORY_STATE = (
    "paint", "audio", "spoiler", "exhaust", "rims", "tyres", "windows",
    "sunroof", "plate", "interior", "trinket", "horn", "camera",
)

def charged_price(real_price, free_purchases):
    return 0 if free_purchases else real_price

def can_purchase(money, real_price, free_purchases):
    return free_purchases or money >= real_price

def apply_purchase(money, cred, real_price, cred_reward, free_purchases):
    if not can_purchase(money, real_price, free_purchases):
        return money, cred, False
    return money - charged_price(real_price, free_purchases), cred + cred_reward, True
