import { useAuth } from "../context/AuthContext";

function ProfilePage() {
  const { user, logout } = useAuth();

  return (
    <div className="profile-page">
      <div className="profile-header">
        <div className="profile-email">{user?.email}</div>
        <p className="profile-muted">
          Вы вошли как <b>{user?.username}</b>. Роль: <b>{user?.role}</b>.
        </p>
      </div>

      <div className="profile-grid">
        <div className="profile-box">
          <h2>Аллергии</h2>
          <label className="checkbox-line">
            <input type="checkbox" />
            Орехи
          </label>
          <label className="checkbox-line">
            <input type="checkbox" />
            Молочные продукты
          </label>
          <label className="checkbox-line">
            <input type="checkbox" />
            Глютен
          </label>
          <button className="btn btn-light">Редактировать</button>
        </div>

        <div className="profile-box">
          <h2>Диета</h2>
          <label className="checkbox-line">
            <input type="checkbox" />
            Вегетарианская
          </label>
          <label className="checkbox-line">
            <input type="checkbox" />
            Без сахара
          </label>
          <label className="checkbox-line">
            <input type="checkbox" />
            Низкокалорийная
          </label>
          <button className="btn btn-light">Редактировать</button>
        </div>
      </div>

      <div className="profile-actions">
        <button className="btn btn-primary">Сохранить</button>
        <button className="btn btn-danger" onClick={logout}>
          Выйти
        </button>
      </div>
    </div>
  );
}

export default ProfilePage;