import { cartItems } from "../data/cart";

function CartPage() {
  const totalPrice = cartItems.reduce((sum, item) => sum + item.price, 0);

  return (
    <div className="cart-page">
      <div className="page-card">
        <h1 className="section-title">Ваш заказ</h1>
        <p className="section-subtitle">
          Здесь отображаются выбранные блюда и общая стоимость заказа.
        </p>

        <div className="cart-list">
          {cartItems.map((item) => (
            <div key={item.id} className="cart-item">
              <span className="cart-item-name">{item.name}</span>
              <span className="cart-item-price">{item.price} ₽</span>
            </div>
          ))}
        </div>
      </div>

      <div className="cart-total">
        <h2>Итого: {totalPrice} ₽</h2>
        <button className="btn btn-primary">Оформить заказ</button>
      </div>
    </div>
  );
}

export default CartPage;