import { createContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';

// 1. Updated User interface to match your backend's response
interface User {
  user_id: string;
  email: string;
  name: string;
  user_type: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (userData: User, token: string) => void;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  // 2. Initialize token from localStorage
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'));

  // 3. Effect to check for user data if token exists (on page load)
  //    (This is a placeholder for a /me endpoint, which is a good future addition)
  useEffect(() => {
    const storedToken = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');
    if (storedToken && storedUser) {
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
    }
  }, []);

  const login = (userData: User, token: string) => {
    setUser(userData);
    setToken(token);
    // 4. Save session to localStorage
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(userData));
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    // 5. Clear session from localStorage
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  };

  const isAuthenticated = !!token;

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};