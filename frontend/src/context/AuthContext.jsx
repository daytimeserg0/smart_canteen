import { createContext, useContext, useEffect, useState } from "react";
import { API_URL } from "../api";

const AuthContext = createContext(null);

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

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Ошибка входа");
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

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Ошибка регистрации");
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