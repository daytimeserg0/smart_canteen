from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field

app = FastAPI(title="SmartCanteen API")


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
# Модели блюд
# ---------------------------------
class DishBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    calories: int = Field(..., ge=0)
    price: float = Field(..., gt=0)
    ingredients: List[str] = Field(default_factory=list)
    description: str = Field(..., min_length=5, max_length=500)
    allergenWarning: str = Field(..., min_length=2, max_length=200)


class DishCreate(DishBase):
    pass


class DishUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    calories: Optional[int] = Field(None, ge=0)
    price: Optional[float] = Field(None, gt=0)
    ingredients: Optional[List[str]] = None
    description: Optional[str] = Field(None, min_length=5, max_length=500)
    allergenWarning: Optional[str] = Field(None, min_length=2, max_length=200)


class Dish(DishBase):
    id: int


# ---------------------------------
# Модели заказов
# ---------------------------------
class OrderCreate(BaseModel):
    dishes: List[int] = Field(..., min_length=1)


class Order(BaseModel):
    id: int
    user: str
    dishes: List[int]


# ---------------------------------
# Модели авторизации
# ---------------------------------
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=100)
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


# ---------------------------------
# Временное хранилище
# ---------------------------------
dishes = [
    {
        "id": 1,
        "name": "Борщ",
        "calories": 250,
        "price": 120,
        "ingredients": ["свекла", "мясо", "капуста"],
        "description": "Традиционный борщ с мясом и овощами.",
        "allergenWarning": "Может содержать следы глютена",
    },
    {
        "id": 2,
        "name": "Салат Цезарь",
        "calories": 220,
        "price": 180,
        "ingredients": ["курица", "салат", "сыр", "соус"],
        "description": "Салат с курицей, сыром и фирменным соусом.",
        "allergenWarning": "Содержит молочные продукты",
    },
    {
        "id": 3,
        "name": "Компот",
        "calories": 90,
        "price": 50,
        "ingredients": ["сухофрукты", "вода", "сахар"],
        "description": "Домашний компот из сухофруктов.",
        "allergenWarning": "Без основных аллергенов",
    },
]

orders = []

users = [
    {
        "id": 1,
        "username": "admin",
        "email": "admin@smartcanteen.ru",
        "password": pwd_context.hash("12345"),
        "role": "admin",
    }
]


# ---------------------------------
# Служебные функции
# ---------------------------------
def find_dish_by_id(dish_id: int):
    for dish in dishes:
        if dish["id"] == dish_id:
            return dish
    return None


def find_user_by_username(username: str):
    for user in users:
        if user["username"].lower() == username.lower():
            return user
    return None


def find_user_by_email(email: str):
    for user in users:
        if user["email"].lower() == email.lower():
            return user
    return None


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


def build_auth_response(user: dict):
    token = create_access_token(
        {
            "sub": user["username"],
            "email": user["email"],
            "role": user["role"],
        }
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
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

    user = find_user_by_username(username)
    if user is None:
        raise credentials_exception

    return user


def get_current_admin(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен: требуется роль администратора",
        )
    return current_user


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
def read_current_user(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "email": current_user["email"],
        "role": current_user["role"],
    }


# ---------------------------------
# CRUD для блюд
# ---------------------------------
@app.get("/dishes", response_model=List[Dish])
def get_dishes():
    return dishes


@app.get("/dishes/{dish_id}", response_model=Dish)
def get_dish(dish_id: int):
    dish = find_dish_by_id(dish_id)
    if dish is None:
        raise HTTPException(status_code=404, detail="Блюдо не найдено")
    return dish


@app.post("/dishes", response_model=Dish, status_code=201)
def create_dish(dish: DishCreate, admin_user: dict = Depends(get_current_admin)):
    for existing_dish in dishes:
        if existing_dish["name"].lower() == dish.name.lower():
            raise HTTPException(status_code=400, detail="Блюдо с таким названием уже существует")

    new_id = max([d["id"] for d in dishes], default=0) + 1
    new_dish = {"id": new_id, **dish.model_dump()}
    dishes.append(new_dish)
    return new_dish


@app.put("/dishes/{dish_id}", response_model=Dish)
def update_dish(
    dish_id: int,
    updated_dish: DishUpdate,
    admin_user: dict = Depends(get_current_admin),
):
    dish = find_dish_by_id(dish_id)
    if dish is None:
        raise HTTPException(status_code=404, detail="Блюдо не найдено")

    update_data = updated_dish.model_dump(exclude_unset=True)

    if "name" in update_data:
        for existing_dish in dishes:
            if existing_dish["id"] != dish_id and existing_dish["name"].lower() == update_data["name"].lower():
                raise HTTPException(status_code=400, detail="Блюдо с таким названием уже существует")

    dish.update(update_data)
    return dish


@app.delete("/dishes/{dish_id}")
def delete_dish(dish_id: int, admin_user: dict = Depends(get_current_admin)):
    dish = find_dish_by_id(dish_id)
    if dish is None:
        raise HTTPException(status_code=404, detail="Блюдо не найдено")

    dishes.remove(dish)
    return {"message": "Блюдо успешно удалено"}


# ---------------------------------
# Заказы
# ---------------------------------
@app.get("/orders")
def get_orders(admin_user: dict = Depends(get_current_admin)):
    return orders


@app.post("/orders")
def create_order(order: OrderCreate, current_user: dict = Depends(get_current_user)):
    for dish_id in order.dishes:
        if find_dish_by_id(dish_id) is None:
            raise HTTPException(status_code=404, detail=f"Блюдо с id={dish_id} не найдено")

    new_order = {
        "id": max([o["id"] for o in orders], default=0) + 1,
        "user": current_user["username"],
        "dishes": order.dishes,
    }
    orders.append(new_order)

    return {
        "message": "Заказ успешно создан",
        "order": new_order,
    }


# ---------------------------------
# Регистрация и вход
# ---------------------------------
@app.post("/register", response_model=AuthResponse, status_code=201)
def register(user_data: RegisterRequest):
    if find_user_by_username(user_data.username):
        raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")

    if find_user_by_email(user_data.email):
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")

    new_user = {
        "id": max([u["id"] for u in users], default=0) + 1,
        "username": user_data.username,
        "email": user_data.email,
        "password": get_password_hash(user_data.password),
        "role": "user",
    }
    users.append(new_user)

    return build_auth_response(new_user)


@app.post("/login", response_model=AuthResponse)
def login(login_data: LoginRequest):
    user = find_user_by_username(login_data.username)

    if user is None or not verify_password(login_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    return build_auth_response(user)


# uvicorn main:app --reload