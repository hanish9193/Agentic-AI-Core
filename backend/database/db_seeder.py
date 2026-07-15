from sqlalchemy.orm import Session
from backend.database.db_models import UserDB, RoleDB, PermissionDB, RolePermissionDB
from backend.services.auth_service import hash_password
from backend.config.settings import get_settings

DEFAULT_ROLES = ["Super Admin", "Admin", "Project Manager", "Tester", "Stakeholder"]

MODULES = ["Dashboard", "Requirements", "Scenarios", "TestCases", "Playwright", "Executions", "Reports", "Settings", "Users"]
ACTIONS = ["view", "create", "edit", "delete", "approve"]

def seed_database(db: Session) -> None:
    settings = get_settings()
    
    # 1. Seed Roles
    existing_roles = {r.name for r in db.query(RoleDB).all()}
    role_objects = {}
    for name in DEFAULT_ROLES:
        if name not in existing_roles:
            role = RoleDB(name=name)
            db.add(role)
            role_objects[name] = role
        else:
            role_objects[name] = db.query(RoleDB).filter(RoleDB.name == name).first()
    db.commit()

    # 2. Seed Permissions
    existing_perms = {(p.module, p.action) for p in db.query(PermissionDB).all()}
    perm_objects = {}
    for module in MODULES:
        for action in ACTIONS:
            if (module, action) not in existing_perms:
                perm = PermissionDB(module=module, action=action)
                db.add(perm)
                perm_objects[(module, action)] = perm
            else:
                perm_objects[(module, action)] = db.query(PermissionDB).filter(
                    PermissionDB.module == module, PermissionDB.action == action
                ).first()
    db.commit()

    # 3. Seed Role-Permissions Mapping
    # Fetch all permissions to ensure cache is hot
    all_perms = db.query(PermissionDB).all()
    perm_lookup = {(p.module, p.action): p.id for p in all_perms}

    def assign_perm(role_name, module, action):
        role_id = role_objects[role_name].id
        perm_id = perm_lookup.get((module, action))
        if perm_id:
            exists = db.query(RolePermissionDB).filter(
                RolePermissionDB.role_id == role_id,
                RolePermissionDB.permission_id == perm_id
            ).first()
            if not exists:
                rp = RolePermissionDB(role_id=role_id, permission_id=perm_id)
                db.add(rp)

    # Super Admin gets all permissions
    for module in MODULES:
        for action in ACTIONS:
            assign_perm("Super Admin", module, action)

    # Admin gets everything except Settings and Users modification
    for module in MODULES:
        if module not in ["Settings", "Users"]:
            for action in ACTIONS:
                assign_perm("Admin", module, action)
        else:
            assign_perm("Admin", module, "view")

    # Project Manager gets view, create, edit, delete, approve for business models
    for module in ["Dashboard", "Requirements", "Scenarios", "TestCases", "Playwright", "Executions", "Reports"]:
        for action in ACTIONS:
            assign_perm("Project Manager", module, action)
    assign_perm("Project Manager", "Settings", "view")

    # Tester gets view, create, edit for scenarios, testcases, executions, playwright, and view-only for dashboard, requirements, reports
    for module in ["Scenarios", "TestCases", "Playwright", "Executions"]:
        for action in ["view", "create", "edit"]:
            assign_perm("Tester", module, action)
    for module in ["Dashboard", "Requirements", "Reports"]:
        assign_perm("Tester", module, "view")

    # Stakeholder gets read-only view access to reports, executions, dashboard
    for module in ["Dashboard", "Requirements", "Executions", "Reports"]:
        assign_perm("Stakeholder", module, "view")

    db.commit()

    # 4. Seed Development Users
    # Seed ONLY if app environment is development
    if settings.app_env == "development":
        dev_users = [
            {"email": "dev@platform.ai", "name": "Super Admin User", "pass": "devpassword", "role": "Super Admin"},
            {"email": "admin@platform.ai", "name": "Admin User", "pass": "adminpassword", "role": "Admin"},
            {"email": "pm@platform.ai", "name": "Project Manager User", "pass": "pmpassword", "role": "Project Manager"},
            {"email": "tester@platform.ai", "name": "Tester User", "pass": "testerpassword", "role": "Tester"},
            {"email": "stakeholder@platform.ai", "name": "Stakeholder User", "pass": "stakeholderpassword", "role": "Stakeholder"}
        ]
        for du in dev_users:
            exists = db.query(UserDB).filter(UserDB.email == du["email"]).first()
            if not exists:
                user = UserDB(
                    email=du["email"],
                    password_hash=hash_password(du["pass"]),
                    full_name=du["name"],
                    role=du["role"],
                    is_active=True
                )
                db.add(user)
        db.commit()
