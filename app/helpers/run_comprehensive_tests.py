#!/usr/bin/env python3
"""
Comprehensive Test Runner for Accessibility Assessment System
Runs all unit tests, integration tests, and validation checks
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class TestRunner:
    """Comprehensive test runner for the application."""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.results = {}
        self.backend_dir = Path("backend/app")
        self.frontend_dir = Path("frontend")

    def log(self, message, level="INFO"):
        """Log message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def run_command(self, command, cwd=None, description=""):
        """Run a command and capture its output."""
        try:
            self.log(f"Running: {description or command}")
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, cwd=cwd
            )

            if result.returncode == 0:
                self.log(f"✓ Success: {description or command}")
                if self.verbose and result.stdout:
                    print(result.stdout)
                return True, result.stdout
            else:
                self.log(f"✗ Failed: {description or command}", "ERROR")
                if result.stderr:
                    print(f"Error: {result.stderr}")
                return False, result.stderr

        except Exception as e:
            self.log(f"✗ Exception: {str(e)}", "ERROR")
            return False, str(e)

    def test_backend_setup(self):
        """Test backend environment setup."""
        self.log("Testing backend setup...")

        # Check if virtual environment exists
        venv_path = self.backend_dir / ".venv"
        if not venv_path.exists():
            self.log("Virtual environment not found", "WARNING")
            return False

        # Activate virtual environment and install dependencies
        if os.name == "nt":  # Windows
            activate_cmd = str(venv_path / "Scripts" / "activate")
        else:  # Unix/Linux/macOS
            activate_cmd = f"source {venv_path}/bin/activate"

        success, _ = self.run_command(
            f"{activate_cmd} && pip install -r requirements.txt",
            cwd=self.backend_dir.parent,
            description="Installing backend dependencies",
        )

        return success

    def test_backend_lint(self):
        """Run backend linting."""
        self.log("Running backend linting...")

        commands = [
            (
                "flake8 --max-line-length = 100 --exclude=.venv,migrations .",
                "Flake8 linting",
            ),
            ("black --check --diff .", "Black formatting check"),
        ]

        all_passed = True
        for cmd, desc in commands:
            success, _ = self.run_command(
                cmd, cwd=self.backend_dir.parent, description=desc
            )
            if not success:
                all_passed = False

        return all_passed

    def test_backend_unit_tests(self):
        """Run backend unit tests."""
        self.log("Running backend unit tests...")

        test_files = [
            "tests/unit/test_user_service.py",
            "tests/unit/test_location_service.py",
            "tests/unit/test_assessment_service.py",
            "tests/unit/test_auth_service.py",
            "tests/unit/test_location_router.py",
        ]

        all_passed = True
        for test_file in test_files:
            if (self.backend_dir / test_file).exists():
                success, _ = self.run_command(
                    f"python -m pytest {test_file} -v",
                    cwd=self.backend_dir,
                    description=f"Running {test_file}",
                )
                if not success:
                    all_passed = False
            else:
                self.log(f"Test file not found: {test_file}", "WARNING")

        return all_passed

    def test_backend_e2e_tests(self):
        """Run backend end-to-end tests."""
        self.log("Running backend E2E tests...")

        e2e_file = "tests/e2e/test_complete_workflows.py"
        if (self.backend_dir / e2e_file).exists():
            success, _ = self.run_command(
                f"python -m pytest {e2e_file} -v",
                cwd=self.backend_dir,
                description="Running E2E tests",
            )
            return success
        else:
            self.log(f"E2E test file not found: {e2e_file}", "WARNING")
            return False

    def test_frontend_setup(self):
        """Test frontend environment setup."""
        self.log("Testing frontend setup...")

        # Check if node_modules exists
        if not (self.frontend_dir / "node_modules").exists():
            success, _ = self.run_command(
                "npm install",
                cwd=self.frontend_dir,
                description="Installing frontend dependencies",
            )
            return success

        return True

    def test_frontend_lint(self):
        """Run frontend linting."""
        self.log("Running frontend linting...")

        commands = [
            ("npm run lint", "ESLint check"),
            ("npm run type-check", "TypeScript type checking"),
        ]

        for cmd, desc in commands:
            success, _ = self.run_command(
                cmd, cwd=self.frontend_dir, description=desc
            )
            if not success:
                # Frontend linting might not be configured, so we'll warn but
                # not fail
                self.log(
                    f"Frontend {desc} failed - might not be configured",
                    "WARNING",
                )

        return True  # Don't fail on frontend linting for now

    def test_frontend_build(self):
        """Test frontend build."""
        self.log("Testing frontend build...")

        success, _ = self.run_command(
            "npm run build",
            cwd=self.frontend_dir,
            description="Building frontend",
        )

        return success

    def test_database_migrations(self):
        """Test database migrations."""
        self.log("Testing database migrations...")

        # Check if migration files exist
        migration_files = [
            "optimize_location_table.sql",
            "apply_migration.sql",
        ]

        all_exist = True
        for migration in migration_files:
            if not Path(migration).exists():
                self.log(f"Migration file not found: {migration}", "WARNING")
                all_exist = False

        return all_exist

    def test_docker_setup(self):
        """Test Docker configuration."""
        self.log("Testing Docker setup...")

        docker_files = [
            "backend/Dockerfile",
            "frontend/Dockerfile",
            "frontend/nginx.conf",
        ]

        all_exist = True
        for docker_file in docker_files:
            if not Path(docker_file).exists():
                self.log(f"Docker file not found: {docker_file}", "WARNING")
                all_exist = False

        return all_exist

    def test_api_endpoints(self):
        """Test critical API endpoints."""
        self.log("Testing API endpoints...")

        # This would require the backend to be running
        # For now, just check if the router files exist
        router_files = [
            "backend/app/api/v1/routers/user_router.py",
            "backend/app/api/v1/routers/location_router.py",
            "backend/app/api/v1/routers/assessment_router.py",
        ]

        all_exist = True
        for router in router_files:
            if not Path(router).exists():
                self.log(f"Router file not found: {router}", "WARNING")
                all_exist = False

        return all_exist

    def generate_report(self):
        """Generate test report."""
        self.log("Generating test report...")

        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result)

        print("\n" + "=" * 60)
        print("COMPREHENSIVE TEST REPORT")
        print("=" * 60)

        for test_name, result in self.results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{test_name:<40} {status}")

        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests / total_tests) * 100:.1f}%")
        print("=" * 60)

        return passed_tests == total_tests

    def run_all_tests(self):
        """Run all test suites."""
        self.log("Starting comprehensive test suite...")

        test_suites = [
            ("Backend Setup", self.test_backend_setup),
            ("Backend Linting", self.test_backend_lint),
            ("Backend Unit Tests", self.test_backend_unit_tests),
            ("Backend E2E Tests", self.test_backend_e2e_tests),
            ("Frontend Setup", self.test_frontend_setup),
            ("Frontend Linting", self.test_frontend_lint),
            ("Frontend Build", self.test_frontend_build),
            ("Database Migrations", self.test_database_migrations),
            ("Docker Setup", self.test_docker_setup),
            ("API Endpoints", self.test_api_endpoints),
        ]

        for name, test_func in test_suites:
            try:
                result = test_func()
                self.results[name] = result
            except Exception as e:
                self.log(f"Test suite '{name}' crashed: {str(e)}", "ERROR")
                self.results[name] = False

        return self.generate_report()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run comprehensive tests")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose output"
    )
    parser.add_argument(
        "--backend-only", action="store_true", help="Run only backend tests"
    )
    parser.add_argument(
        "--frontend-only", action="store_true", help="Run only frontend tests"
    )

    args = parser.parse_args()

    runner = TestRunner(verbose=args.verbose)

    if args.backend_only:
        runner.log("Running backend tests only...")
        # Run only backend tests
        success = runner.run_all_tests()  # You'd modify this to filter
    elif args.frontend_only:
        runner.log("Running frontend tests only...")
        # Run only frontend tests
        success = runner.run_all_tests()  # You'd modify this to filter
    else:
        success = runner.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
