import math
import random
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

# =========================
# НАСТРОЙКИ
# =========================
DATABASE_URL = "postgresql+psycopg2://postgres:A123a123s@localhost:5432/smartcanteen"

CLEAR_OLD_ORDERS = True
SESSIONS_PER_USER_MIN = 18
SESSIONS_PER_USER_MAX = 40
OUTPUT_CSV = "generated_orders_history.csv"
RANDOM_SEED = 42

random.seed(RANDOM_SEED)

STRICT_DIETS = {"vegetarian", "vegan", "glutenFree", "lactoseFree", "halal"}

BREAKFAST_HOURS = [7, 8, 9, 10]
LUNCH_HOURS = [11, 12, 13, 14, 15]
DINNER_HOURS = [17, 18, 19, 20]

WEEKDAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


def get_time_of_day(hour: int) -> str:
    if hour in BREAKFAST_HOURS:
        return "breakfast"
    if hour in LUNCH_HOURS:
        return "lunch"
    return "dinner"


def normalize_pg_array(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return []


def infer_allergen_tags(ingredients, allergen_warning: str):
    text_blob = " ".join(ingredients).lower() + " " + (allergen_warning or "").lower()

    rules = {
        "milk": ["молок", "сыр", "слив", "сметан", "твор", "йогурт", "фета", "капучино", "латте", "морожен"],
        "eggs": ["яйц", "омлет"],
        "nuts": ["орех", "миндаль", "фундук", "грецк"],
        "peanuts": ["арахис"],
        "fish": ["рыб", "тунец", "уха", "лосось", "треск"],
        "seafood": ["морепродукт", "кревет", "мид", "кальмар"],
        "soy": ["соя", "соев", "терияки"],
        "gluten": ["мука", "лапша", "макарон", "хлеб", "булка", "сухар", "блин", "овсян", "перлов", "булгур", "лазань"],
        "sesame": ["кунжут"],
    }

    found = []
    for tag, keywords in rules.items():
        if any(word in text_blob for word in keywords):
            found.append(tag)

    return sorted(set(found))


def infer_diet_tags(category: str, ingredients, allergen_warning: str, calories: int):
    text_blob = " ".join(ingredients).lower() + " " + (allergen_warning or "").lower()

    has_meat = any(
        word in text_blob
        for word in ["говяд", "свин", "куриц", "индейк", "бекон", "ветчин", "мяс", "котлет", "тефтел", "сосиск", "колбас"]
    )
    has_fish = any(word in text_blob for word in ["рыб", "тунец", "уха", "лосось", "треск"])
    has_seafood = any(word in text_blob for word in ["кревет", "мид", "кальмар", "морепродукт"])
    has_milk = any(word in text_blob for word in ["молок", "сыр", "слив", "сметан", "твор", "йогурт", "фета", "капучино", "латте", "морожен"])
    has_eggs = ("яйц" in text_blob) or ("омлет" in text_blob)
    has_gluten = any(word in text_blob for word in ["мука", "лапша", "макарон", "хлеб", "булка", "сухар", "блин", "овсян", "перлов", "булгур", "лазань"])
    has_pork = any(word in text_blob for word in ["свин", "бекон", "ветчин"])

    tags = []

    if not has_meat and not has_fish and not has_seafood:
        tags.append("vegetarian")

    if not has_meat and not has_fish and not has_seafood and not has_milk and not has_eggs:
        tags.append("vegan")

    if not has_gluten:
        tags.append("glutenFree")

    if not has_milk:
        tags.append("lactoseFree")

    if calories <= 260:
        tags.append("lowCalorie")

    if category in {"main", "breakfast"} and calories >= 280 and category != "dessert":
        tags.append("highProtein")

    if calories <= 280 and category != "dessert":
        tags.append("diabetic")

    if not has_pork:
        tags.append("halal")

    return sorted(set(tags))


def category_bonus(category: str, time_of_day: str) -> float:
    table = {
        "breakfast": {"breakfast": 2.2, "lunch": 0.5, "dinner": 0.2},
        "soup": {"breakfast": 0.2, "lunch": 2.1, "dinner": 0.8},
        "main": {"breakfast": 0.5, "lunch": 1.9, "dinner": 1.5},
        "salad": {"breakfast": 0.4, "lunch": 1.1, "dinner": 1.3},
        "dessert": {"breakfast": 0.7, "lunch": 0.9, "dinner": 0.8},
        "drink": {"breakfast": 1.1, "lunch": 0.9, "dinner": 0.9},
        "snack": {"breakfast": 0.9, "lunch": 0.8, "dinner": 0.7},
    }
    return table.get(category, {}).get(time_of_day, 0.5)


def weekday_bonus(category: str, weekday: str) -> float:
    if weekday in {"saturday", "sunday"}:
        if category in {"dessert", "snack", "drink"}:
            return 1.15
        if category == "soup":
            return 0.9
    else:
        if category in {"soup", "main"}:
            return 1.08
    return 1.0


def has_allergy_conflict(user_allergies, dish_allergens) -> bool:
    return any(a in dish_allergens for a in user_allergies)


def has_diet_conflict(user_diets, dish_diets) -> bool:
    for diet in user_diets:
        if diet in STRICT_DIETS and diet not in dish_diets:
            return True
    return False


def price_affinity(price: float, preferred_budget: float) -> float:
    diff = abs(price - preferred_budget)
    if diff <= 20:
        return 1.4
    if diff <= 50:
        return 1.15
    if diff <= 90:
        return 0.95
    return 0.7


def calorie_affinity(calories: int, preferred_calories: int) -> float:
    diff = abs(calories - preferred_calories)
    if diff <= 50:
        return 1.35
    if diff <= 100:
        return 1.1
    if diff <= 180:
        return 0.9
    return 0.65


def choose_quantity(category: str) -> int:
    if category in {"drink", "dessert"}:
        return 1
    return 2 if random.random() < 0.15 else 1


def choose_user_profile(user_row):
    diets = normalize_pg_array(user_row["diet_types"])
    allergies = normalize_pg_array(user_row["allergens"])

    favorite_categories = random.sample(
        ["breakfast", "soup", "main", "salad", "dessert", "drink", "snack"],
        k=2,
    )

    preferred_budget = round(random.uniform(100, 230), 2)
    preferred_calories = random.randint(160, 470)
    sweet_tooth = 1 if random.random() < 0.35 else 0

    return {
        "favorite_categories": favorite_categories,
        "preferred_budget": preferred_budget,
        "preferred_calories": preferred_calories,
        "sweet_tooth": sweet_tooth,
        "diet_types": diets,
        "allergens": allergies,
    }


def load_users_and_dishes(engine):
    users_sql = text("""
        SELECT id, username, diet_types, allergens
        FROM users
        WHERE role = 'user'
        ORDER BY id
    """)

    dishes_sql = text("""
        SELECT id, name, category, calories, price, ingredients, description, allergen_warning, is_available
        FROM dishes
        WHERE is_available = true
        ORDER BY id
    """)

    with engine.connect() as conn:
        users_df = pd.read_sql(users_sql, conn)
        dishes_df = pd.read_sql(dishes_sql, conn)

    if users_df.empty:
        raise ValueError("В таблице users нет обычных пользователей.")
    if dishes_df.empty:
        raise ValueError("В таблице dishes нет доступных блюд.")

    dishes_df["ingredients"] = dishes_df["ingredients"].apply(normalize_pg_array)
    dishes_df["dish_allergens"] = dishes_df.apply(
        lambda row: infer_allergen_tags(row["ingredients"], row["allergen_warning"] or ""),
        axis=1,
    )
    dishes_df["dish_diets"] = dishes_df.apply(
        lambda row: infer_diet_tags(
            row["category"],
            row["ingredients"],
            row["allergen_warning"] or "",
            int(row["calories"]),
        ),
        axis=1,
    )

    return users_df, dishes_df


def clear_old_orders(conn):
    conn.execute(text("DELETE FROM order_items;"))
    conn.execute(text("DELETE FROM orders;"))


def score_dish(profile, dish, time_bucket: str, weekday: str, category_history, dish_history):
    dish_allergens = dish["dish_allergens"]
    dish_diets = dish["dish_diets"]
    category = dish["category"]
    price = float(dish["price"])
    calories = int(dish["calories"])

    if has_allergy_conflict(profile["allergens"], dish_allergens):
        return None

    if has_diet_conflict(profile["diet_types"], dish_diets):
        return None

    score = 0.0
    score += category_bonus(category, time_bucket)
    score *= weekday_bonus(category, weekday)

    if category in profile["favorite_categories"]:
        score += 1.2
    else:
        score += 0.25

    score *= price_affinity(price, profile["preferred_budget"])
    score *= calorie_affinity(calories, profile["preferred_calories"])

    if "lowCalorie" in profile["diet_types"] and calories > 380:
        score *= 0.65

    if "highProtein" in profile["diet_types"] and category in {"main", "breakfast"}:
        score *= 1.15

    if "diabetic" in profile["diet_types"] and category == "dessert":
        score *= 0.45

    if profile["sweet_tooth"] and category == "dessert":
        score *= 1.25

    score *= (1.0 + min(category_history[category], 5) * 0.08)
    score *= (1.0 + min(dish_history[int(dish["id"])], 4) * 0.10)

    score += random.uniform(-0.2, 0.2)
    return max(score, 0.01)


def determine_order_pattern(time_bucket: str):
    if time_bucket == "breakfast":
        patterns = [
            ["breakfast"],
            ["breakfast", "drink"],
            ["breakfast", "dessert"],
            ["breakfast", "drink", "dessert"],
            ["drink", "snack"],
        ]
        weights = [0.34, 0.30, 0.08, 0.08, 0.20]
        return random.choices(patterns, weights=weights, k=1)[0]

    if time_bucket == "lunch":
        patterns = [
            ["soup", "main"],
            ["soup", "main", "drink"],
            ["main", "salad"],
            ["main", "salad", "drink"],
            ["soup", "salad", "main"],
            ["main"],
            ["main", "drink"],
            ["soup", "main", "dessert", "drink"],
        ]
        weights = [0.24, 0.22, 0.10, 0.14, 0.10, 0.08, 0.07, 0.05]
        return random.choices(patterns, weights=weights, k=1)[0]

    patterns = [
        ["main"],
        ["main", "salad"],
        ["main", "drink"],
        ["salad", "drink"],
        ["main", "salad", "drink"],
        ["soup", "main"],
    ]
    weights = [0.24, 0.22, 0.18, 0.10, 0.16, 0.10]
    return random.choices(patterns, weights=weights, k=1)[0]


def choose_dish_for_category(candidates, target_category):
    filtered = [(dish, score) for dish, score in candidates if dish["category"] == target_category]
    if not filtered:
        return None

    dishes = [item[0] for item in filtered]
    weights = [item[1] for item in filtered]
    return random.choices(dishes, weights=weights, k=1)[0]


def generate_orders(engine, users_df, dishes_df):
    history_rows = []
    start_date = datetime.now() - timedelta(days=120)

    with engine.begin() as conn:
        if CLEAR_OLD_ORDERS:
            clear_old_orders(conn)
            print("Старые заказы удалены.")

        for _, user in users_df.iterrows():
            user_id = int(user["id"])
            username = user["username"]
            profile = choose_user_profile(user)

            category_history = defaultdict(int)
            dish_history = defaultdict(int)

            session_count = random.randint(SESSIONS_PER_USER_MIN, SESSIONS_PER_USER_MAX)

            for session_index in range(session_count):
                weekday = random.choice(WEEKDAYS)

                time_bucket = random.choices(
                    population=["breakfast", "lunch", "dinner"],
                    weights=[0.22, 0.48, 0.30],
                    k=1,
                )[0]

                if time_bucket == "breakfast":
                    hour = random.choice(BREAKFAST_HOURS)
                elif time_bucket == "lunch":
                    hour = random.choice(LUNCH_HOURS)
                else:
                    hour = random.choice(DINNER_HOURS)

                order_dt = start_date + timedelta(
                    days=random.randint(0, 120),
                    hours=hour,
                    minutes=random.randint(0, 59),
                )

                scored_candidates = []
                for _, dish in dishes_df.iterrows():
                    score = score_dish(
                        profile,
                        dish,
                        time_bucket,
                        weekday,
                        category_history,
                        dish_history,
                    )
                    if score is not None:
                        scored_candidates.append((dish, score))

                if not scored_candidates:
                    continue

                pattern = determine_order_pattern(time_bucket)
                selected_dishes = []
                selected_ids = set()

                for category in pattern:
                    chosen = choose_dish_for_category(scored_candidates, category)
                    if chosen is None:
                        continue
                    if int(chosen["id"]) in selected_ids:
                        continue

                    selected_dishes.append(chosen)
                    selected_ids.add(int(chosen["id"]))

                if not selected_dishes:
                    chosen_any = random.choices(
                        [d for d, _ in scored_candidates],
                        weights=[s for _, s in scored_candidates],
                        k=1,
                    )[0]
                    selected_dishes = [chosen_any]
                    selected_ids.add(int(chosen_any["id"]))

                total_price = Decimal("0")
                order_items_data = []

                for dish in selected_dishes:
                    quantity = choose_quantity(dish["category"])
                    unit_price = Decimal(str(dish["price"]))
                    line_total = unit_price * quantity
                    total_price += line_total

                    order_items_data.append(
                        {
                            "dish": dish,
                            "quantity": quantity,
                            "unit_price": unit_price,
                        }
                    )

                order_result = conn.execute(
                    text("""
                        INSERT INTO orders (user_id, total_price, status, created_at)
                        VALUES (:user_id, :total_price, :status, :created_at)
                        RETURNING id
                    """),
                    {
                        "user_id": user_id,
                        "total_price": total_price,
                        "status": "created",
                        "created_at": order_dt,
                    }
                )
                order_id = order_result.scalar_one()

                for item in order_items_data:
                    dish = item["dish"]
                    quantity = item["quantity"]
                    unit_price = item["unit_price"]

                    conn.execute(
                        text("""
                            INSERT INTO order_items (order_id, dish_id, quantity, unit_price)
                            VALUES (:order_id, :dish_id, :quantity, :unit_price)
                        """),
                        {
                            "order_id": order_id,
                            "dish_id": int(dish["id"]),
                            "quantity": quantity,
                            "unit_price": unit_price,
                        }
                    )

                    category_history[dish["category"]] += 1
                    dish_history[int(dish["id"])] += 1

                    history_rows.append(
                        {
                            "order_id": order_id,
                            "user_id": user_id,
                            "username": username,
                            "dish_id": int(dish["id"]),
                            "dish_name": dish["name"],
                            "category": dish["category"],
                            "quantity": quantity,
                            "unit_price": float(unit_price),
                            "line_total": float(unit_price * quantity),
                            "order_total_price": float(total_price),
                            "calories": int(dish["calories"]),
                            "weekday": weekday,
                            "hour": hour,
                            "time_of_day": time_bucket,
                            "diet_types": ",".join(profile["diet_types"]),
                            "allergens": ",".join(profile["allergens"]),
                            "favorite_categories": ",".join(profile["favorite_categories"]),
                            "preferred_budget": profile["preferred_budget"],
                            "preferred_calories": profile["preferred_calories"],
                            "sweet_tooth": profile["sweet_tooth"],
                            "dish_allergens": ",".join(dish["dish_allergens"]),
                            "dish_diets": ",".join(dish["dish_diets"]),
                            "created_at": order_dt.isoformat(),
                        }
                    )

    history_df = pd.DataFrame(history_rows)
    history_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    return history_df


def main():
    engine = create_engine(DATABASE_URL)

    users_df, dishes_df = load_users_and_dishes(engine)
    history_df = generate_orders(engine, users_df, dishes_df)

    print(f"Пользователей прочитано: {len(users_df)}")
    print(f"Доступных блюд прочитано: {len(dishes_df)}")
    print(f"Строк в CSV (order items): {len(history_df)}")
    print(f"CSV сохранён в файл: {Path(OUTPUT_CSV).resolve()}")


if __name__ == "__main__":
    main()