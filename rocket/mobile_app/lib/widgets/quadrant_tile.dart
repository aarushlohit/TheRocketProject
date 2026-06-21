import 'package:flutter/material.dart';

import '../models/app_theme.dart';

class QuadrantTile extends StatelessWidget {
  const QuadrantTile({
    required this.title,
    required this.onTap,
    required this.onDoubleTap,
    required this.backgroundColor,
    this.icon,
    this.symbol,
    super.key,
  });

  final String title;
  final VoidCallback onTap;
  final VoidCallback onDoubleTap;
  final Color backgroundColor;
  final IconData? icon;
  final String? symbol;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: '$title. Double tap to enter.',
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        onDoubleTap: onDoubleTap,
        child: Container(
          color: backgroundColor,
          child: DecoratedBox(
            decoration: BoxDecoration(
              border: Border.all(color: Colors.white, width: 1.5),
            ),
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  if (symbol != null)
                    Text(
                      symbol!,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 76,
                        fontWeight: FontWeight.w700,
                      ),
                    )
                  else
                    Icon(
                      icon,
                      size: 76,
                      color: Colors.white,
                    ),
                  const SizedBox(height: AppTheme.spacingM),
                  Text(
                    title.toUpperCase(),
                    style: AppTheme.headingMedium.copyWith(
                      color: Colors.white,
                      fontSize: 28,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
