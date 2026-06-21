import 'package:flutter/material.dart';

import '../models/app_theme.dart';

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
    return Semantics(
      button: true,
      label: '$title. $subtitle',
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        onDoubleTap: onDoubleTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          margin: const EdgeInsets.all(AppTheme.spacingS),
          padding: const EdgeInsets.all(AppTheme.spacingL),
          constraints: const BoxConstraints(minHeight: 120),
          decoration: AppTheme.cardDecoration(
            backgroundColor: backgroundColor,
            isSelected: active,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: <Widget>[
              Icon(
                icon,
                size: 34,
                color: AppTheme.textPrimary.withValues(alpha: 0.85),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    title,
                    style: AppTheme.headingMedium,
                  ),
                  const SizedBox(height: AppTheme.spacingS),
                  Text(
                    subtitle,
                    style: AppTheme.bodySmall.copyWith(
                      height: 1.35,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
