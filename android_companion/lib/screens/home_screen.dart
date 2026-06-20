import 'dart:async';
import 'package:flutter/material.dart';
import '../api_service.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  Map<String, dynamic> _state = {};
  Map<String, dynamic> _health = {"status": "loading", "latency": 0};
  bool _loading = true;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _fetchData();
    _timer = Timer.periodic(const Duration(seconds: 15), (_) => _fetchData());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _fetchData() async {
    final health = await ApiService.checkHealth();
    final state = await ApiService.getState();
    if (mounted) {
      setState(() {
        _health = health;
        _state = state;
        _loading = false;
      });
    }
  }

  void _sendAction(String action) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Triggering: $action'), duration: const Duration(seconds: 1)));
    ApiService.sendAction(action);
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    final isConnected = _health["status"] == "ok";

    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              _state['greeting'] ?? 'Good Morning Boss',
              style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Color(0xFF7C6AEF)),
            ),
            const SizedBox(height: 24),
            _buildInfoCard("Current Focus", _state['current_focus'] ?? 'Unknown'),
            const SizedBox(height: 12),
            _buildInfoCard("Current Project", _state['current_project'] ?? 'Unknown'),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(child: _buildInfoCard("Workspace", _state['workspace'] ?? 'Jarvis')),
                const SizedBox(width: 12),
                Expanded(child: _buildInfoCard("Pending Tasks", "${_state['pending_count'] ?? 0}")),
              ],
            ),
            const SizedBox(height: 24),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: isConnected ? Colors.green.withOpacity(0.1) : Colors.red.withOpacity(0.1),
                border: Border.all(color: isConnected ? Colors.green.withOpacity(0.5) : Colors.red.withOpacity(0.5)),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  Icon(isConnected ? Icons.circle : Icons.error, color: isConnected ? Colors.green : Colors.red, size: 16),
                  const SizedBox(width: 8),
                  Text(isConnected ? "Connected" : "Disconnected", style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
                  const Spacer(),
                  if (isConnected) Text("Latency: ${_health["latency"]}ms", style: const TextStyle(color: Colors.white70, fontSize: 12)),
                ],
              ),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () => _sendAction("morning_brief"),
              icon: const Icon(Icons.wb_sunny),
              label: const Text("Trigger Morning Brief"),
              style: ElevatedButton.styleFrom(padding: const EdgeInsets.all(16)),
            ),
            const SizedBox(height: 12),
            ElevatedButton.icon(
              onPressed: () => _sendAction("resume_session"),
              icon: const Icon(Icons.play_arrow),
              label: const Text("Trigger Resume Session"),
              style: ElevatedButton.styleFrom(padding: const EdgeInsets.all(16)),
            ),
            const SizedBox(height: 12),
            ElevatedButton.icon(
              onPressed: () => _sendAction("analyze_screen"),
              icon: const Icon(Icons.remove_red_eye),
              label: const Text("Trigger Analyze Screen"),
              style: ElevatedButton.styleFrom(padding: const EdgeInsets.all(16)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoCard(String title, String value) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(color: Colors.white54, fontSize: 12)),
          const SizedBox(height: 4),
          Text(value, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }
}
