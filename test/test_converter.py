import os
import pytest
from converter import convert_file_logic
from PIL import Image

# Utwórz obraz testowy
@pytest.fixture
def sample_jpeg(tmp_path):
    path = tmp_path / "test.jpg"
    img = Image.new("RGB", (100, 100), color="red")
    img.save(path)
    return str(path)

def test_jpg_to_png(sample_jpeg):
    output = convert_file_logic(sample_jpeg, "png")
    assert os.path.exists(output)
    assert output.endswith(".png")

def test_unsupported_format(tmp_path):
    fake_path = tmp_path / "file.txt"
    fake_path.write_text("Hello")
    with pytest.raises(ValueError):
        convert_file_logic(str(fake_path), "jpg")
