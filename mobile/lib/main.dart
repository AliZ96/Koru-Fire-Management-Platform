import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

void main() {
  runApp(const KoruApp());
}

class KoruApp extends StatelessWidget {
  const KoruApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'KORU',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark(),
      home: const LoginPage(),
    );
  }
}

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {

  final usernameController = TextEditingController();
  final passwordController = TextEditingController();

  String userType = "user";

  void login() {

    String username = usernameController.text;
    String password = passwordController.text;

    if(username.isEmpty || password.isEmpty){
      showError("Tüm alanları doldurun");
      return;
    }

    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => WelcomePage(username: username),
      ),
    );
  }

  void showError(String msg){
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text("Hata"),
        content: Text(msg),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {

    return Scaffold(
      body: Stack(
        children: [

          /// SVG ARKA PLAN
          SizedBox.expand(
            child: SvgPicture.asset(
              "assets/login-bg.svg",
              fit: BoxFit.cover,
            ),
          ),

          /// LOGIN FORM
          Center(
            child: Container(
              width: 350,
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.green[900],
                borderRadius: BorderRadius.circular(15),
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [

                  const Text(
                    "KORU",
                    style: TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.bold,
                    ),
                  ),

                  const SizedBox(height: 20),

                  Row(
                    children: [

                      Expanded(
                        child: ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor:
                            userType=="user"?Colors.green:Colors.grey,
                          ),
                          onPressed: (){
                            setState(() {
                              userType="user";
                            });
                          },
                          child: const Text("Kullanıcı"),
                        ),
                      ),

                      const SizedBox(width: 10),

                      Expanded(
                        child: ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor:
                            userType=="admin"?Colors.green:Colors.grey,
                          ),
                          onPressed: (){
                            setState(() {
                              userType="admin";
                            });
                          },
                          child: const Text("Admin"),
                        ),
                      ),

                    ],
                  ),

                  const SizedBox(height: 20),

                  TextField(
                    controller: usernameController,
                    decoration: const InputDecoration(
                      labelText: "Kullanıcı Adı",
                    ),
                  ),

                  const SizedBox(height: 10),

                  TextField(
                    controller: passwordController,
                    obscureText: true,
                    decoration: const InputDecoration(
                      labelText: "Şifre",
                    ),
                  ),

                  const SizedBox(height: 20),

                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: login,
                      child: const Text("Giriş Yap"),
                    ),
                  ),

                ],
              ),
            ),
          ),

        ],
      ),
    );
  }
}

class WelcomePage extends StatelessWidget {

  final String username;

  const WelcomePage({super.key, required this.username});

  @override
  Widget build(BuildContext context) {

    return Scaffold(
      appBar: AppBar(title: const Text("KORU")),

      body: Center(
        child: Text(
          "Hoşgeldin $username",
          style: const TextStyle(fontSize: 24),
        ),
      ),
    );
  }
}
