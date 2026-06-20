import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  static const String _defaultIp = "192.168.1.100:8000";

  static Future<String> getBaseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    final ip = prefs.getString('server_ip') ?? _defaultIp;
    return "http://$ip";
  }

  static Future<Map<String, dynamic>> getState() async {
    final baseUrl = await getBaseUrl();
    try {
      final response = await http.get(Uri.parse("$baseUrl/mobile/state")).timeout(const Duration(seconds: 3));
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (e) {
      print("Error fetching state: $e");
    }
    return {};
  }

  static Future<bool> sendAction(String action, [Map<String, dynamic>? payload]) async {
    final baseUrl = await getBaseUrl();
    try {
      final response = await http.post(
        Uri.parse("$baseUrl/operator/action"),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({"action": action, if (payload != null) "payload": payload}),
      ).timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (e) {
      print("Error sending action: $e");
    }
    return false;
  }

  static Future<Map<String, dynamic>> checkHealth() async {
    final baseUrl = await getBaseUrl();
    final stopwatch = Stopwatch()..start();
    try {
      final response = await http.get(Uri.parse("$baseUrl/health")).timeout(const Duration(seconds: 2));
      stopwatch.stop();
      if (response.statusCode == 200) {
        return {"status": "ok", "latency": stopwatch.elapsedMilliseconds};
      }
    } catch (e) {
      stopwatch.stop();
    }
    return {"status": "error", "latency": -1};
  }
}
