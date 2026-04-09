import random
from datetime import datetime

from passlib.context import CryptContext
from sqlalchemy import create_engine, text

# =========================
# НАСТРОЙКИ
# =========================
DATABASE_URL = "postgresql+psycopg2://postgres:A123a123s@localhost:5432/smartcanteen"

USERS_TO_CREATE = 200
CLEAR_EXISTING_USERS = True
PASSWORD_PLAIN = "1234"

DIET_OPTIONS = [
    "vegetarian",
    "vegan",
    "glutenFree",
    "lactoseFree",
    "lowCalorie",
    "highProtein",
    "diabetic",
    "halal",
]

ALLERGY_OPTIONS = [
    "milk",
    "eggs",
    "nuts",
    "peanuts",
    "fish",
    "seafood",
    "soy",
    "gluten",
    "sesame",
]

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def choose_diets() -> list[str]:
    """
    Более реалистичное распределение:
    - чаще 0 или 1 диета
    - реже 2
    - очень редко 3
    """
    count = random.choices(
        population=[0, 1, 2, 3],
        weights=[0.45, 0.35, 0.15, 0.05],
        k=1,
    )[0]

    if count == 0:
        return []

    diets = set()

    # Иногда специально делаем "связанные" комбинации
    patterns = [
        ["vegetarian"],
        ["vegan"],
        ["glutenFree"],
        ["lactoseFree"],
        ["lowCalorie"],
        ["highProtein"],
        ["diabetic"],
        ["halal"],
        ["vegetarian", "lowCalorie"],
        ["vegan", "lactoseFree"],
        ["glutenFree", "diabetic"],
        ["highProtein", "halal"],
    ]

    if random.random() < 0.55:
        base = random.choice(patterns)
        diets.update(base)

    while len(diets) < count:
        diets.add(random.choice(DIET_OPTIONS))

    return sorted(diets)


def choose_allergies() -> list[str]:
    """
    Более реалистичное распределение:
    - чаще 0 или 1 аллергия
    - реже 2
    - очень редко 3-4
    """
    count = random.choices(
        population=[0, 1, 2, 3, 4],
        weights=[0.40, 0.32, 0.18, 0.07, 0.03],
        k=1,
    )[0]

    if count == 0:
        return []

    allergies = set()

    # Иногда используем типичные наборы
    patterns = [
        ["milk"],
        ["eggs"],
        ["gluten"],
        ["nuts"],
        ["peanuts"],
        ["fish"],
        ["soy"],
        ["milk", "eggs"],
        ["milk", "gluten"],
        ["nuts", "peanuts"],
        ["fish", "seafood"],
    ]

    if random.random() < 0.55:
        base = random.choice(patterns)
        allergies.update(base)

    while len(allergies) < count:
        allergies.add(random.choice(ALLERGY_OPTIONS))

    return sorted(allergies)


def main():
    random.seed()

    engine = create_engine(DATABASE_URL)
    password_hash = pwd_context.hash(PASSWORD_PLAIN)

    with engine.raw_connection() as conn:
        with conn.cursor() as cur:
            if CLEAR_EXISTING_USERS:
                cur.execute("DELETE FROM users WHERE role = 'user';")
                print("Обычные пользователи удалены.")

            cur.execute("SELECT COALESCE(MAX(id), 0) FROM users;")
            max_id = cur.fetchone()[0] or 0

            created = 0
            for i in range(1, USERS_TO_CREATE + 1):
                suffix = max_id + i
                username = f"user_{suffix}"
                email = f"user_{suffix}@mail.com"
                diets = choose_diets()
                allergies = choose_allergies()

                cur.execute(
                    """
                    INSERT INTO users (
                        username,
                        email,
                        password_hash,
                        role,
                        diet_types,
                        allergens,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        username,
                        email,
                        password_hash,
                        "user",
                        diets,
                        allergies,
                        datetime.utcnow(),
                    ),
                )
                created += 1

            conn.commit()

    print(f"Готово. Создано пользователей: {created}")
    print(f"Пароль у всех пользователей: {PASSWORD_PLAIN}")


if __name__ == "__main__":
    main()