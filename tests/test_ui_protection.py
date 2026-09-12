"""UI tests for displaying detected protected projects and badges."""

from pathlib import Path
from tidyos.storage import StorageRepository
from tidyos.ui.main_window import MainWindow
from tidyos.testing.demo_corpus import create_demo_corpus


def test_ui_protected_projects_display(qapp, tmp_path: Path):
    """Verify that scanning a project root displays the protected project card and badge on Home page."""
    corpus = create_demo_corpus(tmp_path / "Corpus")
    db_path = tmp_path / "ui_prot_test.db"
    repo = StorageRepository(db_path)

    window = MainWindow(repository=repo)

    # Initial state: 0 protected projects
    assert repo.get_statistics()["total_protected"] == 0
    assert window.home_page.card_protected.value_label.text() == "0"

    # Add Projects folder as a managed root and scan
    root = repo.add_managed_root(corpus["projects"], mode="AUTO")
    window.start_scan(target_root=root)

    window.thread_pool.waitForDone(5000)
    qapp.processEvents()

    # Verify protected projects count updated (next-demo and python-demo detected)
    stats = repo.get_statistics()
    assert stats["total_protected"] >= 1

    assert int(window.home_page.card_protected.value_label.text()) >= 1

    # Verify protected projects container rendered cards
    assert window.home_page.protected_layout.count() >= 1
