/**
 * Getting a photo out of the phone and into the shape the upload wants.
 *
 * Images are compressed before they leave the device: the API rejects anything
 * over 8MB, and a modern phone camera clears that on its own.
 */

import * as ImagePicker from 'expo-image-picker';

import type { Photo } from '../api/client';

const OPTIONS: ImagePicker.ImagePickerOptions = {
  mediaTypes: ['images'],
  quality: 0.7,
  allowsMultipleSelection: false,
  exif: false,
};

export class PermissionDenied extends Error {
  constructor(what: 'camera' | 'library') {
    super(
      what === 'camera'
        ? 'SuqCheck needs camera access to read a receipt or shelf tag.'
        : 'SuqCheck needs photo access to upload an existing picture.',
    );
    this.name = 'PermissionDenied';
  }
}

function toPhoto(result: ImagePicker.ImagePickerResult): Photo | null {
  if (result.canceled || result.assets.length === 0) return null;
  const asset = result.assets[0];
  return { uri: asset.uri, mimeType: asset.mimeType, fileName: asset.fileName };
}

export async function takePhoto(): Promise<Photo | null> {
  const permission = await ImagePicker.requestCameraPermissionsAsync();
  if (!permission.granted) throw new PermissionDenied('camera');
  return toPhoto(await ImagePicker.launchCameraAsync(OPTIONS));
}

export async function choosePhoto(): Promise<Photo | null> {
  const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
  if (!permission.granted) throw new PermissionDenied('library');
  return toPhoto(await ImagePicker.launchImageLibraryAsync(OPTIONS));
}
