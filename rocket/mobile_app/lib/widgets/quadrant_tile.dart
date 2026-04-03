import 'package:flutter/material.dart';

class QuadrantTile extends StatelessWidget {
  const QuadrantTile({
    required this.title,
    required this.subtitle,
    required this.onTap,
    required this.onDoubleTap,
    required this.active,
    required this.backgroundColor,
    required this.icon,
    super.key,
  });

  final String title;
  final String subtitle;
  final VoidCallback onTap;
  final VoidCallback onDoubleTap;
  final bool active;
  final Color backgroundColor;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      onDoubleTap: onDoubleTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        margin: const EdgeInsets.all(12),
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: active ? backgroundColor.withOpacity(0.92) : backgroundColor,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(
            color: active ? Colors.black : Colors.black12,
            width: active ? 2.4 : 1.0,
          ),
          boxShadow: <BoxShadow>[
            BoxShadow(
              color: Colors.black.withOpacity(0.06),
              blurRadius: active ? 22 : 12,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: <Widget>[
            Icon(icon, size: 34, color: Colors.black87),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.w700,
                    color: Colors.black87,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  subtitle,
                  style: const TextStyle(
                    fontSize: 15,
                    height: 1.35,
                    color: Colors.black54,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
