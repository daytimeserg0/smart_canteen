import { useEffect, useState } from "react";
import {
  changeCartQuantity,
  clearCart,
  createOrder,
  getCart,
  removeFromCart,
} from "../api";
import { useAuth } from "../context/AuthContext";

function CartPage() {
  const { isAuthenticated, token } = useAuth();
  const [cartItems, setCartItems] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setCartItems(getCart());
  }, []);

  const refreshCart = () => {
    setCartItems(getCart());
  };

  const totalPrice = cartItems.reduce(
    (sum, item) => sum + item.price * (item.quantity || 1),
    0
  );

  const handleRemove = (id) => {
    removeFromCart(id);
    refreshCart();
  };

  const handleQuantityChange = (id, value) => {
    const quantity = Number(value);
    if (Number.isNaN(quantity) || quantity < 1) return;

    changeCartQuantity(id, quantity);
    refreshCart();
  };

  const handleCheckout = async () => {
    if (!isAuthenticated) {
      setError("Для оформления заказа нужно войти в аккаунт.");
      return;
    }

    if (cartItems.length === 0) {
      setError("Корзина пуста.");
      return;
    }

    try {
      setLoading(true);
      setError("");
      setMessage("");

      const items = cartItems.map((item) => ({
        dish_id: item.id,
        quantity: item.quantity || 1,
      }));

      await createOrder(items, token);

      clearCart();
      setCartItems([]);
      setMessage("Заказ успешно оформлен.");
    } catch (err) {
      setError(err.message || "Не удалось оформить заказ");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="cart-page">
      <div className="page-card">
        <h1 className="section-title">Ваш заказ</h1>
        <p className="section-subtitle">
          Здесь отображаются выбранные блюда и общая стоимость заказа.
        </p>

        {cartItems.length === 0 ? (
          <p>Корзина пуста.</p>
        ) : (
          <div className="cart-list">
            {cartItems.map((item) => (
              <div key={item.id} className="cart-item">
                <span className="cart-item-name">{item.name}</span>
                <span className="cart-item-price">
                  {item.price} ₽ × {item.quantity || 1}
                </span>

                <input
                  type="number"
                  min="1"
                  value={item.quantity || 1}
                  onChange={(e) => handleQuantityChange(item.id, e.target.value)}
                  style={{ width: "70px" }}
                />

                <button
                  className="btn btn-danger"
                  onClick={() => handleRemove(item.id)}
                >
                  Удалить
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="cart-total">
        <h2>Итого: {totalPrice} ₽</h2>
        <button
          className="btn btn-primary"
          onClick={handleCheckout}
          disabled={loading}
        >
          {loading ? "Оформление..." : "Оформить заказ"}
        </button>

        {message && <p style={{ color: "green", marginTop: "12px" }}>{message}</p>}
        {error && <p style={{ color: "red", marginTop: "12px" }}>{error}</p>}
      </div>
    </div>
  );
}

export default CartPage;