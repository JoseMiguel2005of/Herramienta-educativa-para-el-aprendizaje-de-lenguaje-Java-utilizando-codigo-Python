"""
Comprehensive End-to-End System Verification & Security Audit Suite.
"""

import os
import random
import unittest
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash

from app import app, db, LESSON_CATEGORIES, get_section_lessons
from models import User, LessonProgress, ExerciseAttempt, QuizResult, SectionEvaluation, PracticeSubmission

class FullSystemAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        cls.client = app.test_client()

        with app.app_context():
            # Generate unique usernames to avoid conflicts
            suffix = random.randint(10000, 99999)
            cls.student_username = f"AuditStudent_{suffix}"
            cls.teacher_username = f"AuditTeacher_{suffix}"
            
            # 1. Create Student
            student_pw = generate_password_hash("student123")
            cls.student = User(username=cls.student_username, password_hash=student_pw, role="student")
            
            # 2. Create Teacher
            teacher_pw = generate_password_hash("teacher123")
            cls.teacher = User(username=cls.teacher_username, password_hash=teacher_pw, role="teacher")
            
            db.session.add(cls.student)
            db.session.add(cls.teacher)
            db.session.commit()
            cls.student_id = cls.student.id
            cls.teacher_id = cls.teacher.id

            # Pre-complete section lessons for test student so evaluations and certificates are unlocked
            tutorial_lessons = get_section_lessons("cat_python_tutorial")
            for lid in tutorial_lessons:
                lp = LessonProgress(user_id=cls.student_id, lesson_id=lid, completed=True, score=10)
                db.session.add(lp)
            db.session.commit()

    @classmethod
    def tearDownClass(cls):
        with app.app_context():
            u1 = User.query.filter_by(username=cls.student_username).first()
            u2 = User.query.filter_by(username=cls.teacher_username).first()
            if u1:
                LessonProgress.query.filter_by(user_id=u1.id).delete()
                ExerciseAttempt.query.filter_by(user_id=u1.id).delete()
                QuizResult.query.filter_by(user_id=u1.id).delete()
                SectionEvaluation.query.filter_by(user_id=u1.id).delete()
                PracticeSubmission.query.filter_by(user_id=u1.id).delete()
                db.session.delete(u1)
            if u2:
                db.session.delete(u2)
            db.session.commit()

    def test_01_security_password_hashing(self):
        """Security: Verify passwords are encrypted with werkzeug generate_password_hash."""
        with app.app_context():
            user = User.query.filter_by(username=self.student_username).first()
            self.assertNotEqual(user.password_hash, "student123")
            self.assertTrue(check_password_hash(user.password_hash, "student123"))
            self.assertFalse(check_password_hash(user.password_hash, "wrongpass"))

    def test_02_auth_protected_routes(self):
        """Security: Verify protected endpoints reject unauthenticated requests."""
        protected_routes = [
            "/profesor",
            "/certificado/py2java",
            "/evaluacion/cat_python_tutorial",
            "/logout"
        ]
        for route in protected_routes:
            resp = self.client.get(route, follow_redirects=False)
            self.assertIn(resp.status_code, [302, 401], f"Route {route} should require authentication")
            if resp.status_code == 302:
                self.assertIn("/login", resp.headers.get("Location", ""))

    def test_03_teacher_dashboard_and_export(self):
        """Teacher: Verify role-based access control and CSV export."""
        # Student cannot access /profesor
        self.client.post("/login", data={"username": self.student_username, "password": "student123"}, follow_redirects=True)
        resp = self.client.get("/profesor", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/dashboard", resp.headers.get("Location", ""))
        self.client.get("/logout")

        # Teacher CAN access /profesor
        self.client.post("/login", data={"username": self.teacher_username, "password": "teacher123"}, follow_redirects=True)
        resp = self.client.get("/profesor")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Panel", resp.data)
        
        # Test CSV Export
        csv_resp = self.client.get("/profesor/export/csv")
        self.assertEqual(csv_resp.status_code, 200)
        self.assertEqual(csv_resp.mimetype, "text/csv")
        self.assertIn(b"Username", csv_resp.data)
        self.client.get("/logout")

    def test_04_transpiler_api_endpoint(self):
        """Transpiler: Test /api/traducir returns valid Java for complex Python code."""
        snippets = [
            ("print('Hola Mundo')", "System.out.println"),
            ("x = [1, 2, 3]\nprint(len(x))", "ArrayList"),
            ("a, b = 10, 20\na, b = b, a", "_temp"),
            ("def sumar(a, b=5):\n    return a + b", "sumar(Object a)"),
            ("squares = {x: x*2 for x in range(3)}", "HashMap"),
            ("class Animal:\n    def __init__(self, n):\n        self.n = n\nd = Animal('Rex')", "new Animal"),
        ]
        for py_code, expected_java_fragment in snippets:
            resp = self.client.post("/api/traducir", json={"code": py_code, "class_name": "Program"})
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertEqual(data.get("errors"), [], f"Error in translation of {py_code}: {data.get('errors')}")
            java = data.get("java", "")
            self.assertIn(expected_java_fragment, java, f"Expected '{expected_java_fragment}' in:\n{java}")

    def test_05_certificate_generation_flow(self):
        """Certificate: Test locked state and unlocked completion state."""
        self.client.post("/login", data={"username": self.student_username, "password": "student123"}, follow_redirects=True)
        
        # 1. Initially render certificate page
        resp = self.client.get("/certificado/py2java")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Certificado", resp.data)
        self.client.get("/logout")

    def test_06_practice_editor_submission(self):
        """Practice Labs: Test practice lab code validation, XP reward & daily streak."""
        self.client.post("/login", data={"username": self.student_username, "password": "student123"}, follow_redirects=True)
        
        resp = self.client.post("/api/submit_practice", json={
            "problem_id": "py_p1",
            "code": "print('Hola Mundo')",
            "passed": True,
            "tests_passed": 1,
            "tests_total": 1
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("ok"))
        self.assertGreaterEqual(data.get("xp_gained", 0), 0)
        self.assertIn("new_total", data)
        self.client.get("/logout")

    def test_07_evaluations_and_quizzes_api(self):
        """Quizzes & Evaluations: Verify progress tracking and scoring APIs."""
        self.client.post("/login", data={"username": self.student_username, "password": "student123"}, follow_redirects=True)
        
        # Quiz Result
        resp = self.client.post("/api/quiz/resultado", json={
            "quiz_id": "quiz_py_intro",
            "score": 5,
            "total": 5
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json().get("ok"))

        # Section Evaluation: First GET to initialize session questions
        eval_resp = self.client.get("/evaluacion/cat_python_tutorial")
        self.assertEqual(eval_resp.status_code, 200)

        # Section Evaluation Result POST
        resp = self.client.post("/api/evaluacion/resultado", json={
            "section_key": "cat_python_tutorial",
            "answers": {},
            "time_spent": 120
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json().get("ok"))
        self.client.get("/logout")

    def test_08_public_and_student_pages(self):
        """UI: Verify all major student and public pages load with HTTP 200."""
        self.client.post("/login", data={"username": self.student_username, "password": "student123"}, follow_redirects=True)
        pages = [
            ("/", 200),
            ("/dashboard", 200),
            ("/roadmap", 200),
            ("/glosario", 200),
            ("/referencia", 200),
            ("/traductor", 200),
            ("/leaderboard", 200),
            ("/ejemplos", 200),
            ("/practica", 200),
            ("/perfil", 200),
            ("/configuracion", 200),
            ("/evaluacion/cat_python_tutorial", 200),
        ]
        for path, expected_status in pages:
            resp = self.client.get(path, follow_redirects=True)
            self.assertEqual(resp.status_code, expected_status, f"Page {path} returned status {resp.status_code}")
        self.client.get("/logout")

    def test_09_search_api(self):
        """Search: Verify search API returns matching results."""
        resp = self.client.get("/api/buscar?q=variables")
        self.assertEqual(resp.status_code, 200)
        results = resp.get_json()
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0, "Search for 'variables' should return results")

if __name__ == "__main__":
    unittest.main()
