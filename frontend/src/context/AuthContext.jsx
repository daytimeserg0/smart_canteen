import { createContext, useContext, useEffect, useState } from "react";
import { API_URL } from "../api";

const AuthContext = createContext(null);

function formatApiError(data, fallbackMessage) {
  if (!data) {
    return fallbackMessage;
  }

  if (typeof data.detail === "string") {
    return data.detail;
  }

  if (Array.isArray(data.detail)) {
    return data.detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }

        if (item?.msg) {
          const field = Array.isArray(item.loc)
            ? item.loc.slice(1).join(".")
            : "";

          return field ? `${field}: ${item.msg}` : item.msg;
        }

        return JSON.stringify(item);
      })
      .join("; ");
  }

  if (typeof data.detail === "object" && data.detail !== null) {
    return JSON.stringify(data.detail);
  }

  return fallbackMessage;
}

export function AuthProvider({ children }) {
  const [authData, setAuthData] = useState(() => {
    const saved = localStorage.getItem("smartcanteen_auth");
    return saved ? JSON.parse(saved) : null;
  });

  useEffect(() => {
    if (authData) {
      localStorage.setItem("smartcanteen_auth", JSON.stringify(authData));
    } else {
      localStorage.removeItem("smartcanteen_auth");
    }
  }, [authData]);

  const login = async ({ username, password }) => {
    const response = await fetch(`${API_URL}/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, password }),
    });

    let data = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (!response.ok) {
      throw new Error(formatApiError(data, "Ошибка входа"));
    }

    setAuthData(data);
    return data;
  };

  const register = async ({ username, email, password }) => {
    const response = await fetch(`${API_URL}/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, email, password }),
    });

    let data = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (!response.ok) {
      throw new Error(formatApiError(data, "Ошибка регистрации"));
    }

    setAuthData(data);
    return data;
  };

  const logout = () => {
    setAuthData(null);
  };

  return (
    <AuthContext.Provider
      value={{
        authData,
        user: authData
          ? {
              username: authData.username,
              email: authData.email,
              role: authData.role,
            }
          : null,
        token: authData?.access_token || null,
        isAuthenticated: Boolean(authData?.access_token),
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}