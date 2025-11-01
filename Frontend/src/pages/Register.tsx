import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import apiClient from '../api/apiClient';
// We don't need useAuth here, as registration redirects to login
// import { useAuth } from '../hooks/useAuth';

type RegisterStep = 'form' | 'otp';

export const Register = () => {
  const [step, setStep] = useState<RegisterStep>('form');
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [otp, setOtp] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  
  const navigate = useNavigate();
  // const { login } = useAuth(); // Not needed here

  // Step 1: Call /register/initiate
  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);

    // --- THIS IS THE FIX ---
    // Add validation for password length
    if (password.length > 72) {
      setError("Password must be 72 characters or less.");
      return; // Stop the submission
    }
    // --- END OF FIX ---

    setIsLoading(true);

    try {
      await apiClient.post('/auth/register/initiate', { 
        name, 
        email, 
        password,
        user_type: "community"
      });
      
      setIsLoading(false);
      setStep('otp'); // Move to OTP step
      setSuccessMessage(`OTP sent to ${email}. Please check your inbox.`);

    } catch (err: any) {
      setIsLoading(false);
      setError(err.response?.data?.detail || 'Registration failed');
    }
  };

  // Step 2: Call /register/verify
  const handleOtpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await apiClient.post('/auth/register/verify', { 
        email, 
        otp_code: otp
      });

      setIsLoading(false);
      setSuccessMessage("Registration successful! Please log in.");
      
      setTimeout(() => {
        navigate('/login');
      }, 2000);

    } catch (err: any) {
      setIsLoading(false);
      setError(err.response?.data?.detail || 'Invalid OTP');
    }
  };

  // --- STYLING (no changes) ---
  const inputStyle = "w-full p-2 bg-white/80 rounded border border-border-light text-text-dark focus:ring-primary focus:border-primary";
  const labelStyle = "block mb-1 text-sm font-medium text-text-light";

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-light-bg">
      <div className="p-8 rounded-xl shadow-2xl w-96 frosted-glass">
        
        {step === 'form' && (
          <form onSubmit={handleRegisterSubmit} className="space-y-4">
            <h1 className="text-3xl font-bold text-center mb-6 text-text-dark">Register</h1>
            <div>
              <label className={labelStyle}>Email</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className={inputStyle} required />
            </div>
            <div>
              <label className={labelStyle}>Full Name</label>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)} className={inputStyle} required />
            </div>
            <div>
              <label className={labelStyle}>Password</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className={inputStyle} required />
            </div>
            <button type="submit" className="w-full p-2 font-bold text-white bg-primary rounded-lg hover:bg-primary/80" disabled={isLoading}>
              {isLoading ? 'Sending...' : 'Register'}
            </button>
          </form>
        )}

        {step === 'otp' && (
          <form onSubmit={handleOtpSubmit} className="space-y-4">
            <h1 className="text-3xl font-bold text-center mb-4 text-text-dark">Verify OTP</h1>
            {/* --- THIS IS THE FIX --- */}
            <p className="text-center text-sm text-text-light mb-4">
              An OTP has been sent to {email}.
            </p>
            {/* --- END OF FIX --- */}
            <div>
              <label className={labelStyle}>Enter OTP</label>
              <input type="text" value={otp} onChange={(e) => setOtp(e.target.value)} className={inputStyle} required />
            </div>
            <button type="submit" className="w-full p-2 font-bold text-white bg-primary rounded-lg hover:bg-primary/80" disabled={isLoading}>
              {isLoading ? 'Verifying...' : 'Verify & Create Account'}
            </button>
          </form>
        )}

        {error && <p className="mt-4 text-center text-red-500">{error}</p>}
        {successMessage && <p className="mt-4 text-center text-green-600">{successMessage}</p>}
        
        <div className="mt-6 text-center text-sm">
          <p className="text-text-light">
            Already have an account?{' '}
            <Link to="/login" className="font-medium text-primary hover:underline">
              Login here
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};