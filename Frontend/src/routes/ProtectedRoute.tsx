import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export const ProtectedRoute = () => {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    // User is not authenticated, redirect to login
    return <Navigate to="/login" replace />;
  }

  // User is authenticated, render the child component (e.g., Dashboard)
  return <Outlet />;
};