import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _ipController = TextEditingController();
  bool _autoConnect = true;
  bool _darkMode = true;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _ipController.text = prefs.getString('server_ip') ?? "192.168.1.100:8000";
      _autoConnect = prefs.getBool('auto_connect') ?? true;
      _darkMode = prefs.getBool('dark_mode') ?? true;
    });
  }

  Future<void> _saveIp(String value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('server_ip', value);
  }

  @override
  void dispose() {
    _ipController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          const Text(
            'Settings',
            style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Color(0xFF7C6AEF)),
          ),
          const SizedBox(height: 24),
          const Text("CONNECTION", style: TextStyle(color: Colors.white54, fontSize: 12, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          TextField(
            controller: _ipController,
            decoration: const InputDecoration(
              labelText: 'PC IP Address (e.g. 192.168.1.100:8000)',
              border: OutlineInputBorder(),
              filled: true,
              fillColor: Color(0xFF1A1A1A),
            ),
            onSubmitted: _saveIp,
          ),
          const SizedBox(height: 16),
          SwitchListTile(
            title: const Text('Auto Connect'),
            value: _autoConnect,
            onChanged: (val) {
              setState(() => _autoConnect = val);
              SharedPreferences.getInstance().then((p) => p.setBool('auto_connect', val));
            },
          ),
          const Divider(height: 32, color: Colors.white10),
          const Text("APPEARANCE", style: TextStyle(color: Colors.white54, fontSize: 12, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          SwitchListTile(
            title: const Text('Dark Mode'),
            value: _darkMode,
            onChanged: (val) {
              setState(() => _darkMode = val);
              SharedPreferences.getInstance().then((p) => p.setBool('dark_mode', val));
            },
          ),
          const Divider(height: 32, color: Colors.white10),
          const Text("FUTURE INTEGRATIONS (DISABLED)", style: TextStyle(color: Colors.white54, fontSize: 12, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          SwitchListTile(title: const Text('Hardware Bridge'), value: false, onChanged: null),
          SwitchListTile(title: const Text('Telegram Bridge'), value: false, onChanged: null),
          SwitchListTile(title: const Text('Android Notifications'), value: false, onChanged: null),
          const Divider(height: 32, color: Colors.white10),
          const Center(
            child: Text("Version 1.0.0", style: TextStyle(color: Colors.white54)),
          ),
        ],
      ),
    );
  }
}
