import 'package:faso_love/core/constants/assets_path.dart';
import 'package:flutter/material.dart';

/// Retourne le provider d'image adapté à la source :
/// - URL distante (`http(s)…`) → [NetworkImage] (photos servies par le
///   backend FASO LOVE) ;
/// - chemin local → [AssetImage] (placeholders embarqués) ;
/// - chaîne vide → placeholder générique (jamais de crash de rendu).
///
/// Centraliser ce choix ici évite de disperser la logique asset/réseau
/// dans les écrans.
ImageProvider profileImageProvider(String source) {
  if (source.isEmpty) {
    return const AssetImage(AssetsPath.avatar1);
  }
  if (source.startsWith('http')) {
    return NetworkImage(source);
  }
  return AssetImage(source);
}
