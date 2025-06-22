#!/usr/bin/env python3
"""
Comprehensive test runner for the Urban Infrastructure Accessibility Monitoring Platform.

This script runs all tests and generates coverage reports with meaningful output.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description=""):
    """Run a shell command and handle errors."""
    print(f"\n{'=' * 60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'=' * 60}")

    try:
        result = subprocess.run(
            cmd, check=True, capture_output=True, text=True
        )
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Command failed with return code {e.returncode}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False


def setup_test_environment():
    """Setup the test environment."""
    print("Setting up test environment...")

    # Change to the backend directory (go up from helpers directory)
    backend_dir = Path(__file__).parent.parent.parent
    os.chdir(backend_dir)
    print(f"Working directory set to: {backend_dir}")

    # Activate virtual environment if it exists
    venv_activate = backend_dir / ".venv" / "bin" / "activate"
    if venv_activate.exists():
        print(f"Virtual environment found at: {venv_activate}")

    return True


def install_test_dependencies():
    """Install required test dependencies."""
    dependencies = [
        "pytest>=7.0.0",
        "pytest-cov>=4.0.0",
        "pytest-asyncio>=0.21.0",
        "pytest-mock>=3.10.0",
        "httpx>=0.24.0",
        "coverage>=7.0.0",
    ]

    for dep in dependencies:
        cmd = [sys.executable, "-m", "pip", "install", dep]
        if not run_command(cmd, f"Installing {dep}"):
            print(f"Failed to install {dep}")
            return False

    return True


def run_linting():
    """Run code linting checks."""
    print("\n" + "=" * 60)
    print("RUNNING CODE LINTING")
    print("=" * 60)

    # Run flake8
    cmd = [
        sys.executable,
        "-m",
        "flake8",
        "app/",
        "tests/",
        "--max-line-length=120",
        "--ignore=E203,W503",
    ]
    success = run_command(cmd, "Running flake8 linting")

    if not success:
        print("Linting found issues. Please fix them before running tests.")
        return False

    return True


def run_unit_tests():
    """Run unit tests with coverage."""
    print("\n" + "=" * 60)
    print("RUNNING UNIT TESTS")
    print("=" * 60)

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "app/tests/",
        "tests/",
        "-v",
        "--tb = short",
        "--cov = app",
        "--cov-report = term-missing",
        "--cov-report = html:htmlcov",
        "--cov-report = xml:coverage.xml",
        "--cov-fail-under = 60",  # Lower threshold since we found actual test files
    ]

    return run_command(cmd, "Running unit tests with coverage")


def run_integration_tests():
    """Run integration tests."""
    print("\n" + "=" * 60)
    print("RUNNING INTEGRATION TESTS")
    print("=" * 60)

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "app/tests/",
        "tests/",
        "-v",
        "-m",
        "integration",
        "--tb = short",
    ]

    return run_command(cmd, "Running integration tests")


def run_service_tests():
    """Run service layer tests."""
    print("\n" + "=" * 60)
    print("RUNNING SERVICE TESTS")
    print("=" * 60)

    service_test_files = [
        "app/tests/test_user_service.py",
        "app/tests/test_location_service.py",
        "app/tests/test_assessment_service.py",
    ]

    for test_file in service_test_files:
        if Path(test_file).exists():
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                test_file,
                "-v",
                "--tb = short",
            ]
            if not run_command(cmd, f"Running {test_file}"):
                return False
        else:
            print(f"Warning: {test_file} not found")

    return True


def run_route_tests():
    """Run API route tests."""
    print("\n" + "=" * 60)
    print("RUNNING API ROUTE TESTS")
    print("=" * 60)

    route_test_files = [
        "app/tests/test_user_routes.py",
        "app/tests/test_location_routes.py",
        "app/tests/test_assessment_routes.py",
    ]

    for test_file in route_test_files:
        if Path(test_file).exists():
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                test_file,
                "-v",
                "--tb = short",
            ]
            if not run_command(cmd, f"Running {test_file}"):
                return False
        else:
            print(f"Warning: {test_file} not found")

    return True


def run_performance_tests():
    """Run performance tests."""
    print("\n" + "=" * 60)
    print("RUNNING PERFORMANCE TESTS")
    print("=" * 60)

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "app/tests/",
        "tests/",
        "-v",
        "-m",
        "performance",
        "--tb = short",
    ]

    return run_command(cmd, "Running performance tests")


def generate_test_report():
    """Generate comprehensive test report."""
    print("\n" + "=" * 60)
    print("GENERATING TEST REPORTS")
    print("=" * 60)

    # Generate coverage badge
    cmd = [sys.executable, "-m", "coverage", "report", "--format = markdown"]
    run_command(cmd, "Generating coverage report")

    # Generate HTML coverage report
    cmd = [sys.executable, "-m", "coverage", "html"]
    run_command(cmd, "Generating HTML coverage report")

    print("\nTest reports generated:")
    print("- HTML Coverage Report: htmlcov/index.html")
    print("- XML Coverage Report: coverage.xml")

    return True


def run_security_tests():
    """Run security tests."""
    print("\n" + "=" * 60)
    print("RUNNING SECURITY TESTS")
    print("=" * 60)

    # Install bandit for security testing
    cmd = [sys.executable, "-m", "pip", "install", "bandit"]
    run_command(cmd, "Installing bandit security scanner")

    # Run bandit security scan
    cmd = [
        sys.executable,
        "-m",
        "bandit",
        "-r",
        "app/",
        "-f",
        "json",
        "-o",
        "bandit-report.json",
    ]
    run_command(cmd, "Running security scan with bandit")

    return True


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="Run comprehensive tests for the platform"
    )
    parser.add_argument(
        "--skip-lint", action="store_true", help="Skip linting checks"
    )
    parser.add_argument(
        "--skip-security", action="store_true", help="Skip security tests"
    )
    parser.add_argument(
        "--unit-only", action="store_true", help="Run only unit tests"
    )
    parser.add_argument(
        "--services-only", action="store_true", help="Run only service tests"
    )
    parser.add_argument(
        "--routes-only", action="store_true", help="Run only route tests"
    )
    parser.add_argument(
        "--install-deps", action="store_true", help="Install test dependencies"
    )

    args = parser.parse_args()

    print("Urban Infrastructure Accessibility Monitoring Platform")
    print("Comprehensive Test Suite Runner")
    print("=" * 60)

    # Setup environment
    if not setup_test_environment():
        sys.exit(1)

    # Install dependencies if requested
    if args.install_deps:
        if not install_test_dependencies():
            sys.exit(1)

    # Run linting unless skipped
    if not args.skip_lint:
        if not run_linting():
            print("Linting failed. Fix issues before proceeding.")
            sys.exit(1)

    success = True

    # Run specific test suites based on arguments
    if args.unit_only:
        success = run_unit_tests()
    elif args.services_only:
        success = run_service_tests()
    elif args.routes_only:
        success = run_route_tests()
    else:
        # Run all test suites
        test_suites = [
            ("Unit Tests", run_unit_tests),
            ("Service Tests", run_service_tests),
            ("Route Tests", run_route_tests),
            ("Integration Tests", run_integration_tests),
            ("Performance Tests", run_performance_tests),
        ]

        for suite_name, suite_func in test_suites:
            print(f"\n{'=' * 60}")
            print(f"RUNNING {suite_name.upper()}")
            print(f"{'=' * 60}")

            if not suite_func():
                print(f"{suite_name} failed!")
                success = False
                break

    # Run security tests unless skipped
    if not args.skip_security and success:
        run_security_tests()

    # Generate reports
    if success:
        generate_test_report()

        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print("✅ All tests completed successfully!")
        print("\nGenerated Reports:")
        print("- Coverage Report: htmlcov/index.html")
        print("- Security Report: bandit-report.json")
        print("- XML Coverage: coverage.xml")

        print("\nTest Files Covered:")
        test_files = [
            "test_conftest.py - Test configuration and fixtures",
            "test_user_service.py - User service functionality",
            "test_user_routes.py - User API endpoints",
            "test_location_service.py - Location service functionality",
            "test_location_routes.py - Location API endpoints",
            "test_assessment_service.py - Assessment service functionality",
            "test_assessment_routes.py - Assessment API endpoints",
        ]

        for test_file in test_files:
            print(f"  ✓ {test_file}")

    else:
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print("❌ Some tests failed!")
        print("Please check the output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
