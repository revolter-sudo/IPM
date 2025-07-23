# Flutter Token Refresh Integration Guide

## Overview

This guide shows how to integrate the token refresh system into your Flutter app using Dio (recommended) or http package.

## 1. Dependencies

Add these to your `pubspec.yaml`:

```yaml
dependencies:
  dio: ^5.3.2
  flutter_secure_storage: ^9.0.0
  # OR use shared_preferences for non-sensitive data
  shared_preferences: ^2.2.2
```

## 2. Token Storage Service

```dart
// lib/services/token_storage_service.dart
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class TokenStorageService {
  static const _storage = FlutterSecureStorage();
  
  static const String _accessTokenKey = 'access_token';
  static const String _refreshTokenKey = 'refresh_token';
  
  // Store tokens after login
  static Future<void> storeTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await Future.wait([
      _storage.write(key: _accessTokenKey, value: accessToken),
      _storage.write(key: _refreshTokenKey, value: refreshToken),
    ]);
  }
  
  // Get access token
  static Future<String?> getAccessToken() async {
    return await _storage.read(key: _accessTokenKey);
  }
  
  // Get refresh token
  static Future<String?> getRefreshToken() async {
    return await _storage.read(key: _refreshTokenKey);
  }
  
  // Update only access token (after refresh)
  static Future<void> updateAccessToken(String accessToken) async {
    await _storage.write(key: _accessTokenKey, value: accessToken);
  }
  
  // Clear all tokens (on logout)
  static Future<void> clearTokens() async {
    await Future.wait([
      _storage.delete(key: _accessTokenKey),
      _storage.delete(key: _refreshTokenKey),
    ]);
  }
  
  // Check if user is logged in
  static Future<bool> hasValidTokens() async {
    final accessToken = await getAccessToken();
    final refreshToken = await getRefreshToken();
    return accessToken != null && refreshToken != null;
  }
}
```

## 3. API Service with Dio (Recommended)

```dart
// lib/services/api_service.dart
import 'package:dio/dio.dart';
import 'token_storage_service.dart';

class ApiService {
  static const String baseUrl = 'http://your-server.com'; // Replace with your URL
  late Dio _dio;
  
  ApiService() {
    _dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 30),
      headers: {
        'Content-Type': 'application/json',
      },
    ));
    
    _setupInterceptors();
  }
  
  void _setupInterceptors() {
    // Request interceptor - Add access token to requests
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final accessToken = await TokenStorageService.getAccessToken();
          if (accessToken != null) {
            options.headers['Authorization'] = 'Bearer $accessToken';
          }
          handler.next(options);
        },
        
        onError: (error, handler) async {
          // Handle 401 errors (token expired)
          if (error.response?.statusCode == 401) {
            final refreshed = await _refreshToken();
            
            if (refreshed) {
              // Retry the original request with new token
              final accessToken = await TokenStorageService.getAccessToken();
              error.requestOptions.headers['Authorization'] = 'Bearer $accessToken';
              
              try {
                final response = await _dio.fetch(error.requestOptions);
                handler.resolve(response);
                return;
              } catch (e) {
                // If retry fails, continue with original error
              }
            } else {
              // Refresh failed, redirect to login
              await _handleLogout();
            }
          }
          
          handler.next(error);
        },
      ),
    );
  }
  
  // Refresh access token
  Future<bool> _refreshToken() async {
    try {
      final refreshToken = await TokenStorageService.getRefreshToken();
      if (refreshToken == null) return false;
      
      final response = await Dio().post(
        '$baseUrl/auth/refresh',
        data: {'refresh_token': refreshToken},
      );
      
      if (response.statusCode == 200) {
        final data = response.data;
        if (data['status_code'] == 200) {
          final newAccessToken = data['data']['access_token'];
          await TokenStorageService.updateAccessToken(newAccessToken);
          print('✅ Token refreshed successfully');
          return true;
        }
      }
      
      return false;
    } catch (e) {
      print('❌ Token refresh failed: $e');
      return false;
    }
  }
  
  // Handle logout (clear tokens and redirect)
  Future<void> _handleLogout() async {
    await TokenStorageService.clearTokens();
    // Navigate to login screen
    // You might want to use a navigation service or state management
    print('🔓 Session expired, please login again');
  }
  
  // Login method
  Future<Map<String, dynamic>?> login({
    required int phone,
    required String password,
    required String deviceId,
    String? fcmToken,
  }) async {
    try {
      final response = await _dio.post('/auth/login', data: {
        'phone': phone,
        'password': password,
        'device_id': deviceId,
        if (fcmToken != null) 'fcm_token': fcmToken,
      });
      
      if (response.statusCode == 201) {
        final data = response.data;
        if (data['status_code'] == 201) {
          // Store tokens
          await TokenStorageService.storeTokens(
            accessToken: data['data']['access_token'],
            refreshToken: data['data']['refresh_token'],
          );
          
          return data['data'];
        }
      }
      
      return null;
    } catch (e) {
      print('❌ Login failed: $e');
      return null;
    }
  }
  
  // Logout method
  Future<bool> logout({
    required String userId,
    required String deviceId,
  }) async {
    try {
      await _dio.post('/auth/logout', data: {
        'user_id': userId,
        'device_id': deviceId,
      });
      
      await TokenStorageService.clearTokens();
      return true;
    } catch (e) {
      print('❌ Logout failed: $e');
      await TokenStorageService.clearTokens(); // Clear tokens anyway
      return false;
    }
  }
  
  // Example API call
  Future<List<dynamic>?> getUsers() async {
    try {
      final response = await _dio.get('/auth/users');
      if (response.statusCode == 200) {
        return response.data['data'];
      }
      return null;
    } catch (e) {
      print('❌ Get users failed: $e');
      return null;
    }
  }
  
  // Example protected API call
  Future<Map<String, dynamic>?> createPayment(Map<String, dynamic> paymentData) async {
    try {
      final response = await _dio.post('/payments/create', data: paymentData);
      if (response.statusCode == 201) {
        return response.data;
      }
      return null;
    } catch (e) {
      print('❌ Create payment failed: $e');
      return null;
    }
  }
}
```

