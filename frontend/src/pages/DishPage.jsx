import { useParams } from "react-router-dom";
import { dishes } from "../data/dishes";

function DishPage() {
  const { id } = useParams();
  const dish = dishes.find((item) => item.id === Number(id));

  if (!dish) {
    return <h2>Блюдо не найдено</h2>;
  }

  return (
    <div className="dish-page">
      <div className="dish-page-main">
        <div className="dish-image-placeholder">Фото блюда</div>

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

      <div className="allergen-box">
        ⚠ {dish.allergenWarning}
      </div>

      <div className="dish-actions">
        <div className="dish-actions-price">Цена: {dish.price} ₽</div>
        <button className="btn btn-primary">Добавить в заказ</button>
      </div>
    </div>
  );
}

export default DishPage;