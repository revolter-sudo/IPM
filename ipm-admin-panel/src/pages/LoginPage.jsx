import React from 'react';
import { useNavigate } from 'react-router-dom';
import Login from '../components/Login';

const LoginPage = () => {
  const navigate = useNavigate();

  const handleLoginSuccess = () => {
    // Redirect to admin dashboard or home page after login
    navigate('/admin-dashboard');
  };

  return (
    <div>
      <Login onLoginSuccess={handleLoginSuccess} />
    </div>
  );
};

export default LoginPage;
