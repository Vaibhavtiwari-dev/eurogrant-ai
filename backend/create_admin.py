import argparse
import getpass
import os
import sys

from sqlalchemy.orm import Session

# Add the parent directory to sys.path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import auth, database, models


def create_admin(email: str, password: str, full_name: str, org_name: str):
    db: Session = next(database.get_db())
    try:
        # Check if user exists
        user = db.query(models.User).filter(models.User.email == email).first()
        if user:
            print(f"User {email} already exists.")
            return

        # Check if organization exists or create new
        org = db.query(models.Organization).filter(models.Organization.name == org_name).first()
        if not org:
            email_domain = email.rsplit("@", 1)[-1].lower()
            org = models.Organization(name=org_name, email_domain=email_domain)
            db.add(org)
            db.commit()
            db.refresh(org)
            print(f"Created organization: {org_name}")

        hashed_password = auth.get_password_hash(password)
        new_user = models.User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            organization_id=org.id,
            role=models.RoleEnum.ADMIN,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        print(f"Successfully created admin user: {email} for organization: {org_name}")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create an initial admin user.")
    parser.add_argument("--email", required=True, help="Admin email address")
    parser.add_argument("--password", required=False, help="Admin password")
    parser.add_argument("--name", required=True, help="Admin full name")
    parser.add_argument("--org", required=True, help="Organization name")

    args = parser.parse_args()
    password = (
        args.password
        or os.environ.get("ADMIN_PASSWORD")
        or getpass.getpass("Enter admin password: ")
    )
    create_admin(args.email, password, args.name, args.org)
