from PIL import Image

# Wczytaj plik PNG
input_png = "C:\\Users\\JJHK\\Downloads\\app_icon_transparent.png"
output_ico = "C:\\Users\\JJHK\\Downloads\\converter_icon.ico"

# Konwersja na ICO
img = Image.open(input_png)
img.save(output_ico, format="ICO", sizes=[(256, 256)])

print("Konwersja zakończona! Ikona zapisana jako:", output_ico)
