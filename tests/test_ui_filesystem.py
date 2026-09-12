"""UI integration tests for managed roots and filesystem scanning."""

from pathlib import Path
from tidyos.storage import StorageRepository
from tidyos.ui.main_window import MainWindow
from tidyos.testing.demo_corpus import create_demo_corpus


def test_ui_managed_roots_and_scan_flow(qapp, tmp_path: Path):
    """Test full UI integration: adding managed root, scanning, and UI metric refresh."""
    corpus = create_demo_corpus(tmp_path / "Corpus")
    db_path = tmp_path / "ui_test.db"
    repo = StorageRepository(db_path)

    # Initialize MainWindow with test repository
    window = MainWindow(repository=repo)

    # Pre-condition: 0 roots, 0 files
    stats_initial = repo.get_statistics()
    assert stats_initial["total_roots"] == 0
    assert stats_initial["total_files"] == 0

    # Simulate adding managed root
    root = repo.add_managed_root(corpus["downloads"], mode="AUTO")
    window.settings_page.refresh_roots_list()
    window.home_page.refresh_metrics()

    assert repo.get_statistics()["total_roots"] == 1

    # Trigger scan via MainWindow
    worker = window.start_scan(target_root=root)

    # Wait for thread pool or worker execution to finish
    window.thread_pool.waitForDone(5000)
    qapp.processEvents()

    # Verify metrics updated on Home page
    stats_after = repo.get_statistics()
    assert stats_after["total_files"] == 3
    assert stats_after["total_roots"] == 1

    assert window.home_page.card_indexed.value_label.text() == "3"
    assert "Across 1 approved root" in window.home_page.card_indexed.hint_label.text()

