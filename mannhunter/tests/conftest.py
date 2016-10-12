import os

import pytest


@pytest.fixture()
def mannhunter():
    import mannhunter.core

    os.environ['SUPERVISOR_SERVER_URL'] = 'unix:///dev/null'

    return mannhunter.core.Mannhunter()