## 4. Usage in Flutter Widgets

```dart
// lib/screens/login_screen.dart
import 'package:flutter/material.dart';
import '../services/api_service.dart';

class LoginScreen extends StatefulWidget {
  @override
  _LoginScreenState createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _apiService = ApiService();
  final _phoneController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;
  
  Future<void> _login() async {
    if (_isLoading) return;
    
    setState(() => _isLoading = true);
    
    try {
      final result = await _apiService.login(
        phone: int.parse(_phoneController.text),
        password: _passwordController.text,
        deviceId: 'flutter_device_${DateTime.now().millisecondsSinceEpoch}',
      );
      
      if (result != null) {
        // Login successful, navigate to home
        Navigator.pushReplacementNamed(context, '/home');
      } else {
        // Show error
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Login failed. Please check credentials.')),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Login error: $e')),
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Login')),
      body: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          children: [
            TextField(
              controller: _phoneController,
              decoration: InputDecoration(labelText: 'Phone Number'),
              keyboardType: TextInputType.phone,
            ),
            TextField(
              controller: _passwordController,
              decoration: InputDecoration(labelText: 'Password'),
              obscureText: true,
            ),
            SizedBox(height: 20),
            ElevatedButton(
              onPressed: _isLoading ? null : _login,
              child: _isLoading 
                ? CircularProgressIndicator() 
                : Text('Login'),
            ),
          ],
        ),
      ),
    );
  }
}
```

## 5. App Initialization

```dart
// lib/main.dart
import 'package:flutter/material.dart';
import 'services/token_storage_service.dart';
import 'screens/login_screen.dart';
import 'screens/home_screen.dart';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'IPM App',
      home: SplashScreen(),
      routes: {
        '/login': (context) => LoginScreen(),
        '/home': (context) => HomeScreen(),
      },
    );
  }
}

class SplashScreen extends StatefulWidget {
  @override
  _SplashScreenState createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _checkAuthStatus();
  }
  
  Future<void> _checkAuthStatus() async {
    // Add a small delay for splash effect
    await Future.delayed(Duration(seconds: 2));
    
    final hasTokens = await TokenStorageService.hasValidTokens();
    
    if (hasTokens) {
      Navigator.pushReplacementNamed(context, '/home');
    } else {
      Navigator.pushReplacementNamed(context, '/login');
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            FlutterLogo(size: 100),
            SizedBox(height: 20),
            CircularProgressIndicator(),
            SizedBox(height: 20),
            Text('Loading...'),
          ],
        ),
      ),
    );
  }
}
```
