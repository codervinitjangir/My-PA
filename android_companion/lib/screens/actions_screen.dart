import 'package:flutter/material.dart';
import '../api_service.dart';

class ActionsScreen extends StatelessWidget {
  const ActionsScreen({super.key});

  void _openSite(BuildContext context, String alias) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Opening $alias on PC...'), duration: const Duration(seconds: 1)));
    ApiService.sendAction("open_site", {"site": alias});
  }

  @override
  Widget build(BuildContext context) {
    final sites = [
      {"name": "GitHub", "alias": "github", "icon": Icons.code},
      {"name": "LinkedIn", "alias": "linkedin", "icon": Icons.work},
      {"name": "ChatGPT", "alias": "chatgpt", "icon": Icons.chat},
      {"name": "Claude", "alias": "claude", "icon": Icons.smart_toy},
      {"name": "Notion", "alias": "notion", "icon": Icons.description},
      {"name": "LeetCode", "alias": "leetcode", "icon": Icons.terminal},
    ];

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Quick Actions',
              style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Color(0xFF7C6AEF)),
            ),
            const SizedBox(height: 24),
            Expanded(
              child: GridView.builder(
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  crossAxisSpacing: 16,
                  mainAxisSpacing: 16,
                  childAspectRatio: 1.2,
                ),
                itemCount: sites.length,
                itemBuilder: (context, index) {
                  final site = sites[index];
                  return _buildActionCard(context, site['name'] as String, site['alias'] as String, site['icon'] as IconData);
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionCard(BuildContext context, String title, String alias, IconData icon) {
    return InkWell(
      onTap: () => _openSite(context, alias),
      borderRadius: BorderRadius.circular(12),
      child: Ink(
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.white10),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 36, color: Colors.white70),
            const SizedBox(height: 12),
            Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          ],
        ),
      ),
    );
  }
}
