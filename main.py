from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Generator, List, Optional
from uuid import uuid4
from zoneinfo import ZoneInfo

import pandas as pd
from catboost import CatBoostClassifier
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    create_engine,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

app = FastAPI(title="SmartCanteen API")

# ---------------------------------
# Пути
# ---------------------------------
BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

MODEL_PATH = BASE_DIR / "dish_ranker.cbm"
ranking_model: Optional[CatBoostClassifier] = None

MOSCOW_TZ = ZoneInfo("Europe/Moscow")
STRICT_DIETS = {"vegetarian", "vegan", "glutenFree", "lactoseFree", "halal"}

app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# ---------------------------------
# CORS для связи React и FastAPI
# ---------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------
# JWT настройки
# ---------------------------------
SECRET_KEY = "smartcanteen_super_secret_key_change_me"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

security = HTTPBearer()
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# ---------------------------------
# Подключение к PostgreSQL
# ---------------------------------
DATABASE_URL = "postgresql+psycopg2://postgres:A123a123s@localhost:5432/smartcanteen"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


# ---------------------------------
# SQLAlchemy модели
# ---------------------------------
class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    email = Column(String(100), nullable=False, unique=True, index=True)
    password_hash = Column(Text, nullable=False)
    role = Column(String(20), nullable=False, default="user")
    diet_types = Column(ARRAY(Text), nullable=False, default=list)
    allergens = Column(ARRAY(Text), nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    orders = relationship("OrderDB", back_populates="user", cascade="all, delete-orphan")


class DishDB(Base):
    __tablename__ = "dishes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    category = Column(String(50), nullable=False, default="main")
    calories = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    ingredients = Column(ARRAY(Text), nullable=False, default=list)
    description = Column(Text, nullable=False)
    allergen_warning = Column(String(200), nullable=False)
    image_url = Column(Text, nullable=True)
    is_available = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("calories >= 0", name="check_dish_calories_nonnegative"),
        CheckConstraint("price > 0", name="check_dish_price_positive"),
    )

    order_items = relationship("OrderItemDB", back_populates="dish")


class OrderDB(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False, default=0)
    status = Column(String(30), nullable=False, default="created")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("UserDB", back_populates="orders")
    items = relationship("OrderItemDB", back_populates="order", cascade="all, delete-orphan")


class OrderItemDB(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    dish_id = Column(Integer, ForeignKey("dishes.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_order_item_quantity_positive"),
        CheckConstraint("unit_price > 0", name="check_order_item_unit_price_positive"),
    )

    order = relationship("OrderDB", back_populates="items")
    dish = relationship("DishDB", back_populates="order_items")


# ---------------------------------
# Pydantic модели
# ---------------------------------
class DishBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    category: str = Field(..., min_length=2, max_length=50)
    calories: int = Field(..., ge=0)
    price: float = Field(..., gt=0)
    ingredients: List[str] = Field(default_factory=list)
    description: str = Field(..., min_length=5, max_length=500)
    allergenWarning: str = Field(..., min_length=2, max_length=200)
    imageUrl: Optional[str] = None
    isAvailable: bool = True


class DishCreate(DishBase):
    pass


class DishUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    category: Optional[str] = Field(None, min_length=2, max_length=50)
    calories: Optional[int] = Field(None, ge=0)
    price: Optional[float] = Field(None, gt=0)
    ingredients: Optional[List[str]] = None
    description: Optional[str] = Field(None, min_length=5, max_length=500)
    allergenWarning: Optional[str] = Field(None, min_length=2, max_length=200)
    imageUrl: Optional[str] = None
    isAvailable: Optional[bool] = None


class Dish(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    calories: int
    price: float
    ingredients: List[str]
    description: str
    allergenWarning: str
    imageUrl: Optional[str]
    isAvailable: bool


class OrderItemCreate(BaseModel):
    dish_id: int
    quantity: int = Field(default=1, gt=0)


class OrderCreate(BaseModel):
    items: List[OrderItemCreate] = Field(..., min_length=1)


class OrderItemOut(BaseModel):
    dish_id: int
    dish_name: str
    quantity: int
    unit_price: float


class Order(BaseModel):
    id: int
    user: str
    total_price: float
    status: str
    dishes: List[OrderItemOut]


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=4, max_length=100)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4, max_length=100)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    username: str
    email: str
    role: str


