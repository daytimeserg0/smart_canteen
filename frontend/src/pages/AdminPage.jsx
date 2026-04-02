import { adminDishes } from "../data/admin";

function AdminPage() {
  return (
    <div className="admin-page">
      <div className="admin-header">
        <div>
          <h1 className="section-title">Панель администратора</h1>
          <p className="section-subtitle">
            Управление списком блюд: просмотр, редактирование, удаление и добавление.
          </p>
        </div>

        <button className="btn btn-primary">Добавить блюдо</button>
      </div>

      <div className="admin-list">
        {adminDishes.map((dish) => (
          <div key={dish.id} className="admin-row">
            <span className="admin-dish-name">{dish.name}</span>
            <button className="btn btn-light">Редактировать</button>
            <button className="btn btn-danger">Удалить</button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default AdminPage;