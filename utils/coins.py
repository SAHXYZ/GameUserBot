# filename: utils/coins.py

"""
Coin conversion utilities used across GameBot.

Denominations:
- 1 Bronze    = 1 bronze unit
- 1 Silver    = 100 Bronze
- 1 Gold      = 10,000 Bronze
- 1 Platinum  = 1,000,000 Bronze
- Black Gold  = special (excluded from conversion)
"""

# ---------------------------
# CONSTANTS
# ---------------------------

BRONZE_PER_SILVER = 100
BRONZE_PER_GOLD = BRONZE_PER_SILVER * 100        # 10,000
BRONZE_PER_PLATINUM = BRONZE_PER_GOLD * 100      # 1,000,000


# ---------------------------
# STRUCTURED BREAKDOWN
# ---------------------------

def breakdown_from_bronze(total_bronze: int) -> dict:
    """
    Convert bronze units → structured currency breakdown.
    Returns:
    {
        "platinum": x,
        "gold": x,
        "silver": x,
        "bronze": x
    }
    """
    total_bronze = max(int(total_bronze), 0)

    platinum = total_bronze // BRONZE_PER_PLATINUM
    rem = total_bronze % BRONZE_PER_PLATINUM

    gold = rem // BRONZE_PER_GOLD
    rem %= BRONZE_PER_GOLD

    silver = rem // BRONZE_PER_SILVER
    bronze = rem % BRONZE_PER_SILVER

    return {
        "platinum": platinum,
        "gold": gold,
        "silver": silver,
        "bronze": bronze,
    }


# ---------------------------
# TOTAL VALUE IN BRONZE
# ---------------------------

def total_bronze_value(user: dict) -> int:
    """
    Convert a user's entire wallet into bronze units.
    Used for:
    - leaderboard ranking
    - comparing wealth
    - economy logic
    
    Black gold is intentionally excluded (event/premium currency).
    """
    plat = int(user.get("platinum", 0) or 0)
    gold = int(user.get("gold", 0) or 0)
    silver = int(user.get("silver", 0) or 0)
    bronze = int(user.get("bronze", 0) or 0)

    return (
        plat * BRONZE_PER_PLATINUM +
        gold * BRONZE_PER_GOLD +
        silver * BRONZE_PER_SILVER +
        bronze
    )
