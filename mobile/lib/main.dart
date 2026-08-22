import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker_android/image_picker_android.dart';
import 'package:image_picker_platform_interface/image_picker_platform_interface.dart';

import 'app.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  // Use the Android system Photo Picker (no READ_MEDIA_IMAGES permission needed).
  // On Android 13+ this uses PickVisualMedia; on older Android 11/12 devices with
  // the Photo Picker back-port, it does the same. Camera source is unaffected.
  final picker = ImagePickerPlatform.instance;
  if (picker is ImagePickerAndroid) {
    picker.useAndroidPhotoPicker = true;
  }

  runApp(const ProviderScope(child: App()));
}
