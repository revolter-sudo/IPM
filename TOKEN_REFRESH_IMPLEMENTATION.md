# Token Refresh Implementation Guide

## Problem Solved

Your mobile app was forcing users to re-login every time their access token expired (1 minute in DEV environment). This created a terrible user experience.

## What Was Fixed

### 1. **Fixed Login Endpoint**
- **Before**: Login endpoint required authentication (circular dependency)
- **After**: Login endpoint no longer requires authentication
- **Impact**: Users can now actually login to get tokens

### 2. **Added Refresh Token System**
- **Access Tokens**: Short-lived (1 minute in DEV, 15 minutes in PROD)
- **Refresh Tokens**: Long-lived (10x access token time, minimum 7 days)
- **Purpose**: Mobile apps can renew expired access tokens without re-login

### 3. **New API Endpoints**

#### Login Response (Updated)
```json
POST /auth/login
{
  "phone": 1234567890,
  "password": "password",
  "device_id": "device123",
  "fcm_token": "optional"
}

Response:
{
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer",
    "user_data": { ... }
  },
  "message": "User logged in successfully",
  "status_code": 201
}
```

#### New Refresh Endpoint
```json
POST /auth/refresh
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}

Response:
{
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer"
  },
  "message": "Token refreshed successfully",
  "status_code": 200
}
```

## Mobile App Implementation

### 1. **Store Both Tokens**
```javascript
// After successful login
const loginResponse = await login(credentials);
const { access_token, refresh_token } = loginResponse.data;

// Store both tokens securely
await SecureStore.setItemAsync('access_token', access_token);
await SecureStore.setItemAsync('refresh_token', refresh_token);
```

### 2. **API Call with Auto-Refresh**
```javascript
async function apiCall(endpoint, options = {}) {
  let accessToken = await SecureStore.getItemAsync('access_token');
  
  // Try API call with current access token
  let response = await fetch(endpoint, {
    ...options,
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      ...options.headers
    }
  });
  
  // If token expired, refresh and retry
  if (response.status === 401) {
    const newAccessToken = await refreshAccessToken();
    if (newAccessToken) {
      // Retry with new token
      response = await fetch(endpoint, {
        ...options,
        headers: {
          'Authorization': `Bearer ${newAccessToken}`,
          ...options.headers
        }
      });
    } else {
      // Refresh failed, redirect to login
      redirectToLogin();
      return;
    }
  }
  
  return response;
}

async function refreshAccessToken() {
  try {
    const refreshToken = await SecureStore.getItemAsync('refresh_token');
    
    const response = await fetch('/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken })
    });
    
    if (response.status === 200) {
      const data = await response.json();
      const newAccessToken = data.data.access_token;
      
      // Store new access token
      await SecureStore.setItemAsync('access_token', newAccessToken);
      return newAccessToken;
    } else {
      // Refresh token expired, need to login again
      return null;
    }
  } catch (error) {
    console.error('Token refresh failed:', error);
    return null;
  }
}
```

### 3. **Axios Interceptor Example**
```javascript
import axios from 'axios';

// Request interceptor to add token
axios.interceptors.request.use(async (config) => {
  const token = await SecureStore.getItemAsync('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor to handle token refresh
axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      const newToken = await refreshAccessToken();
      if (newToken) {
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return axios(originalRequest);
      } else {
        // Redirect to login
        redirectToLogin();
      }
    }
    
    return Promise.reject(error);
  }
);
```

## Testing

Run the test script to verify everything works:

```bash
python test_token_refresh.py
```

This will test:
1. Login to get tokens
2. Access token works for protected endpoints
3. Refresh token can generate new access token
4. New access token works
5. Invalid refresh tokens are rejected

## Environment Configuration

- **LOCAL**: Tokens never expire (for development)
- **DEV**: Access tokens expire in 1 minute, refresh tokens in 10 minutes
- **PROD**: Access tokens expire in 15 minutes, refresh tokens in 7+ days

## Security Features

1. **Token Blacklisting**: Tokens are blacklisted on logout
2. **JTI Tracking**: Each token has unique identifier
3. **IP Binding**: Optional IP validation (configurable)
4. **Token Type Validation**: Refresh tokens can't be used as access tokens

## Benefits

✅ **No More Forced Re-logins**: Users stay logged in even with short token expiry
✅ **Better Security**: Short-lived access tokens with long-lived refresh tokens
✅ **Seamless UX**: Token refresh happens automatically in background
✅ **Proper Error Handling**: Clear distinction between expired and invalid tokens