class UserInfo(BaseModel):
    id: int
    username: str
    email: str
    role: str
    diet_types: List[str]
    allergens: List[str]


class UserPreferencesUpdate(BaseModel):
    diet_types: List[str] = Field(default_factory=list)
    allergens: List[str] = Field(default_factory=list)


class UploadImageResponse(BaseModel):
    imageUrl: str
    filename: str


# ---------------------------------
# DB helpers
# ---------------------------------
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def decimal_to_float(value) -> float:
    return float(value) if value is not None else 0.0


# ---------------------------------
# Служебные функции
# ---------------------------------
def get_user_by_username(db: Session, username: str):
    return db.query(UserDB).filter(UserDB.username.ilike(username)).first()


def get_user_by_email(db: Session, email: str):
    return db.query(UserDB).filter(UserDB.email.ilike(email)).first()


def get_dish_by_id(db: Session, dish_id: int):
    return db.query(DishDB).filter(DishDB.id == dish_id).first()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def build_auth_response(user: UserDB):
    token = create_access_token(
        {
            "sub": user.username,
            "email": user.email,
            "role": user.role,
        }
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user.username,
        "email": user.email,
        "role": user.role,
    }


def dish_to_response(dish: DishDB) -> Dish:
    return Dish(
        id=dish.id,
        name=dish.name,
        category=dish.category,
        calories=dish.calories,
        price=decimal_to_float(dish.price),
        ingredients=dish.ingredients or [],
        description=dish.description,
        allergenWarning=dish.allergen_warning,
        imageUrl=dish.image_url,
        isAvailable=dish.is_available,
    )


def order_to_response(order: OrderDB) -> Order:
    return Order(
        id=order.id,
        user=order.user.username,
        total_price=decimal_to_float(order.total_price),
        status=order.status,
        dishes=[
            OrderItemOut(
                dish_id=item.dish_id,
                dish_name=item.dish.name,
                quantity=item.quantity,
                unit_price=decimal_to_float(item.unit_price),
            )
            for item in order.items
        ],
    )


# ---------------------------------
# Правила тегов блюда
# ---------------------------------
def infer_allergen_tags(ingredients: List[str], allergen_warning: str) -> List[str]:
    text_blob = " ".join(ingredients).lower() + " " + (allergen_warning or "").lower()

    rules = {
        "milk": [
            "молок", "молочный",
            "сыр", "фета", "брынз",
            "слив", "сливки",
            "сметан", "сметана",
            "твор", "творог",
            "йогурт",
            "кефир",
            "морожен",
            "капучино", "латте",
            "крем",
        ],
        "eggs": [
            "яйц", "яйцо", "яйца",
            "омлет",
            "майонез",
        ],
        "nuts": [
            "орех", "орехи",
            "миндаль",
            "фундук",
            "грецк",
            "грецкие",
        ],
        "peanuts": [
            "арахис",
        ],
        "fish": [
            "рыб", "рыба",
            "тунец",
            "уха",
            "лосось",
            "треск",
            "филе рыбы",
        ],
        "seafood": [
            "морепродукт",
            "кревет",
            "мид",
            "кальмар",
        ],
        "soy": [
            "соя", "соев", "соус терияки", "терияки",
        ],
        "gluten": [
            "мука",
            "лапша",
            "макарон", "макароны",
            "хлеб",
            "булка", "булоч",
            "сухар", "сухарики",
            "блин", "блины", "блинчики",
            "овсян", "овсяные хлопья",
            "перлов",
            "булгур",
            "лазань", "листы лазаньи",
            "манка",
            "печенье",
            "круассан",
        ],
        "sesame": [
            "кунжут",
        ],
    }

    found = []
    for tag, keywords in rules.items():
        if any(word in text_blob for word in keywords):
            found.append(tag)

    return sorted(set(found))


