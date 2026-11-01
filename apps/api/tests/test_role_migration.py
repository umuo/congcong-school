from uuid import uuid4

import psycopg
from sqlalchemy.engine import make_url

from tests.test_foundation import migrate


def test_existing_parent_identity_survives_role_upgrade(postgres_url):
    migrate(postgres_url, "upgrade", "0004_curriculum")
    dsn = make_url(postgres_url).set(drivername="postgresql").render_as_string(hide_password=False)
    user_id, family_id, student_id = uuid4(), uuid4(), uuid4()
    with psycopg.connect(dsn) as db:
        db.execute(
            "INSERT INTO users (id,email,hashed_password,nickname,"
            "is_active,is_superuser,is_verified) "
            "VALUES (%s,%s,%s,%s,true,false,false)",
            (user_id, "legacy@example.com", "preserved-hash", "家长"),
        )
        db.execute(
            "INSERT INTO families (id,name,timezone) VALUES (%s,'既有家庭','Asia/Shanghai')",
            (family_id,),
        )
        db.execute(
            "INSERT INTO family_memberships (id,user_id,family_id,role) VALUES (%s,%s,%s,'owner')",
            (uuid4(), user_id, family_id),
        )
        db.execute(
            "INSERT INTO students (id,family_id,nickname,avatar,school_stage,"
            "grade,semester,daily_goal_minutes,revision) "
            "VALUES (%s,%s,'既有孩子','panda','primary',3,'up',20,1)",
            (student_id, family_id),
        )
        db.execute(
            "INSERT INTO auth_sessions (token,user_id,created_at,"
            "csrf_hash,mode,parent_verified_at) "
            "VALUES (%s,%s,now(),%s,'parent',now())",
            ("a" * 64, user_id, "b" * 64),
        )
    migrate(postgres_url, "upgrade", "head")
    with psycopg.connect(dsn) as db:
        assert db.execute(
            "SELECT id, login_name, role, must_change_password, hashed_password FROM users"
        ).fetchone() == (user_id, "legacy@example.com", "parent", False, "preserved-hash")
        assert db.execute("SELECT id,family_id FROM students").fetchone() == (student_id, family_id)
        assert db.execute("SELECT count(*) FROM auth_sessions").fetchone() == (0,)
    migrate(postgres_url, "downgrade", "0004_curriculum")
    migrate(postgres_url, "upgrade", "head")
    migrate(postgres_url, "check")


def test_regular_password_policy_clears_only_non_admin_flags(postgres_url):
    migrate(postgres_url, "upgrade", "0005_account_roles")
    dsn = make_url(postgres_url).set(drivername="postgresql").render_as_string(hide_password=False)
    identities = {role: uuid4() for role in ["admin", "parent", "student"]}
    with psycopg.connect(dsn) as db:
        for role, user_id in identities.items():
            db.execute(
                "INSERT INTO users (id,login_name,role,nickname,hashed_password,"
                "is_active,is_superuser,is_verified,must_change_password) "
                "VALUES (%s,%s,%s,%s,'unchanged-hash',true,false,false,true)",
                (user_id, "policy-" + role, role, role),
            )
    migrate(postgres_url, "upgrade", "head")
    with psycopg.connect(dsn) as db:
        rows = db.execute(
            "SELECT id,role,must_change_password,hashed_password FROM users"
        ).fetchall()
        assert len(rows) == 3
        for user_id, role, required, password_hash in rows:
            assert user_id == identities[role]
            assert required == (role == "admin")
            assert password_hash == "unchanged-hash"
    migrate(postgres_url, "downgrade", "0005_account_roles")
    migrate(postgres_url, "upgrade", "head")
    migrate(postgres_url, "check")
