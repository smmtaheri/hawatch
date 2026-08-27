import pytest
from django.core.management import get_commands, load_command_class
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db
def test_migrations_apply():
    executor = MigrationExecutor(connection)
    plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    assert plan == []


def test_seed_command_registered():
    commands = get_commands()
    assert "seed_demo_data" in commands
    assert "seed_tochal_catalog" in commands
    assert "ingest_open_meteo" in commands
    command = load_command_class(commands["seed_demo_data"], "seed_demo_data")
    assert "Idempotently seed" in command.help
