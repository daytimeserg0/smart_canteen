export const DISH_CATEGORIES = [
  { value: "all", label: "Все категории" },
  { value: "breakfast", label: "Завтраки" },
  { value: "soup", label: "Супы" },
  { value: "main", label: "Основные блюда" },
  { value: "salad", label: "Салаты" },
  { value: "dessert", label: "Десерты" },
  { value: "drink", label: "Напитки" },
  { value: "snack", label: "Закуски" },
];

export const ADMIN_DISH_CATEGORIES = DISH_CATEGORIES.filter(
  (item) => item.value !== "all"
);

export const CATEGORY_LABELS = DISH_CATEGORIES.reduce((acc, item) => {
  acc[item.value] = item.label;
  return acc;
}, {});