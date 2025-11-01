import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import apiClient from '../api/apiClient';

export const Login = () => {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      // 1. Your backend expects email and password, which is correct
      const { data } = await apiClient.post('/auth/signin', { email, password });
      
      // 2. Your backend returns 'access_token', not 'token'
      // 3. Your backend returns 'user' object directly
      login(data.user, data.access_token); // This now matches
      
      setIsLoading(false);
      navigate('/dashboard'); 

    } catch (err: any) {
      setIsLoading(false);
      setError(err.response?.data?.detail || 'Invalid email or password');
    }
  };
  
  // --- STYLING (no changes) ---
  const inputStyle = "w-full p-2 bg-white/80 rounded border border-border-light text-text-dark focus:ring-primary focus:border-primary";
  const labelStyle = "block mb-1 text-sm font-medium text-text-light";

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-light-bg">
      <div className="p-8 rounded-xl shadow-2xl w-96 frosted-glass">
        <h1 className="text-3xl font-bold text-center mb-6 text-text-dark">
          QuantumDash Login
        </h1>
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className={labelStyle}>Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className={inputStyle} required />
          </div>
          <div>
            <label className={labelStyle}>Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className={inputStyle} required />
          </div>

          {error && <p className="text-center text-red-500 text-sm">{error}</p>}

          <button type="submit" className="w-full p-2 font-bold text-white bg-primary rounded-lg hover:bg-primary/80" disabled={isLoading}>
            {isLoading ? 'Logging in...' : 'Login'}
          </button>
        </form>
        
        <div className="mt-6 text-center text-sm">
          <p className="text-text-light">
            New user?{' '}
            <Link to="/register" className="font-medium text-primary hover:underline">
              Register here
            </Link>
          </p>
          <p className="mt-2 text-text-light">
            Or{' '}
            <Link to="/dashboard" className="font-medium text-primary hover:underline">
              Continue with Free Trial
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};