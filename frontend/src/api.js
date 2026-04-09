export const API_URL = "http://127.0.0.1:8000";

function formatError(data) {
  if (!data) return "Ошибка запроса";

  if (typeof data.detail === "string") {
    return data.detail;
  }

  if (Array.isArray(data.detail)) {
    return data.detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item?.msg) {
          const field = Array.isArray(item.loc) ? item.loc.slice(1).join(".") : "";
          return field ? `${field}: ${item.msg}` : item.msg;
        }
        return JSON.stringify(item);
      })
      .join("; ");
  }

  if (typeof data.detail === "object") {
    return JSON.stringify(data.detail);
  }

  return "Ошибка запроса";
}

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, options);

  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    throw new Error(formatError(data));
  }

  return data;
}

export function getDishes() {
  return request("/dishes");
}

export function getRecommendations(token) {
  return request("/recommendations", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export function getDishById(id) {
  return request(`/dishes/${id}`);
}

export function getCurrentUser(token) {
  return request("/me", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export function updatePreferences(payload, token) {
  return request("/me/preferences", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export function createOrder(items, token) {
  return request("/orders", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ items }),
  });
}

export function getOrders(token) {
  return request("/orders", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export function getMyOrders(token) {
  return request("/my-orders", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export function createDish(dish, token) {
  return request("/dishes", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(dish),
  });
}

export function updateDish(id, dish, token) {
  return request(`/dishes/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(dish),
  });
}

export function deleteDish(id, token) {
  return request(`/dishes/${id}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function uploadDishImage(file, token) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_URL}/upload-image`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });

  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    throw new Error(formatError(data));
  }

  return data;
}

const CART_KEY = "smartcanteen_cart";

export function getCart() {
  const saved = localStorage.getItem(CART_KEY);
  return saved ? JSON.parse(saved) : [];
}

export function saveCart(items) {
  localStorage.setItem(CART_KEY, JSON.stringify(items));
}

export function addToCart(dish) {
  const cart = getCart();
  const existing = cart.find((item) => item.id === dish.id);

  if (existing) {
    existing.quantity += 1;
  } else {
    cart.push({ ...dish, quantity: 1 });
  }

  saveCart(cart);
}

export function removeFromCart(id) {
  const cart = getCart().filter((item) => item.id !== id);
  saveCart(cart);
}

export function changeCartQuantity(id, quantity) {
  const cart = getCart()
    .map((item) => (item.id === id ? { ...item, quantity } : item))
    .filter((item) => item.quantity > 0);

  saveCart(cart);
}

export function clearCart() {
  localStorage.removeItem(CART_KEY);
}