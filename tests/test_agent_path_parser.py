from core.agent import _extract_windows_path

def test_windows_path_from_turkish_sentence():
    prompt = (
        r"C:\CREWINTEL projesini baştan sona incele. "
        "Önce klasör ağacını çıkar."
    )
    assert _extract_windows_path(prompt) == r"C:\CREWINTEL"

def test_windows_path_with_period():
    assert _extract_windows_path(r"C:\CREWINTEL. incele") == r"C:\CREWINTEL"

def test_no_path():
    assert _extract_windows_path("UMAY'ı test et") is None
