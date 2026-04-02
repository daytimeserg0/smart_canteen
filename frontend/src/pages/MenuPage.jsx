import { dishes } from "../data/dishes";
import DishCard from "../components/DishCard";

function MenuPage() {
  return (
    <div className="menu-page">
      <section className="hero-block">
        <h2>Меню столовой</h2>
        <p>
          Выберите блюда, посмотрите состав, калорийность и предупреждения
          об аллергенах. Интерфейс подготовлен как клиентская часть проекта
          SmartCanteen.
        </p>
      </section>

      <div className="menu-controls">
        <input
          type="text"
          placeholder="Поиск блюда..."
          className="search-input"
        />
        <button className="filter-btn">Фильтр</button>
      </div>

      <div className="dishes-grid">
        {dishes.map((dish) => (
          <DishCard key={dish.id} dish={dish} />
        ))}
      </div>
    </div>
  );
}

export default MenuPage;