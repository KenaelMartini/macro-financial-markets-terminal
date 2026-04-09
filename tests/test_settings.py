from terminal_app.core.settings import SETTINGS


def test_settings_paths_are_resolved():
    assert SETTINGS.project_root.exists()
    assert SETTINGS.terminal_data_dir.exists()
    assert SETTINGS.sqlite_path.parent.exists()

