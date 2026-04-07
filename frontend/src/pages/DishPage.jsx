import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { addToCart, getDishById } from "../api";

function DishPage() {
  const { id } = useParams();
  const [dish, setDish] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadDish = async () => {
      try {
        setLoading(true);
        setError("");
        const data = await getDishById(id);
        setDish(data);
      } catch (err) {
        setError(err.message || "Не удалось загрузить блюдо");
      } finally {
        setLoading(false);
      }
    };

    loadDish();
  }, [id]);

  const handleAddToCart = () => {
    addToCart(dish);
    alert(`Блюдо "${dish.name}" добавлено в заказ`);
  };

  if (loading) {
    return <p>Загрузка блюда...</p>;
  }

  if (error) {
    return <p style={{ color: "red" }}>{error}</p>;
  }

  if (!dish) {
    return <h2>Блюдо не найдено</h2>;
  }

  return (
    <div className="dish-page">
      <div className="dish-page-main">
        {dish.imageUrl ? (
          <img
            src={dish.imageUrl}
            alt={dish.name}
            style={{
              width: "320px",
              maxWidth: "100%",
              borderRadius: "20px",
              objectFit: "cover",
            }}
          />
        ) : (
          <div className="dish-image-placeholder">Фото блюда</div>
        )}

        <div className="dish-info-panel">
          <h1>{dish.name}</h1>
          <p className="dish-description">{dish.description}</p>

          <h2 className="ingredients-title">Состав</h2>
          <ul className="ingredients-list">
            {dish.ingredients.map((ingredient, index) => (
              <li key={index}>• {ingredient}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="allergen-box">⚠ {dish.allergenWarning}</div>

      <div className="dish-actions">
        <div className="dish-actions-price">Цена: {dish.price} ₽</div>
        <button className="btn btn-primary" onClick={handleAddToCart}>
          Добавить в заказ
        </button>
      </div>
    </div>
  );
}

export default DishPage;