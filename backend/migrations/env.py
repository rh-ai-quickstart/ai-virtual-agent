import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from sqlalchemy.orm import Session

from models import Base, User, RoleEnum

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get the DATABASE_URL from environment variable
load_dotenv()
db_url_from_env = os.getenv("DATABASE_URL")

if not db_url_from_env:
    raise ValueError(
        "DATABASE_URL environment variable is not set or is empty. "
        "Alembic requires this to connect to the database. "
        "Please ensure it is defined in your environment "
        "(e.g., .env file, shell export)."
    )

# If your DATABASE_URL is an async one (e.g., postgresql+asyncpg://)
# Alembic typically uses a synchronous connection for migrations.
# So, you might need to convert it.
if db_url_from_env and db_url_from_env.startswith("postgresql+asyncpg://"):
    db_url_from_env = db_url_from_env.replace(
        "postgresql+asyncpg://", "postgresql://", 1
    )


config.set_main_option("sqlalchemy.url", db_url_from_env)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def seed_user(username: str, email: str, role: RoleEnum):
    session = Session(bind=context.get_bind())
    if session.query(User).filter(User.username == username).count() > 0:
        print("'" + username + "' user already exists")
    elif session.query(User).filter(User.email == email).count() > 0:
        print("user with '" + email + "' email address already exists")
    else:
        user = User(
            username=username,
            email=email,
            role=role,
        )
        session.add(user)
        session.commit()
        print("'" + username + "' user successfully seeded as a " + str(role))


def seed_admin_users():
    seed_user("ingestion-pipeline", "ingestion-pipeline@change.me", RoleEnum.admin)
    admin_username = os.getenv("ADMIN_USERNAME")
    if admin_username is not None:
        admin_email = os.getenv("ADMIN_EMAIL", "admin@change.me")
        seed_user(admin_username, admin_email, RoleEnum.admin)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()
        seed_admin_users()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()
            seed_admin_users()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
