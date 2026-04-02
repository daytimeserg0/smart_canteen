import { Link } from "react-router-dom";

function DishCard({ dish }) {
  return (
    <article className="dish-card">
      <div className="dish-card-top">
        <div className="dish-badge">{dish.calories} ккал</div>
        <div className="dish-price">{dish.price} ₽</div>
      </div>

      <h3 className="dish-title">{dish.name}</h3>

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

        <button className="btn btn-primary">В заказ</button>
      </div>
    </article>
  );
}

export default DishCard;