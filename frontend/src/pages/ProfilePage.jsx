import { useEffect, useMemo, useState } from "react";
import { getCurrentUser, updatePreferences } from "../api";
import { useAuth } from "../context/AuthContext";
import { ALLERGY_OPTIONS, DIET_OPTIONS } from "../data/preferences";

function createSelectionState(options, selectedValues = []) {
  const selectedSet = new Set(selectedValues);

  return options.reduce((acc, option) => {
    acc[option.value] = selectedSet.has(option.value);
    return acc;
  }, {});
}

function ProfilePage() {
  const { user, token, logout } = useAuth();
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [preferences, setPreferences] = useState({
    allergies: createSelectionState(ALLERGY_OPTIONS),
    diet: createSelectionState(DIET_OPTIONS),
  });

  useEffect(() => {
    const loadProfile = async () => {
      try {
        setError("");

        const data = await getCurrentUser(token);
        setProfile(data);

        setPreferences({
          allergies: createSelectionState(ALLERGY_OPTIONS, data.allergens || []),
          diet: createSelectionState(DIET_OPTIONS, data.diet_types || []),
        });
      } catch (err) {
        setError(err.message || "Не удалось загрузить профиль");
      }
    };

    if (token) {
      loadProfile();
    }
  }, [token]);

  const selectedAllergiesCount = useMemo(
    () => Object.values(preferences.allergies).filter(Boolean).length,
    [preferences.allergies]
  );

  const selectedDietCount = useMemo(
    () => Object.values(preferences.diet).filter(Boolean).length,
    [preferences.diet]
  );

  const handleCheckboxChange = (group, field) => {
    setPreferences((prev) => ({
      ...prev,
      [group]: {
        ...prev[group],
        [field]: !prev[group][field],
      },
    }));
    setMessage("");
  };

  const handleSave = async () => {
    try {
      setError("");
      setMessage("");

      const allergens = Object.entries(preferences.allergies)
        .filter(([, value]) => value)
        .map(([key]) => key);

      const diet_types = Object.entries(preferences.diet)
        .filter(([, value]) => value)
        .map(([key]) => key);

      const updated = await updatePreferences(
        {
          allergens,
          diet_types,
        },
        token
      );

      setProfile(updated);
      setMessage("Предпочтения успешно сохранены.");
    } catch (err) {
      setError(err.message || "Не удалось сохранить настройки");
    }
  };

  return (
    <div className="profile-page">
      <div className="profile-header">
        <div className="profile-email">{profile?.email || user?.email}</div>
        <p className="profile-muted">
          Вы вошли как <b>{profile?.username || user?.username}</b>. Роль:{" "}
          <b>{profile?.role || user?.role}</b>.
        </p>
        <p className="profile-muted">
          Здесь можно указать пищевые ограничения и предпочтения, чтобы в
          будущем рекомендации блюд были точнее.
        </p>

        {error && <p style={{ color: "red" }}>{error}</p>}
        {message && <p style={{ color: "green" }}>{message}</p>}
      </div>

      <div className="profile-grid">
        <div className="profile-box">
          <h2>Аллергии</h2>
          <p className="profile-muted">
            Выбрано: <b>{selectedAllergiesCount}</b>
          </p>

          {ALLERGY_OPTIONS.map((option) => (
            <label className="checkbox-line" key={option.value}>
              <input
                type="checkbox"
                checked={preferences.allergies[option.value] || false}
                onChange={() =>
                  handleCheckboxChange("allergies", option.value)
                }
              />
              {option.label}
            </label>
          ))}
        </div>

        <div className="profile-box">
          <h2>Диетические предпочтения</h2>
          <p className="profile-muted">
            Выбрано: <b>{selectedDietCount}</b>
          </p>

          {DIET_OPTIONS.map((option) => (
            <label className="checkbox-line" key={option.value}>
              <input
                type="checkbox"
                checked={preferences.diet[option.value] || false}
                onChange={() => handleCheckboxChange("diet", option.value)}
              />
              {option.label}
            </label>
          ))}
        </div>
      </div>

      <div className="profile-actions">
        <button className="btn btn-primary" onClick={handleSave}>
          Сохранить
        </button>
        <button className="btn btn-danger" onClick={logout}>
          Выйти
        </button>
      </div>
    </div>
  );
}

export default ProfilePage;