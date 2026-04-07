const CART_KEY = "smartcanteen_cart";

export function getCart() {
  const raw = localStorage.getItem(CART_KEY);
  if (!raw) return [];

  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveCart(cart) {
  localStorage.setItem(CART_KEY, JSON.stringify(cart));
}

export function addToCart(dish) {
  const cart = getCart();
  const existing = cart.find((item) => item.id === dish.id);

  if (existing) {
    existing.quantity += 1;
  } else {
    cart.push({
      ...dish,
      quantity: 1,
    });
  }

  saveCart(cart);
  return cart;
}

export function removeFromCart(dishId) {
  const cart = getCart().filter((item) => item.id !== dishId);
  saveCart(cart);
  return cart;
}

export function changeCartQuantity(dishId, quantity) {
  const cart = getCart()
    .map((item) =>
      item.id === dishId ? { ...item, quantity: Math.max(1, quantity) } : item
    );

  saveCart(cart);
  return cart;
}

export function clearCart() {
  localStorage.removeItem(CART_KEY);
}