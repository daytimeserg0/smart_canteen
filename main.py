from typing import List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
class Order(BaseModel):
    user: str = Field(..., min_length=2, max_length=100)
    dishes: List[int] = Field(..., min_length=1)


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
        "password": "12345",
        "role": "admin",
    }
]

tokens = {}


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


# ---------------------------------
# Базовый маршрут
# ---------------------------------
@app.get("/")
def home():
    return {"message": "SmartCanteen API работает"}


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
def create_dish(dish: DishCreate):
    for existing_dish in dishes:
        if existing_dish["name"].lower() == dish.name.lower():
            raise HTTPException(status_code=400, detail="Блюдо с таким названием уже существует")

    new_id = max([d["id"] for d in dishes], default=0) + 1
    new_dish = {"id": new_id, **dish.model_dump()}
    dishes.append(new_dish)
    return new_dish


@app.put("/dishes/{dish_id}", response_model=Dish)
def update_dish(dish_id: int, updated_dish: DishUpdate):
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
def delete_dish(dish_id: int):
    dish = find_dish_by_id(dish_id)
    if dish is None:
        raise HTTPException(status_code=404, detail="Блюдо не найдено")

    dishes.remove(dish)
    return {"message": "Блюдо успешно удалено"}


# ---------------------------------
# Заказы
# ---------------------------------
@app.get("/orders")
def get_orders():
    return orders


@app.post("/orders")
def create_order(order: Order):
    for dish_id in order.dishes:
        if find_dish_by_id(dish_id) is None:
            raise HTTPException(status_code=404, detail=f"Блюдо с id={dish_id} не найдено")

    new_order = order.model_dump()
    orders.append(new_order)

    return {
        "message": "Заказ успешно создан",
        "order": new_order
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
        "password": user_data.password,
        "role": "user",
    }
    users.append(new_user)

    token = str(uuid4())
    tokens[token] = {
        "username": new_user["username"],
        "email": new_user["email"],
        "role": new_user["role"],
    }

    return {
        "access_token": token,
        "token_type": "bearer",
        "username": new_user["username"],
        "email": new_user["email"],
        "role": new_user["role"],
    }


@app.post("/login", response_model=AuthResponse)
def login(login_data: LoginRequest):
    user = find_user_by_username(login_data.username)

    if user is None or user["password"] != login_data.password:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    token = str(uuid4())
    tokens[token] = {
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
    }

    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
    }


# uvicorn main:app --reload