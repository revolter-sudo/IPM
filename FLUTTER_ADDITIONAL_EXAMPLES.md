# Flutter Token Refresh - Additional Examples

## Alternative: Using HTTP Package

If you prefer the `http` package instead of Dio:

```dart
// lib/services/http_api_service.dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'token_storage_service.dart';

class HttpApiService {
  static const String baseUrl = 'http://your-server.com';
  
  // Helper method to make authenticated requests
  Future<http.Response?> _makeAuthenticatedRequest(
    Future<http.Response> Function(Map<String, String> headers) request,
  ) async {
    String? accessToken = await TokenStorageService.getAccessToken();
    
    Map<String, String> headers = {
      'Content-Type': 'application/json',
      if (accessToken != null) 'Authorization': 'Bearer $accessToken',
    };
    
    http.Response response = await request(headers);
    
    // If token expired, try to refresh
    if (response.statusCode == 401) {
      final refreshed = await _refreshToken();
      if (refreshed) {
        // Retry with new token
        accessToken = await TokenStorageService.getAccessToken();
        headers['Authorization'] = 'Bearer $accessToken!';
        response = await request(headers);
      } else {
        // Refresh failed, handle logout
        await _handleLogout();
      }
    }
    
    return response;
  }
  
  Future<bool> _refreshToken() async {
    try {
      final refreshToken = await TokenStorageService.getRefreshToken();
      if (refreshToken == null) return false;
      
      final response = await http.post(
        Uri.parse('$baseUrl/auth/refresh'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'refresh_token': refreshToken}),
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['status_code'] == 200) {
          await TokenStorageService.updateAccessToken(data['data']['access_token']);
          return true;
        }
      }
      return false;
    } catch (e) {
      print('Token refresh failed: $e');
      return false;
    }
  }
  
  Future<void> _handleLogout() async {
    await TokenStorageService.clearTokens();
    // Handle navigation to login
  }
}
```

## State Management with Provider

```dart
// lib/providers/auth_provider.dart
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/token_storage_service.dart';

class AuthProvider with ChangeNotifier {
  final ApiService _apiService = ApiService();
  bool _isAuthenticated = false;
  Map<String, dynamic>? _userData;
  
  bool get isAuthenticated => _isAuthenticated;
  Map<String, dynamic>? get userData => _userData;
  
  Future<void> checkAuthStatus() async {
    _isAuthenticated = await TokenStorageService.hasValidTokens();
    notifyListeners();
  }
  
  Future<bool> login({
    required int phone,
    required String password,
    required String deviceId,
    String? fcmToken,
  }) async {
    final result = await _apiService.login(
      phone: phone,
      password: password,
      deviceId: deviceId,
      fcmToken: fcmToken,
    );
    
    if (result != null) {
      _isAuthenticated = true;
      _userData = result['user_data'];
      notifyListeners();
      return true;
    }
    
    return false;
  }
  
  Future<void> logout() async {
    if (_userData != null) {
      await _apiService.logout(
        userId: _userData!['uuid'],
        deviceId: 'current_device',
      );
    }
    
    _isAuthenticated = false;
    _userData = null;
    notifyListeners();
  }
}
```

## Usage with Provider

```dart
// lib/main.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'providers/auth_provider.dart';

void main() {
  runApp(
    ChangeNotifierProvider(
      create: (context) => AuthProvider(),
      child: MyApp(),
    ),
  );
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: Consumer<AuthProvider>(
        builder: (context, authProvider, child) {
          if (authProvider.isAuthenticated) {
            return HomeScreen();
          } else {
            return LoginScreen();
          }
        },
      ),
    );
  }
}
```

## Error Handling Widget

```dart
// lib/widgets/api_error_handler.dart
import 'package:flutter/material.dart';

class ApiErrorHandler {
  static void showError(BuildContext context, String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
        action: SnackBarAction(
          label: 'Dismiss',
          onPressed: () {
            ScaffoldMessenger.of(context).hideCurrentSnackBar();
          },
        ),
      ),
    );
  }
  
  static void showSuccess(BuildContext context, String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.green,
      ),
    );
  }
}
```

## Testing

```dart
// test/token_refresh_test.dart
import 'package:flutter_test/flutter_test.dart';
import '../lib/services/api_service.dart';

void main() {
  group('Token Refresh Tests', () {
    late ApiService apiService;
    
    setUp(() {
      apiService = ApiService();
    });
    
    test('should login and store tokens', () async {
      final result = await apiService.login(
        phone: 1234567890,
        password: 'supersecurepassword',
        deviceId: 'test_device',
      );
      
      expect(result, isNotNull);
      expect(result!['access_token'], isNotNull);
      expect(result['refresh_token'], isNotNull);
    });
  });
}
```

## Key Benefits

✅ **Automatic Token Refresh**: No manual intervention needed
✅ **Seamless UX**: Users never see login screens due to expired tokens  
✅ **Secure Storage**: Tokens stored in secure storage
✅ **Error Handling**: Proper handling of network errors and token issues
✅ **Easy Integration**: Drop-in solution with interceptors
✅ **State Management Ready**: Works with Provider, Bloc, Riverpod, etc.

## Quick Setup Checklist

1. ✅ Add dependencies (`dio`, `flutter_secure_storage`)
2. ✅ Create `TokenStorageService` for secure token storage
3. ✅ Create `ApiService` with Dio interceptors
4. ✅ Implement automatic token refresh logic
5. ✅ Handle 401 errors with retry mechanism
6. ✅ Add proper error handling and user feedback
7. ✅ Test the implementation

This provides a robust, production-ready token refresh system for Flutter apps! 🚀