def infer_diet_tags(category: str, ingredients: List[str], allergen_warning: str, calories: int) -> List[str]:
    text_blob = " ".join(ingredients).lower() + " " + (allergen_warning or "").lower()

    has_meat = any(
        word in text_blob
        for word in [
            "говяд", "говядин",
            "свин", "свинин",
            "куриц", "курица", "куриное", "куриный", "куриное филе", "куриный фарш",
            "индейк", "индейка",
            "бекон",
            "ветчин", "ветчина",
            "мяс", "мясо",
            "котлет",
            "тефтел", "тефтели",
            "фрикадель",
            "сосиск", "сосиска",
            "колбас", "колбаса",
            "фарш",
            "плов с курицей",
            "курица с тушёной капустой",
        ]
    )

    has_fish = any(
        word in text_blob
        for word in [
            "рыб", "рыба",
            "тунец",
            "уха",
            "лосось",
            "треск",
            "филе рыбы",
        ]
    )

    has_seafood = any(
        word in text_blob
        for word in [
            "кревет",
            "мид",
            "кальмар",
            "морепродукт",
        ]
    )

    has_milk = any(
        word in text_blob
        for word in [
            "молок", "молочный",
            "сыр", "фета", "брынз",
            "слив", "сливки",
            "сметан", "сметана",
            "твор", "творог",
            "йогурт",
            "кефир",
            "морожен",
            "капучино", "латте",
            "крем",
        ]
    )

    has_eggs = any(
        word in text_blob
        for word in [
            "яйц", "яйцо", "яйца",
            "омлет",
            "майонез",
        ]
    )

    has_gluten = any(
        word in text_blob
        for word in [
            "мука",
            "лапша",
            "макарон", "макароны",
            "хлеб",
            "булка", "булоч",
            "сухар", "сухарики",
            "блин", "блины", "блинчики",
            "овсян", "овсяные хлопья",
            "перлов",
            "булгур",
            "лазань", "листы лазаньи",
            "манка",
            "печенье",
            "круассан",
        ]
    )

    has_pork = any(
        word in text_blob
        for word in [
            "свин", "свинин",
            "бекон",
            "ветчин", "ветчина",
        ]
    )

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


def is_dish_allowed_for_user(user_diets: List[str], user_allergens: List[str], dish: DishDB) -> bool:
    dish_allergens = infer_allergen_tags(dish.ingredients or [], dish.allergen_warning or "")
    dish_diets = infer_diet_tags(
        dish.category,
        dish.ingredients or [],
        dish.allergen_warning or "",
        int(dish.calories),
    )

    if any(a in dish_allergens for a in user_allergens):
        return False

    for diet in user_diets:
        if diet in STRICT_DIETS and diet not in dish_diets:
            return False

    return True


def get_moscow_context():
    now = datetime.now(MOSCOW_TZ)
    weekday = now.strftime("%A").lower()
    hour = now.hour

    if 6 <= hour <= 10:
        time_of_day = "breakfast"
    elif 11 <= hour <= 15:
        time_of_day = "lunch"
    else:
        time_of_day = "dinner"

    return weekday, hour, time_of_day


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Недействительный или просроченный токен",
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_by_username(db, username)
    if user is None:
        raise credentials_exception

    return user


def get_current_admin(current_user: UserDB = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен: требуется роль администратора",
        )
    return current_user


