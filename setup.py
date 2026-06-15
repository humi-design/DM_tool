#!/usr/bin/env python3
"""
Setup script for AI Social OS
Creates initial admin user, sample data, and initializes the database.
"""

import os
import sys
import uuid
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_setup(email="admin@example.com", password="AdminPass123!", org_name="Demo Company", use_sqlite=True):
    """Run the complete setup."""
    print("\n" + "="*50)
    print("🚀 AI Social OS Setup")
    print("="*50 + "\n")
    
    # Set environment variables for SQLite if requested
    if use_sqlite:
        os.environ["SQLALCHEMY_DATABASE_URI"] = "sqlite:///aios.db"
        os.environ["FLASK_ENV"] = "development"
    
    from app import create_app, db
    from models.user import User
    from models.organization import Organization
    from models.subscription import Subscription
    from models.lead import Lead
    from models.business import Business
    
    def create_admin_user(email, password):
        """Create an admin user."""
        existing = User.query.filter_by(email=email).first()
        if existing:
            print(f"⚠️  User {email} already exists")
            return existing
        
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            first_name="Admin",
            last_name="User",
            is_verified=True,
            is_active=True,
            is_superuser=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f"✅ Created admin user: {email}")
        return user

    def create_sample_organization(owner, name, plan="starter"):
        """Create a sample organization."""
        existing = Organization.query.filter_by(slug=name.lower().replace(" ", "-")).first()
        if existing:
            print(f"⚠️  Organization '{name}' already exists")
            return existing
        
        org = Organization(
            id=str(uuid.uuid4()),
            name=name,
            slug=name.lower().replace(" ", "-"),
            description=f"Demo organization for {name}",
            owner_id=owner.id,
            plan=plan,
            plan_expires_at=datetime.utcnow() + timedelta(days=30),
            is_active=True,
        )
        db.session.add(org)
        db.session.commit()
        print(f"✅ Created organization: {name}")
        return org

    def create_sample_business(org, owner, name, business_type="ecommerce"):
        """Create a sample business."""
        existing = Business.query.filter_by(slug=name.lower().replace(" ", "-")).first()
        if existing:
            print(f"⚠️  Business '{name}' already exists")
            return existing
        
        business = Business(
            id=str(uuid.uuid4()),
            name=name,
            slug=name.lower().replace(" ", "-"),
            description=f"A sample {business_type} business",
            organization_id=org.id,
            owner_id=owner.id,
            business_type=business_type,
            industry="Retail",
            is_active=True,
        )
        db.session.add(business)
        db.session.commit()
        print(f"✅ Created business: {name}")
        return business

    def create_sample_leads(business, count=10):
        """Create sample leads."""
        sample_leads = [
            {"name": "John Smith", "email": "john@example.com", "phone": "+1234567890", "source_type": "instagram", "status": "new", "lead_score": 85},
            {"name": "Sarah Johnson", "email": "sarah@example.com", "phone": "+1987654321", "source_type": "instagram", "status": "contacted", "lead_score": 72},
            {"name": "Mike Brown", "email": "mike@example.com", "phone": "+1122334455", "source_type": "website", "status": "qualified", "lead_score": 90},
            {"name": "Emily Davis", "email": "emily@example.com", "phone": "+1555666777", "source_type": "instagram", "status": "new", "lead_score": 65},
            {"name": "David Wilson", "email": "david@example.com", "phone": "+1999888777", "source_type": "referral", "status": "converted", "lead_score": 95},
            {"name": "Lisa Anderson", "email": "lisa@example.com", "phone": "+1777888999", "source_type": "instagram", "status": "contacted", "lead_score": 78},
            {"name": "James Taylor", "email": "james@example.com", "phone": "+1666555444", "source_type": "website", "status": "new", "lead_score": 55},
            {"name": "Jennifer Martinez", "email": "jennifer@example.com", "phone": "+1444333222", "source_type": "instagram", "status": "qualified", "lead_score": 88},
            {"name": "Robert Garcia", "email": "robert@example.com", "phone": "+1333222111", "source_type": "referral", "status": "new", "lead_score": 70},
            {"name": "Amanda Thomas", "email": "amanda@example.com", "phone": "+1222111333", "source_type": "instagram", "status": "contacted", "lead_score": 82},
        ]
        
        for lead_data in sample_leads[:count]:
            lead = Lead(
                id=str(uuid.uuid4()),
                business_id=business.id,
                name=lead_data["name"],
                email=lead_data["email"],
                phone=lead_data["phone"],
                source_type=lead_data["source_type"],
                status=lead_data["status"],
                lead_score=lead_data["lead_score"],
            )
            db.session.add(lead)
        
        db.session.commit()
        print(f"✅ Created {count} sample leads")

    def create_subscription(org, plan="starter"):
        """Create a subscription for the organization."""
        existing = Subscription.query.filter_by(organization_id=org.id).first()
        if existing:
            print(f"⚠️  Subscription already exists for {org.name}")
            return existing
        
        subscription = Subscription(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            plan_id=plan,
            plan_name=plan.title(),
            status="active",
            billing_period_start=datetime.utcnow(),
            billing_period_end=datetime.utcnow() + timedelta(days=30),
            trial_start=datetime.utcnow(),
            trial_end=datetime.utcnow() + timedelta(days=30),
            quantity=1,
            unit_price=0,
            total_amount=0,
        )
        db.session.add(subscription)
        db.session.commit()
        print(f"✅ Created {plan} subscription")
        return subscription

    app = create_app()
    
    with app.app_context():
        # Create database tables
        print("📦 Creating database tables...")
        db.create_all()
        print("✅ Database tables created\n")
        
        # Create admin user
        print("👤 Creating admin user...")
        user = create_admin_user(email=email, password=password)
        
        # Create organization
        print("\n🏢 Creating organization...")
        org = create_sample_organization(owner=user, name=org_name)
        
        # Link user to organization
        user.organization_id = org.id
        db.session.commit()
        
        # Create business
        print("\n🏪 Creating sample business...")
        business = create_sample_business(org, user, name=f"{org_name} Store")
        
        # Create subscription
        print("\n💳 Creating subscription...")
        create_subscription(org)
        
        # Create sample leads
        print("\n👥 Creating sample leads...")
        create_sample_leads(business, count=10)
        
        print("\n" + "="*50)
        print("✅ Setup Complete!")
        print("="*50)
        print(f"\n🔐 Login Credentials:")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"\n🌐 URLs:")
        print(f"   Login: http://localhost:5000/auth/login")
        print(f"   Admin: http://localhost:5000/admin")
        print(f"   Settings: http://localhost:5000/admin/settings")
        print("\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup AI Social OS")
    parser.add_argument("--email", default="admin@example.com", help="Admin email")
    parser.add_argument("--password", default="AdminPass123!", help="Admin password")
    parser.add_argument("--org", default="Demo Company", help="Organization name")
    parser.add_argument("--no-sqlite", action="store_true", help="Use PostgreSQL instead of SQLite")
    
    args = parser.parse_args()
    run_setup(email=args.email, password=args.password, org_name=args.org, use_sqlite=not args.no_sqlite)