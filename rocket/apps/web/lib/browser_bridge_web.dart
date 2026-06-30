// ignore_for_file: avoid_web_libraries_in_flutter, deprecated_member_use

import 'dart:html' as html;

String get origin => html.window.location.origin;

void openUrl(String url) {
  html.window.open(url, '_blank');
}
