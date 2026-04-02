from agent.utils.app_map import canonicalize_app_name, normalize_app_name


def test_normalize_app_name_linux():
    assert normalize_app_name("calculator", platform_type="linux") == "gnome-calculator"
    assert normalize_app_name("google chrome", platform_type="linux") == "google-chrome-stable"


def test_normalize_app_name_windows():
    assert normalize_app_name("calculator", platform_type="windows") == "calc"
    assert normalize_app_name("spotify", platform_type="windows") == "spotify"


def test_normalize_app_name_macos():
    assert normalize_app_name("calculator", platform_type="macos") == "Calculator"
    assert normalize_app_name("chrome", platform_type="macos") == "Google Chrome"


def test_canonicalize_app_name():
    assert canonicalize_app_name("google chrome") == "chrome"
    assert canonicalize_app_name("vs code") == "vscode"
