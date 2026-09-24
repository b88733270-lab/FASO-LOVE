import 'package:faso_love/core/constants/app_colors.dart';
import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

/// Boutons d'action de la file « Découvrir » : passer / aimer / coup de cœur.
class ActionButtons extends StatelessWidget {
  final VoidCallback onSwipeLeft;
  final VoidCallback onSwipeRight;
  final VoidCallback onSuperLike;

  const ActionButtons({
    super.key,
    required this.onSwipeLeft,
    required this.onSwipeRight,
    required this.onSuperLike,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 40),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          _buildActionButton(
            icon: FontAwesomeIcons.xmark,
            tooltip: 'Passer',
            color: Colors.white,
            backgroundColor: AppColors.pass.withOpacity(0.75),
            onPressed: onSwipeLeft,
          ),
          _buildActionButton(
            icon: FontAwesomeIcons.solidHeart,
            tooltip: 'Aimer',
            color: Colors.white,
            backgroundColor: AppColors.like,
            size: 28,
            onPressed: onSwipeRight,
          ),
          _buildActionButton(
            icon: FontAwesomeIcons.solidStar,
            tooltip: 'Coup de cœur',
            color: Colors.white,
            backgroundColor: AppColors.superLike,
            onPressed: onSuperLike,
          ),
        ],
      ),
    );
  }

  Widget _buildActionButton({
    required IconData icon,
    required String tooltip,
    required Color color,
    required Color backgroundColor,
    double size = 24,
    required VoidCallback onPressed,
  }) {
    return Container(
      width: 60,
      height: 60,
      decoration: BoxDecoration(
        color: backgroundColor,
        shape: BoxShape.circle,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.2),
            blurRadius: 10,
            spreadRadius: 2,
          )
        ],
      ),
      child: IconButton(
        icon: FaIcon(icon, size: size, color: color),
        tooltip: tooltip,
        onPressed: onPressed,
      ),
    );
  }
}
