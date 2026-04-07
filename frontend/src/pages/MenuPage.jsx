import { useEffect, useMemo, useState } from "react";
import { getDishes } from "../api";
import DishCard from "../components/DishCard";
import { DISH_CATEGORIES } from "../data/categories";

function MenuPage() {
  const [dishes, setDishes] = useState([]);
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadDishes = async () => {
      try {
        setLoading(true);
        setError("");
        const data = await getDishes();
        setDishes(data);
      } catch (err) {
        setError(err.message || "Не удалось загрузить блюда");
      } finally {
        setLoading(false);
      }
    };

    loadDishes();
  }, []);

  const filteredDishes = useMemo(() => {
    return dishes.filter((dish) => {
      const matchesSearch = dish.name
        .toLowerCase()
        .includes(search.toLowerCase());

      const matchesCategory =
        selectedCategory === "all" || dish.category === selectedCategory;

      return matchesSearch && matchesCategory;
    });
  }, [dishes, search, selectedCategory]);

  return (
    <div className="menu-page">
      <section className="hero-block">
        <h2>Меню столовой</h2>
        <p>
          Выберите блюда, посмотрите состав, калорийность и предупреждения
          об аллергенах.
        </p>
      </section>

      <div className="menu-controls" style={{ gap: "12px", flexWrap: "wrap" }}>
        <input
          type="text"
          placeholder="Поиск блюда..."
          className="search-input"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <select
          className="search-input"
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          style={{ maxWidth: "260px" }}
        >
          {DISH_CATEGORIES.map((category) => (
            <option key={category.value} value={category.value}>
              {category.label}
            </option>
          ))}
        </select>
      </div>

      {loading && <p>Загрузка блюд...</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}
      {!loading && !error && filteredDishes.length === 0 && (
        <p>Блюда не найдены.</p>
      )}

      <div className="dishes-grid">
        {filteredDishes.map((dish) => (
          <DishCard key={dish.id} dish={dish} />
        ))}
      </div>
    </div>
  );
}

export default MenuPage;