# ---------------------------------
# Инициализация
# ---------------------------------
@app.on_event("startup")
def startup():
    global ranking_model

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        admin = db.query(UserDB).filter(UserDB.username == "admin").first()
        if not admin:
            admin = UserDB(
                username="admin",
                email="admin@smartcanteen.ru",
                password_hash=get_password_hash("12345"),
                role="admin",
                diet_types=[],
                allergens=[],
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()

    if MODEL_PATH.exists():
        ranking_model = CatBoostClassifier()
        ranking_model.load_model(str(MODEL_PATH))
        print(f"Модель загружена: {MODEL_PATH}")
    else:
        print(f"Файл модели не найден: {MODEL_PATH}")


# ---------------------------------
# Базовый маршрут
# ---------------------------------
@app.get("/")
def home():
    return {"message": "SmartCanteen API работает"}


# ---------------------------------
# Пользователь
# ---------------------------------
@app.get("/me", response_model=UserInfo)
def read_current_user(current_user: UserDB = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "diet_types": current_user.diet_types or [],
        "allergens": current_user.allergens or [],
    }


@app.put("/me/preferences", response_model=UserInfo)
def update_preferences(
    payload: UserPreferencesUpdate,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.diet_types = payload.diet_types
    current_user.allergens = payload.allergens
    db.commit()
    db.refresh(current_user)

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "diet_types": current_user.diet_types or [],
        "allergens": current_user.allergens or [],
    }


# ---------------------------------
# Загрузка изображений
# ---------------------------------
@app.post("/upload-image", response_model=UploadImageResponse)
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    admin_user: UserDB = Depends(get_current_admin),
):
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Разрешены только JPG, PNG и WEBP изображения",
        )

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"

    filename = f"{uuid4().hex}{suffix}"
    file_path = UPLOADS_DIR / filename

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Файл слишком большой. Максимум 5 МБ",
        )

    file_path.write_bytes(content)

    image_url = str(request.base_url).rstrip("/") + f"/uploads/{filename}"
    return {
        "imageUrl": image_url,
        "filename": filename,
    }


# ---------------------------------
# CRUD для блюд
# ---------------------------------
@app.get("/dishes", response_model=List[Dish])
def get_dishes(db: Session = Depends(get_db)):
    dishes = db.query(DishDB).order_by(DishDB.id.asc()).all()
    return [dish_to_response(dish) for dish in dishes]


