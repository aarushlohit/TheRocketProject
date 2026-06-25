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
              border: Border.all(color: Colors.white, width: 2.5),
            ),
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  if (symbol != null)
                    const _BrailleDotsIcon()
                  else
                    Icon(
                      icon,
                      size: 92,
                      color: Colors.white,
                    ),
                  const SizedBox(height: AppTheme.spacingL),
                  Text(
                    title.toUpperCase(),
                    style: AppTheme.headingMedium.copyWith(
                      color: Colors.white,
                      fontSize: 34,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 1,
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

class _BrailleDotsIcon extends StatelessWidget {
  const _BrailleDotsIcon();

  @override
  Widget build(BuildContext context) {
    return const SizedBox(
      width: 76,
      height: 102,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          _BrailleDotColumn(),
          _BrailleDotColumn(),
        ],
      ),
    );
  }
}

class _BrailleDotColumn extends StatelessWidget {
  const _BrailleDotColumn();

  @override
  Widget build(BuildContext context) {
    return const Column(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        _BrailleDot(),
        _BrailleDot(),
        _BrailleDot(),
      ],
    );
  }
}

class _BrailleDot extends StatelessWidget {
  const _BrailleDot();

  @override
  Widget build(BuildContext context) {
    return const DecoratedBox(
      decoration: BoxDecoration(
        color: Colors.white,
        shape: BoxShape.circle,
      ),
      child: SizedBox.square(dimension: 24),
    );
  }
}
