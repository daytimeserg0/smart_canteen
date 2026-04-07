import { useEffect, useMemo, useState } from "react";
import {
  createDish,
  deleteDish,
  getDishes,
  getOrders,
  updateDish,
  uploadDishImage,
} from "../api";
import { useAuth } from "../context/AuthContext";
import { ADMIN_DISH_CATEGORIES, CATEGORY_LABELS } from "../data/categories";

const emptyForm = {
  name: "",
  category: "main",
  calories: "",
  price: "",
  ingredients: "",
  description: "",
  allergenWarning: "",
  imageUrl: "",
};

function AdminPage() {
  const { token } = useAuth();

  const [dishes, setDishes] = useState([]);
  const [orders, setOrders] = useState([]);
  const [dishSearch, setDishSearch] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);

  const [loading, setLoading] = useState(true);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadData = async () => {
    try {
      setLoading(true);
      setError("");

      const [dishesData, ordersData] = await Promise.all([
        getDishes(),
        getOrders(token),
      ]);

      setDishes(dishesData);
      setOrders(ordersData);
    } catch (err) {
      setError(err.message || "Не удалось загрузить данные администратора");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filteredDishes = useMemo(() => {
    const searchValue = dishSearch.trim().toLowerCase();

    if (!searchValue) {
      return dishes;
    }

    return dishes.filter((dish) => {
      const nameMatch = dish.name.toLowerCase().includes(searchValue);
      const categoryLabel = (CATEGORY_LABELS[dish.category] || "").toLowerCase();
      const categoryValue = (dish.category || "").toLowerCase();

      return (
        nameMatch ||
        categoryLabel.includes(searchValue) ||
        categoryValue.includes(searchValue)
      );
    });
  }, [dishes, dishSearch]);

  const handleChange = (e) => {
    setForm((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const resetForm = () => {
    setForm(emptyForm);
    setEditingId(null);
    setError("");
    setMessage("");
  };

  const handleEdit = (dish) => {
    setEditingId(dish.id);
    setForm({
      name: dish.name,
      category: dish.category || "main",
      calories: String(dish.calories),
      price: String(dish.price),
      ingredients: dish.ingredients.join(", "),
      description: dish.description,
      allergenWarning: dish.allergenWarning,
      imageUrl: dish.imageUrl || "",
    });
    setError("");
    setMessage("");
  };

  const handleDelete = async (id) => {
    try {
      setError("");
      setMessage("");
      await deleteDish(id, token);
      await loadData();
      setMessage("Блюдо удалено.");
    } catch (err) {
      setError(err.message || "Не удалось удалить блюдо");
    }
  };

  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setUploadingImage(true);
      setError("");
      setMessage("");

      const result = await uploadDishImage(file, token);

      setForm((prev) => ({
        ...prev,
        imageUrl: result.imageUrl,
      }));

      setMessage("Фото блюда успешно загружено.");
    } catch (err) {
      setError(err.message || "Не удалось загрузить изображение");
    } finally {
      setUploadingImage(false);
      e.target.value = "";
    }
  };

  const validateForm = () => {
    if (!form.name.trim()) return "Введите название блюда.";
    if (!form.category.trim()) return "Выберите категорию блюда.";
    if (!form.calories.trim()) return "Введите калорийность.";
    if (!form.price.trim()) return "Введите цену.";
    if (!form.ingredients.trim()) return "Введите ингредиенты.";
    if (!form.description.trim()) return "Введите описание.";
    if (!form.allergenWarning.trim()) {
      return "Введите предупреждение об аллергенах.";
    }

    if (Number.isNaN(Number(form.calories)) || Number(form.calories) < 0) {
      return "Калорийность должна быть числом не меньше 0.";
    }

    if (Number.isNaN(Number(form.price)) || Number(form.price) <= 0) {
      return "Цена должна быть числом больше 0.";
    }

    if (form.description.trim().length < 5) {
      return "Описание должно содержать минимум 5 символов.";
    }

    if (form.allergenWarning.trim().length < 2) {
      return "Предупреждение об аллергенах должно содержать минимум 2 символа.";
    }

    return "";
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    setError("");
    setMessage("");

    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    const payload = {
      name: form.name.trim(),
      category: form.category,
      calories: Number(form.calories),
      price: Number(form.price),
      ingredients: form.ingredients
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
      description: form.description.trim(),
      allergenWarning: form.allergenWarning.trim(),
      imageUrl: form.imageUrl.trim(),
      isAvailable: true,
    };

    try {
      if (editingId) {
        await updateDish(editingId, payload, token);
        setMessage("Блюдо обновлено.");
      } else {
        await createDish(payload, token);
        setMessage("Блюдо добавлено.");
      }

      resetForm();
      await loadData();
    } catch (err) {
      setError(err.message || "Не удалось сохранить блюдо");
    }
  };

  return (
    <div className="admin-page">
      <div className="admin-header">
        <div>
          <h1 className="section-title">Панель администратора</h1>
          <p className="section-subtitle">
            Управление блюдами и просмотр заказов.
          </p>
        </div>
      </div>

      {loading && <p>Загрузка данных...</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}
      {message && <p style={{ color: "green" }}>{message}</p>}

      <form
        onSubmit={handleSubmit}
        className="page-card"
        style={{ marginBottom: "24px" }}
      >
        <h2>{editingId ? "Редактировать блюдо" : "Добавить блюдо"}</h2>

        <input
          name="name"
          placeholder="Название"
          value={form.name}
          onChange={handleChange}
          className="search-input"
        />

        <select
          name="category"
          value={form.category}
          onChange={handleChange}
          className="search-input"
        >
          {ADMIN_DISH_CATEGORIES.map((category) => (
            <option key={category.value} value={category.value}>
              {category.label}
            </option>
          ))}
        </select>

        <input
          name="calories"
          placeholder="Калории"
          value={form.calories}
          onChange={handleChange}
          className="search-input"
        />

        <input
          name="price"
          placeholder="Цена"
          value={form.price}
          onChange={handleChange}
          className="search-input"
        />

        <input
          name="ingredients"
          placeholder="Ингредиенты через запятую"
          value={form.ingredients}
          onChange={handleChange}
          className="search-input"
        />

        <textarea
          name="description"
          placeholder="Описание"
          value={form.description}
          onChange={handleChange}
          className="search-input admin-textarea"
        />

        <input
          name="allergenWarning"
          placeholder="Предупреждение об аллергенах"
          value={form.allergenWarning}
          onChange={handleChange}
          className="search-input"
        />

        <input
          name="imageUrl"
          placeholder="Ссылка на фото блюда"
          value={form.imageUrl}
          onChange={handleChange}
          className="search-input"
        />

        <div style={{ marginTop: "10px", marginBottom: "10px" }}>
          <label
            style={{
              display: "block",
              fontWeight: 600,
              marginBottom: "8px",
            }}
          >
            Или загрузите фото с компьютера
          </label>
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={handleImageUpload}
            className="search-input"
          />
          {uploadingImage && (
            <p style={{ marginTop: "8px" }}>Загрузка изображения...</p>
          )}
        </div>

        {form.imageUrl && (
          <div style={{ marginTop: "12px", marginBottom: "12px" }}>
            <p className="section-subtitle" style={{ marginBottom: "8px" }}>
              Предпросмотр фото:
            </p>
            <img
              src={form.imageUrl}
              alt="Предпросмотр блюда"
              style={{
                width: "220px",
                maxWidth: "100%",
                borderRadius: "16px",
                objectFit: "cover",
              }}
            />
          </div>
        )}

        <div style={{ display: "flex", gap: "12px", marginTop: "12px" }}>
          <button
            className="btn btn-primary"
            type="submit"
            disabled={uploadingImage}
          >
            {editingId ? "Сохранить изменения" : "Добавить блюдо"}
          </button>

          {editingId && (
            <button
              className="btn btn-light"
              type="button"
              onClick={resetForm}
            >
              Отмена
            </button>
          )}
        </div>
      </form>

      <section className="page-card" style={{ marginBottom: "24px" }}>
        <div className="admin-header" style={{ marginBottom: "16px" }}>
          <div>
            <h2 className="section-title" style={{ marginBottom: "6px" }}>
              Список блюд
            </h2>
            <p className="section-subtitle">
              Поиск по названию и категории блюда.
            </p>
          </div>
        </div>

        <input
          type="text"
          placeholder="Найти блюдо..."
          className="search-input"
          value={dishSearch}
          onChange={(e) => setDishSearch(e.target.value)}
          style={{ marginBottom: "16px" }}
        />

        <div className="admin-list">
          {filteredDishes.length === 0 ? (
            <p>Блюда не найдены.</p>
          ) : (
            filteredDishes.map((dish) => (
              <div key={dish.id} className="admin-row">
                <div>
                  <strong>{dish.name}</strong>
                  <div className="profile-muted">
                    Категория: {CATEGORY_LABELS[dish.category] || "Без категории"}
                  </div>
                  <div className="profile-muted">
                    {dish.calories} ккал • {dish.price} ₽
                  </div>
                </div>

                <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                  <button
                    className="btn btn-light"
                    type="button"
                    onClick={() => handleEdit(dish)}
                  >
                    Редактировать
                  </button>
                  <button
                    className="btn btn-danger"
                    type="button"
                    onClick={() => handleDelete(dish.id)}
                  >
                    Удалить
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </section>

      <section className="page-card">
        <div className="admin-header" style={{ marginBottom: "16px" }}>
          <div>
            <h2 className="section-title" style={{ marginBottom: "6px" }}>
              Заказы
            </h2>
            <p className="section-subtitle">
              Список всех оформленных заказов.
            </p>
          </div>
        </div>

        {orders.length === 0 ? (
          <p>Заказов пока нет.</p>
        ) : (
          <div className="admin-list">
            {orders.map((order) => (
              <div key={order.id} className="admin-row">
                <div>
                  <strong>Заказ #{order.id}</strong>
                  <div className="profile-muted">
                    Пользователь: {order.user}
                  </div>
                  <div className="profile-muted">
                    Статус: {order.status}
                  </div>
                  <div className="profile-muted">
                    Сумма: {order.total_price} ₽
                  </div>
                  <div className="profile-muted" style={{ marginTop: "6px" }}>
                    Блюда:{" "}
                    {order.dishes
                      .map((item) => `${item.dish_name} ×${item.quantity}`)
                      .join(", ")}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default AdminPage;