@app.get("/recommendations", response_model=List[Dish])
def get_recommendations(
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dishes = (
        db.query(DishDB)
        .filter(DishDB.is_available == True)
        .order_by(DishDB.id.asc())
        .all()
    )

    allowed_dishes = [
        dish for dish in dishes
        if is_dish_allowed_for_user(
            current_user.diet_types or [],
            current_user.allergens or [],
            dish,
        )
    ]

    if not allowed_dishes:
        return []

    if ranking_model is None:
        return [dish_to_response(dish) for dish in allowed_dishes]

    weekday, _, time_of_day = get_moscow_context()

    rows = []
    for dish in allowed_dishes:
        rows.append(
            {
                "user_id": current_user.id,
                "dish_id": dish.id,
                "category": dish.category,
                "price": float(dish.price),
                "calories": int(dish.calories),
                "weekday": weekday,
                "time_of_day": time_of_day,
                "diet_types": ",".join(sorted(current_user.diet_types or [])),
                "allergens": ",".join(sorted(current_user.allergens or [])),
            }
        )

    pred_df = pd.DataFrame(rows)
    scores = ranking_model.predict_proba(pred_df)[:, 1]

    ranked = list(zip(allowed_dishes, scores))
    ranked.sort(key=lambda x: x[1], reverse=True)

    return [dish_to_response(dish) for dish, _ in ranked]


@app.get("/dishes/{dish_id}", response_model=Dish)
def get_dish(dish_id: int, db: Session = Depends(get_db)):
    dish = get_dish_by_id(db, dish_id)
    if dish is None:
        raise HTTPException(status_code=404, detail="Блюдо не найдено")
    return dish_to_response(dish)


@app.post("/dishes", response_model=Dish, status_code=201)
def create_dish(
    dish: DishCreate,
    admin_user: UserDB = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    existing = db.query(DishDB).filter(DishDB.name.ilike(dish.name)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Блюдо с таким названием уже существует")

    new_dish = DishDB(
        name=dish.name,
        category=dish.category,
        calories=dish.calories,
        price=dish.price,
        ingredients=dish.ingredients,
        description=dish.description,
        allergen_warning=dish.allergenWarning,
        image_url=dish.imageUrl,
        is_available=dish.isAvailable,
    )
    db.add(new_dish)
    db.commit()
    db.refresh(new_dish)

    return dish_to_response(new_dish)


@app.put("/dishes/{dish_id}", response_model=Dish)
def update_dish(
    dish_id: int,
    updated_dish: DishUpdate,
    admin_user: UserDB = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    dish = get_dish_by_id(db, dish_id)
    if dish is None:
        raise HTTPException(status_code=404, detail="Блюдо не найдено")

    update_data = updated_dish.model_dump(exclude_unset=True)

    if "name" in update_data:
        existing = (
            db.query(DishDB)
            .filter(DishDB.id != dish_id, DishDB.name.ilike(update_data["name"]))
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Блюдо с таким названием уже существует")

    if "name" in update_data:
        dish.name = update_data["name"]
    if "category" in update_data:
        dish.category = update_data["category"]
    if "calories" in update_data:
        dish.calories = update_data["calories"]
    if "price" in update_data:
        dish.price = update_data["price"]
    if "ingredients" in update_data:
        dish.ingredients = update_data["ingredients"]
    if "description" in update_data:
        dish.description = update_data["description"]
    if "allergenWarning" in update_data:
        dish.allergen_warning = update_data["allergenWarning"]
    if "imageUrl" in update_data:
        dish.image_url = update_data["imageUrl"]
    if "isAvailable" in update_data:
        dish.is_available = update_data["isAvailable"]

    dish.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(dish)
    return dish_to_response(dish)


@app.delete("/dishes/{dish_id}")
def delete_dish(
    dish_id: int,
    admin_user: UserDB = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    dish = get_dish_by_id(db, dish_id)
    if dish is None:
        raise HTTPException(status_code=404, detail="Блюдо не найдено")

    db.delete(dish)
    db.commit()
    return {"message": "Блюдо успешно удалено"}


# ---------------------------------
# Заказы
# ---------------------------------
@app.get("/orders", response_model=List[Order])
def get_orders(admin_user: UserDB = Depends(get_current_admin), db: Session = Depends(get_db)):
    orders = db.query(OrderDB).order_by(OrderDB.created_at.desc()).all()
    return [order_to_response(order) for order in orders]


@app.get("/my-orders", response_model=List[Order])
def get_my_orders(current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    orders = (
        db.query(OrderDB)
        .filter(OrderDB.user_id == current_user.id)
        .order_by(OrderDB.created_at.desc())
        .all()
    )
    return [order_to_response(order) for order in orders]


@app.post("/orders")
def create_order(order: OrderCreate, current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    total = Decimal("0")

    db_order = OrderDB(
        user_id=current_user.id,
        total_price=0,
        status="created",
    )
    db.add(db_order)
    db.flush()

    for item in order.items:
        dish = get_dish_by_id(db, item.dish_id)
        if dish is None:
            raise HTTPException(status_code=404, detail=f"Блюдо с id={item.dish_id} не найдено")
        if not dish.is_available:
            raise HTTPException(status_code=400, detail=f"Блюдо '{dish.name}' сейчас недоступно")

        line_total = Decimal(str(dish.price)) * item.quantity
        total += line_total

        db_item = OrderItemDB(
            order_id=db_order.id,
            dish_id=dish.id,
            quantity=item.quantity,
            unit_price=dish.price,
        )
        db.add(db_item)

    db_order.total_price = total
    db.commit()
    db.refresh(db_order)

    return {
        "message": "Заказ успешно создан",
        "order": order_to_response(db_order),
    }


# ---------------------------------
# Регистрация и вход
# ---------------------------------
@app.post("/register", response_model=AuthResponse, status_code=201)
def register(user_data: RegisterRequest, db: Session = Depends(get_db)):
    if get_user_by_username(db, user_data.username):
        raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")

    if get_user_by_email(db, user_data.email):
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")

    new_user = UserDB(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        role="user",
        diet_types=[],
        allergens=[],
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return build_auth_response(new_user)


@app.post("/login", response_model=AuthResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = get_user_by_username(db, login_data.username)

    if user is None or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    return build_auth_response(user)