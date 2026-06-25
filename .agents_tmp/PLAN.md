# 1. OBJECTIVE

Fix the SQLAlchemy mapper error: `Mapper 'Mapper[Organization(organizations)]' has no property 'saas_overrides'` that prevents login and accessing the admin panel.

# 2. CONTEXT SUMMARY

The error occurs due to a **SQLAlchemy relationship mismatch** between the `Organization` model and the SaaS models:

- **SaaS models** (in `models/saas.py`) define relationships using `back_populates` pointing to the `Organization` model:
  - `SaaSUsageTracking` → expects `organization.saas_usage_tracking`
  - `SaaSInvoice` → expects `organization.saas_invoices`
  - `SaaSTransaction` → expects `organization.saas_transactions`
  - `SaaSOrganizationOverride` → expects `organization.saas_overrides`

- **Organization model** (in `models/organization.py`) is **missing** all these relationship definitions. It only has `organization_usage` and `organization_features`.

This causes SQLAlchemy to fail when the mapper configuration is compiled because it can't find the expected relationships on the Organization mapper.

# 3. APPROACH OVERVIEW

Add the missing SaaS relationships to the `Organization` model to match what the SaaS models expect via `back_populates`. This will allow SQLAlchemy to properly configure the mapper relationships.

**Files to modify:**
- `models/organization.py` - Add missing SaaS relationships

# 4. IMPLEMENTATION STEPS

## Step 1: Add missing SaaS relationships to Organization model

**File:** `models/organization.py`

**Goal:** Add the 4 missing SaaS relationships that are expected by the SaaS models.

**Method:** Add the following relationships after the existing `organization_features` relationship:

```python
# SaaS relationships (required by dynamic SaaS models)
saas_usage_tracking = db.relationship("SaaSUsageTracking", back_populates="organization", lazy="dynamic", cascade="all, delete-orphan")
saas_invoices = db.relationship("SaaSInvoice", back_populates="organization", lazy="dynamic", cascade="all, delete-orphan")
saas_transactions = db.relationship("SaaSTransaction", back_populates="organization", lazy="dynamic", cascade="all, delete-orphan")
saas_overrides = db.relationship("SaaSOrganizationOverride", back_populates="organization", lazy="dynamic", cascade="all, delete-orphan")
```

**Location:** Insert after line 42 (after `organization_features` relationship) in `models/organization.py`.

## Step 2: Create database migration for new relationships

**Goal:** Ensure the database schema is updated to support the new relationships.

**Method:** Run the setup script or create a Flask-Migrate migration to sync the models with the database.

```bash
# If using Docker
docker-compose exec app python setup.py

# Or run migrations
docker-compose exec app flask db migrate -m "Add SaaS relationships to Organization"
docker-compose exec app flask db upgrade
```

## Step 3: Verify the fix

**Goal:** Confirm the login and admin panel work correctly.

**Method:** 
1. Start the application
2. Navigate to `/auth/login`
3. Login with admin credentials
4. Access `/admin` to verify the admin panel loads without errors

# 5. TESTING AND VALIDATION

**Success Criteria:**
1. Login page loads without errors
2. Admin credentials work (email: `admin@example.com`, password: `AdminPass123!`)
3. Admin panel (`/admin`) loads successfully
4. No SQLAlchemy mapper errors in console/logs

**Verification Commands:**
```bash
# Check if app starts without errors
docker-compose logs app | grep -i error

# Test the health endpoint
curl http://localhost:5000/health

# Test login endpoint
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"AdminPass123!"}'
```
