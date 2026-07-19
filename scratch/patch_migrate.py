import os

migrate_path = os.path.join("backend", "database", "migrate_to_postgres.py")
with open(migrate_path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Patch ProjectDB creation
old_proj_creation = """            db_proj = session.get(ProjectDB, p_id)
            if not db_proj:
                db_proj = ProjectDB(
                    id=p_id,
                    name=p["name"],
                    description=p.get("description", ""),
                    line_of_business=p.get("line_of_business", "general"),
                    created_at=datetime.fromisoformat(p["created_at"].replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(p["created_at"].replace("Z", "+00:00"))
                )
                session.add(db_proj)"""

new_proj_creation = """            db_proj = session.get(ProjectDB, p_id)
            if not db_proj:
                db_proj = ProjectDB(
                    id=p_id,
                    name=p["name"],
                    description=p.get("description", ""),
                    line_of_business=p.get("line_of_business", "general"),
                    framework=p.get("framework", "playwright"),
                    jira_project_key=p.get("jira_project_key"),
                    target_url=p.get("target_url"),
                    target_username=p.get("target_username"),
                    target_password_enc=p.get("target_password_enc"),
                    created_at=datetime.fromisoformat(p["created_at"].replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(p["created_at"].replace("Z", "+00:00"))
                )
                session.add(db_proj)"""

if old_proj_creation in code:
    code = code.replace(old_proj_creation, new_proj_creation)
    print("Patched ProjectDB creation.")
else:
    print("Warning: ProjectDB creation pattern not matched.")

# 2. Patch db_projects serialization in round-trip check
old_db_projects = """        db_projects = []
        for p in session.scalars(select(ProjectDB).order_by(ProjectDB.created_at)).all():
            db_projects.append({
                "id": str(p.id),
                "name": p.name,
                "description": p.description,
                "line_of_business": p.line_of_business,
                "created_at": p.created_at.isoformat().replace("+00:00", "Z"),
                "requirements": [str(r.id) for r in p.requirements if r.deleted_at is None]
            })"""

new_db_projects = """        db_projects = []
        for p in session.scalars(select(ProjectDB).order_by(ProjectDB.created_at)).all():
            db_projects.append({
                "id": str(p.id),
                "name": p.name,
                "description": p.description,
                "line_of_business": p.line_of_business,
                "framework": p.framework,
                "jira_project_key": p.jira_project_key,
                "target_url": p.target_url,
                "target_username": p.target_username,
                "target_password_enc": p.target_password_enc,
                "created_at": p.created_at.isoformat().replace("+00:00", "Z"),
                "requirements": [str(r.id) for r in p.requirements if r.deleted_at is None]
            })"""

if old_db_projects in code:
    code = code.replace(old_db_projects, new_db_projects)
    print("Patched db_projects serialization.")
else:
    print("Warning: db_projects serialization pattern not matched.")

# 3. Insert Releases & Test Cycles Migration logic
old_notes_migration = """        # 9. Migrate Test Case Notes
        logger.info("Migrating test case notes...")
        for tc_id_str, notes in raw.get("test_case_notes", {}).items():
            tc_id = UUID(tc_id_str)
            for note in notes:
                stmt = select(TestCaseNoteDB).where(TestCaseNoteDB.test_case_id == tc_id, TestCaseNoteDB.note == note)
                if not session.scalar(stmt):
                    db_note = TestCaseNoteDB(test_case_id=tc_id, note=note)
                    session.add(db_note)

        session.commit()"""

new_notes_migration = """        # 9. Migrate Test Case Notes
        logger.info("Migrating test case notes...")
        for tc_id_str, notes in raw.get("test_case_notes", {}).items():
            tc_id = UUID(tc_id_str)
            for note in notes:
                stmt = select(TestCaseNoteDB).where(TestCaseNoteDB.test_case_id == tc_id, TestCaseNoteDB.note == note)
                if not session.scalar(stmt):
                    db_note = TestCaseNoteDB(test_case_id=tc_id, note=note)
                    session.add(db_note)

        # 10. Migrate Releases
        logger.info("Migrating releases...")
        for r_id_str, rel in raw.get("releases", {}).items():
            r_id = UUID(r_id_str)
            db_rel = session.get(ReleaseDB, r_id)
            if not db_rel:
                db_rel = ReleaseDB(
                    id=r_id,
                    project_id=UUID(rel["project_id"]),
                    name=rel["name"],
                    description=rel.get("description", ""),
                    status=rel.get("status", "Active"),
                    start_date=datetime.fromisoformat(rel["start_date"].replace("Z", "+00:00")) if rel.get("start_date") else None,
                    end_date=datetime.fromisoformat(rel["end_date"].replace("Z", "+00:00")) if rel.get("end_date") else None
                )
                session.add(db_rel)

        # 11. Migrate Test Cycles
        logger.info("Migrating test cycles...")
        for tc_id_str, tc in raw.get("test_cycles", {}).items():
            tc_id = UUID(tc_id_str)
            db_tc = session.get(TestCycleDB, tc_id)
            if not db_tc:
                db_tc = TestCycleDB(
                    id=tc_id,
                    release_id=UUID(tc["release_id"]),
                    name=tc["name"],
                    description=tc.get("description", ""),
                    status=tc.get("status", "Active"),
                    created_at=datetime.fromisoformat(tc["created_at"].replace("Z", "+00:00")) if tc.get("created_at") else None
                )
                session.add(db_tc)

        session.commit()"""

if old_notes_migration in code:
    code = code.replace(old_notes_migration, new_notes_migration)
    print("Patched Releases & Test Cycles migration.")
else:
    print("Warning: Notes migration pattern not matched.")

# 4. Insert Releases & Test Cycles Validation logic
old_recompiled = """        recompiled = {
            "projects": db_projects,
            "requirements": db_requirements,
            "scenarios": db_scenarios,
            "test_cases": db_tcs,
            "documents": db_documents,
            "execution_results": db_executions,
            "reports": db_reports,
            "scenario_notes": db_scenario_notes,
            "test_case_notes": db_test_case_notes
        }"""

new_recompiled = """        db_releases = {}
        for r in session.scalars(select(ReleaseDB)).all():
            db_releases[str(r.id)] = {
                "id": str(r.id),
                "project_id": str(r.project_id),
                "name": r.name,
                "description": r.description,
                "status": r.status,
                "start_date": r.start_date.isoformat().replace("+00:00", "Z") if r.start_date else None,
                "end_date": r.end_date.isoformat().replace("+00:00", "Z") if r.end_date else None
            }

        db_test_cycles = {}
        for tc in session.scalars(select(TestCycleDB)).all():
            db_test_cycles[str(tc.id)] = {
                "id": str(tc.id),
                "release_id": str(tc.release_id),
                "name": tc.name,
                "description": tc.description,
                "status": tc.status,
                "created_at": tc.created_at.isoformat().replace("+00:00", "Z") if tc.created_at else None
            }

        recompiled = {
            "projects": db_projects,
            "requirements": db_requirements,
            "scenarios": db_scenarios,
            "test_cases": db_tcs,
            "documents": db_documents,
            "execution_results": db_executions,
            "reports": db_reports,
            "scenario_notes": db_scenario_notes,
            "test_case_notes": db_test_case_notes,
            "releases": db_releases,
            "test_cycles": db_test_cycles
        }"""

if old_recompiled in code:
    code = code.replace(old_recompiled, new_recompiled)
    print("Patched recompiled validation object.")
else:
    print("Warning: Recompiled validation object pattern not matched.")

# 5. Patch default root nodes standardization
old_standardize = """        # Standardize missing root nodes in original to avoid key mismatches
        for k in ["documents", "execution_results", "reports", "scenario_notes", "test_case_notes"]:
            norm_original.setdefault(k, {})
            norm_db.setdefault(k, {})"""

new_standardize = """        # Standardize missing root nodes in original to avoid key mismatches
        for k in ["documents", "execution_results", "reports", "scenario_notes", "test_case_notes", "releases", "test_cycles"]:
            norm_original.setdefault(k, {})
            norm_db.setdefault(k, {})"""

if old_standardize in code:
    code = code.replace(old_standardize, new_standardize)
    print("Patched root nodes standardization.")
else:
    print("Warning: Root nodes standardization pattern not matched.")

# 6. Patch normalize_val for robust datetime comparisons
old_normalize_val = """        # Normalize and compare utility
        def normalize_val(val):
            if isinstance(val, str):
                if val.endswith("Z"):
                    val = val[:-1]
                if "+00:00" in val:
                    val = val.split("+00:00")[0]
                if "\\\\" in val:
                    val = val.replace("\\\\", "/")
            return val"""

new_normalize_val = """        # Normalize and compare utility
        def normalize_val(val):
            if isinstance(val, str):
                try:
                    # Clean up and normalize potential ISO datetimes to compare timezone offsets accurately
                    t_str = val
                    if t_str.endswith("Z"):
                        t_str = t_str[:-1] + "+00:00"
                    from datetime import timezone
                    dt = datetime.fromisoformat(t_str)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    else:
                        dt = dt.astimezone(timezone.utc)
                    return dt.strftime("%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    pass
                if "\\\\" in val:
                    val = val.replace("\\\\", "/")
            return val"""

if old_normalize_val in code:
    code = code.replace(old_normalize_val, new_normalize_val)
    print("Patched normalize_val helper.")
else:
    print("Warning: normalize_val pattern not matched.")

with open(migrate_path, "w", encoding="utf-8") as f:
    f.write(code)

print("Patch applied to migrate_to_postgres.py successfully.")
