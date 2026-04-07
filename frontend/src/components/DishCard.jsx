import { Link } from "react-router-dom";
import { addToCart } from "../api";
import { CATEGORY_LABELS } from "../data/categories";

function DishCard({ dish }) {
  const handleAddToCart = () => {
    addToCart(dish);
    alert(`Блюдо "${dish.name}" добавлено в заказ`);
  };

  return (
    <article className="dish-card">
      {dish.imageUrl ? (
        <img
          src={dish.imageUrl}
          alt={dish.name}
          style={{
            width: "100%",
            height: "180px",
            objectFit: "cover",
            borderRadius: "16px",
            marginBottom: "12px",
          }}
        />
      ) : (
        <div className="dish-image-placeholder">Фото блюда</div>
      )}

      <div className="dish-card-top">
        <div className="dish-badge">{dish.calories} ккал</div>
        <div className="dish-price">{dish.price} ₽</div>
      </div>

      <h3 className="dish-title">{dish.name}</h3>

      <p
        style={{
          margin: "0 0 10px 0",
          fontSize: "14px",
          color: "#64748b",
          fontWeight: 600,
        }}
      >
        Категория: {CATEGORY_LABELS[dish.category] || "Без категории"}
      </p>

      <p className="dish-warning">⚠ {dish.allergenWarning}</p>

      <div className="dish-ingredients">
        {dish.ingredients.slice(0, 3).map((item, index) => (
          <span key={index} className="ingredient-tag">
            {item}
          </span>
        ))}
      </div>

      <div className="dish-buttons">
        <Link to={`/dish/${dish.id}`} className="btn btn-light">
          Подробнее
        </Link>

        <button
          className="btn btn-primary"
          onClick={handleAddToCart}
          disabled={!dish.isAvailable}
        >
          {dish.isAvailable ? "В заказ" : "Недоступно"}
        </button>
      </div>
    </article>
  );
}

export default DishCard;