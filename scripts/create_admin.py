#!/usr/bin/env python3
"""
AUREVIX — Safe Local Development Administrator Setup and Recovery Utility
Creates or resets an ADMIN account in local development environments without exposing credentials.
Strictly forbidden in production environments.
"""

import os
import sys
import getpass
import argparse
from pathlib import Path

# 1. IMMEDIATE PRODUCTION GUARD
# Check environment variables before importing any platform configuration
_env_name = os.getenv("AUREVIX_ENV", os.getenv("ENVIRONMENT", "development")).strip().lower()
if _env_name == "production":
    print("\n[SECURITY ERROR] Local admin recovery/setup utility is strictly disabled in production environments.")
    print("   Production deployments require centralized enterprise directory or IAM provisioning.\n")
    sys.exit(1)

# Ensure project root is available on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.analytics.auth_manager import (
    AuthManager,
    validate_password_policy,
    normalize_email
)


def verify_non_production_environment() -> None:
    """
    Enforces strict production safety check across settings profiles.
    Refuses execution if the environment is set to production.
    """
    env_name = os.getenv("AUREVIX_ENV", os.getenv("ENVIRONMENT", "development")).strip().lower()
    if env_name == "production":
        print("\n[SECURITY ERROR] Local admin recovery/setup utility is strictly disabled in production environments.")
        print("   Production deployments require centralized enterprise directory or IAM provisioning.\n")
        sys.exit(1)

    try:
        from src.config.settings import ProductionSettings
        settings = ProductionSettings()
        if settings.IS_PRODUCTION:
            print("\n[SECURITY ERROR] Platform configuration reports production mode (IS_PRODUCTION=True).")
            print("   Aborting local admin utility execution.\n")
            sys.exit(1)
    except Exception:
        pass


def main() -> None:
    verify_non_production_environment()

    parser = argparse.ArgumentParser(
        description="AUREVIX — Safe Local Development Admin Account Setup / Recovery"
    )
    parser.add_argument(
        "--email",
        type=str,
        default=None,
        help="Administrator email address"
    )
    parser.add_argument(
        "--password",
        type=str,
        default=None,
        help="Administrator password (optional; if omitted, you will be prompted securely without echoing)"
    )
    parser.add_argument(
        "--display-name",
        type=str,
        default=None,
        help="Optional display name for administrator"
    )

    args = parser.parse_args()

    print("\n" + "=" * 65)
    print(" [ADMIN SETUP] AUREVIX — Safe Local Development Admin Setup")
    print("=" * 65)

    # 1. Acquire Email
    email = args.email
    if not email:
        try:
            email = input("\nEnter ADMIN email address: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            sys.exit(1)

    norm_email = normalize_email(email)
    if not norm_email or "@" not in norm_email:
        print("\n[ERROR] A valid email address is required.")
        sys.exit(1)

    # 2. Acquire Password
    password = args.password
    if not password:
        try:
            password = getpass.getpass("Enter new ADMIN password (min 8 characters): ")
            confirm = getpass.getpass("Confirm new ADMIN password: ")
            if password != confirm:
                print("\n[ERROR] Passwords do not match.")
                sys.exit(1)
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            sys.exit(1)

    # 3. Validate Password Policy
    is_valid, err_msg = validate_password_policy(password)
    if not is_valid:
        print(f"\n[ERROR] {err_msg}")
        sys.exit(1)

    # 4. Create or Reset ADMIN account via server-side UserStore
    try:
        res = AuthManager.setup_admin(
            email=norm_email,
            password=password,
            display_name=args.display_name
        )

        action_desc = "Created new" if res.get("action") == "created" else "Safely reset existing"

        print("\n" + "-" * 65)
        print("[SUCCESS] Administrator account configured successfully.")
        print("-" * 65)
        print(f" * Status:             {action_desc} ADMIN account")
        print(f" * Email:              {res['email']}")
        print(f" * Role:               {res['role']}")
        print(f" * Active:             {res['is_active']}")
        print(f" * Session Security:   Prior sessions invalidated; session version updated")
        print(f" * Hashing Algorithm:  scrypt (memory-hard, salted)")
        print("-" * 65)
        print("You can now sign in using these credentials in the AUREVIX application header.\n")

    except Exception as exc:
        print(f"\n[ERROR] Failed to setup administrator account: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
