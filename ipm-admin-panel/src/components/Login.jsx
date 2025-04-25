import React, { useState } from 'react';
import { login } from '../services/api';

const Login = ({ onLoginSuccess }) => {
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const data = await login(phone, password);
      if (!data || !data.data) {
        setError('Login failed: Invalid response from server.');
        return;
      }
      // Save token and user data to localStorage or context
      localStorage.setItem('token', data.data.access_token);
      localStorage.setItem('user', JSON.stringify(data.data.user_data));
      onLoginSuccess();
      // Redirect to admin dashboard after successful login
      window.location.href = '/admin-dashboard';
    } catch (err) {
      // Check for backend error message "Only admin can access"
      if (err.response && err.response.data && err.response.data.message === "Only admin can access") {
        setError('Only superadmin and admin users can login.');
      } else if (err.message.includes('Access denied')) {
        setError('Only superadmin and admin users can login.');
      } else {
        setError(err.message);
      }
    }
  };

  return (
    <div className="login-container">
      <h2>Login</h2>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <form onSubmit={handleSubmit}>
        <div>
          <label>Phone:</label>
          <input
            type="text"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            required
            placeholder="Enter phone number"
          />
        </div>
        <div>
          <label>Password:</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            placeholder="Enter password"
          />
        </div>
        <button type="submit">Login</button>
      </form>
    </div>
  );
};

export default Login;
