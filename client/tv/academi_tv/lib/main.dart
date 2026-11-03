import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import 'dart:convert';

void main() => runApp(const AcademiTVApp());

class AcademiTVApp extends StatelessWidget {
  const AcademiTVApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Academi TV',
      theme: ThemeData(brightness: Brightness.dark, primarySwatch: Colors.blue),
      home: const TVCoursesPage(),
    );
  }
}

class TVCoursesPage extends StatefulWidget {
  const TVCoursesPage({super.key});

  @override
  State<TVCoursesPage> createState() => _TVCoursesPageState();
}

class _TVCoursesPageState extends State<TVCoursesPage> {
  List courses = [];
  bool isLoading = true;
  String errorMessage = '';

  @override
  void initState() {
    super.initState();
    loadCourses();
  }

  Future<void> loadCourses() async {
    try {
      final response = await http.get(
        Uri.parse('http://localhost:8000/api/courses'),
      );
      if (response.statusCode == 200) {
        setState(() {
          courses = json.decode(response.body);
          isLoading = false;
        });
      } else {
        setState(() {
          errorMessage = 'Ошибка сервера: ${response.statusCode}';
          isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        errorMessage = 'Ошибка подключения: $e';
        isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: Padding(
        padding: const EdgeInsets.all(40),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Мои курсы',
              style: TextStyle(
                fontSize: 48,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 30),
            Expanded(child: _buildContent()),
          ],
        ),
      ),
    );
  }

  Widget _buildContent() {
    if (isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (errorMessage.isNotEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              errorMessage,
              style: const TextStyle(color: Colors.red, fontSize: 20),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: loadCourses,
              child: const Text('Повторить'),
            ),
          ],
        ),
      );
    }
    if (courses.isEmpty) {
      return const Center(
        child: Text(
          'Курсов пока нет',
          style: TextStyle(color: Colors.white70, fontSize: 24),
        ),
      );
    }
    return GridView.builder(
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 3,
        childAspectRatio: 1.5,
        crossAxisSpacing: 20,
        mainAxisSpacing: 20,
      ),
      itemCount: courses.length,
      itemBuilder: (context, index) {
        final course = courses[index];
        return FocusableCourseCard(
          title: course['title'],
          duration: course['duration'],
        );
      },
    );
  }
}

class FocusableCourseCard extends StatefulWidget {
  final String title;
  final String duration;
  const FocusableCourseCard({
    super.key,
    required this.title,
    required this.duration,
  });

  @override
  State<FocusableCourseCard> createState() => _FocusableCourseCardState();
}

class _FocusableCourseCardState extends State<FocusableCourseCard> {
  bool _focused = false;

  @override
  Widget build(BuildContext context) {
    return Focus(
      onFocusChange: (focused) => setState(() => _focused = focused),
      child: Container(
        decoration: BoxDecoration(
          color: _focused ? Colors.blue[700] : Colors.grey[900],
          borderRadius: BorderRadius.circular(15),
          border: Border.all(
            color: _focused ? Colors.white : Colors.transparent,
            width: 4,
          ),
        ),
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              widget.title,
              style: const TextStyle(
                fontSize: 32,
                color: Colors.white,
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 10),
            Text(
              widget.duration,
              style: const TextStyle(fontSize: 22, color: Colors.white70),
            ),
          ],
        ),
      ),
    );
  }
}
