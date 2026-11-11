import sys
from pathlib import Path

import pytest

PASTA_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(PASTA_SCRIPTS))

from banco import CAMINHO_BANCO  # noqa: E402


@pytest.fixture(scope="session")
def cliente():
    if not CAMINHO_BANCO.exists():
        pytest.skip("Banco não encontrado: rode a coleta e os scripts de estatística antes dos testes")
    from fastapi.testclient import TestClient

    from api import app

    with TestClient(app) as c:
        yield c
