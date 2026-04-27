# Firebase Firestore Dokumantasyonu (KORU)

Bu dokuman, KORU projesinde Firebase Authentication ve Firestore entegrasyonunun nasil calistigini ozellikle **kullaniciyi koleksiyona ekleme** adimini aciklar.

## 1) Genel Mimari

- Kimlik dogrulama: Firebase Authentication (Email/Password)
- Veri yazma: Cloud Firestore (NoSQL)
- Koleksiyon: `users`
- Dokuman ID: Firebase Auth tarafindan uretilen `user.uid`

Bu yapi sayesinde her kullanicinin Firestore kaydi, Auth UID ile birebir eslesir.

## 2) Firestore'da `users` Koleksiyonu Alanlari

PostgreSQL semasindaki alan isimleri Firestore tarafinda da korunmustur:

- `username` (string)
- `password_hash` (string)
- `role` (string: `USER`, `FIREFIGHTER`, `ADMIN`)
- `created_at` (timestamp)

Not: Firebase Authentication sifre hash bilgisini istemciye vermez. Bu nedenle `password_hash` alani uygulamada sabit bir isaretleyici ile yazilir:

- `FIREBASE_AUTH_MANAGED`

## 3) Kullanici Koleksiyona Nasil Ekleniyor?

Kullanici ekleme hem kayit hem giris sonrasinda "ping" mantigi ile yapilir:

1. Kullanici Firebase Auth ile giris yapar veya kayit olur.
2. `idToken` ve `uid` alinir.
3. Firestore `users/{uid}` dokumanina `PATCH` istegi atilir.
4. Dokuman yoksa olusturulur, varsa guncellenir (upsert davranisi).

Kullanilan endpoint:

`https://firestore.googleapis.com/v1/projects/koru-41307/databases/(default)/documents/users/{uid}`

## 4) Ornek Firestore Ping Govdesi

```json
{
  "fields": {
    "username": { "stringValue": "testuser.koru@example.com" },
    "password_hash": { "stringValue": "FIREBASE_AUTH_MANAGED" },
    "role": { "stringValue": "USER" },
    "created_at": { "timestampValue": "2026-04-26T14:55:43.280904Z" }
  }
}
```

## 5) Uygulamadaki Akis (Ozet)

- Dosyalar:
  - `static/login.html`
  - `static/home.html`
- Ortak fonksiyon: `pingFirestoreUser({ idToken, uid, username, role })`
- Auth basarili olduktan sonra bu fonksiyon cagrilir.

## 6) Guvenlik ve Dikkat Notlari

- `idToken`, `Authorization: Bearer <token>` basliginda gonderilir.
- Firestore Security Rules, kullanicinin sadece kendi `users/{uid}` kaydina yazmasina izin verecek sekilde kisitlanmalidir.
- `role` alani istemciden geldigi icin production ortamda backend veya Cloud Functions ile dogrulanmasi tavsiye edilir.

## 7) Hata Durumlari

Yaygin hatalar:

- `permission-denied`: Firestore rule engeli
- `unauthenticated`: token yok / gecersiz
- `not-found`: proje/veritabani yolu yanlis

Bu durumda:

1. Firebase Console -> Authentication ve Firestore ayarlarini kontrol et
2. Proje ID'nin `koru-41307` oldugunu dogrula
3. Firestore rule'larin `users/{uid}` yazimini kapsadigindan emin ol
