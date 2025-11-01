import { Routes, Route, Navigate } from 'react-router-dom';
import { ProtectedRoute } from './ProtectedRoute';
import { Login } from '../pages/Login';
import { Register } from '../pages/Register';
import { Dashboard } from '../pages/Dashboard';
import { useAuth } from '../hooks/useAuth';

// --- MAKE SURE 'export' IS HERE ---
export const AppRoutes = () => {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* This is the Free Trial route.
        The Dashboard page itself will handle what to show.
      */}
      <Route path="/dashboard" element={<Dashboard />} />
      
      {/* This is a placeholder for a true protected route. 
        If you want /dashboard to be *only* for logged-in users,
        you would wrap it like this:
      */}
      {/*
      <Route element={<ProtectedRoute />}>
         <Route path="/dashboard" element={<Dashboard />} />
      </Route>
      */}

      {/* Redirect root URL ('/') to the correct page */}
      <Route 
        path="/" 
        element={<Navigate to={isAuthenticated ? "/dashboard" : "/login"} replace />} 
      />
    </Routes>
  );
};