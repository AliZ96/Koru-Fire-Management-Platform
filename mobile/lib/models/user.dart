class User {
  final String username;
  final String role; // 'user', 'admin', 'firefighter'
  final String? fullname;
  final String? email;
  final String? accessToken;

  User({
    required this.username,
    required this.role,
    this.fullname,
    this.email,
    this.accessToken,
  });

  bool get isAdmin => role == 'admin';
  bool get isFirefighter => role == 'firefighter';

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      username: json['sub'] ?? json['username'] ?? '',
      role: json['role'] ?? 'user',
      fullname: json['fullname'],
      email: json['email'],
    );
  }

  User copyWith({String? accessToken}) {
    return User(
      username: username,
      role: role,
      fullname: fullname,
      email: email,
      accessToken: accessToken ?? this.accessToken,
    );
  }
}
