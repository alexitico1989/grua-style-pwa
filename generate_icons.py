# generate_icons.py
"""
Generador de iconos PWA para Grúa Style
Crea todos los tamaños de iconos necesarios para la PWA
"""

from PIL import Image, ImageDraw, ImageFont
import os


def create_simple_icons():
    """Crear iconos simples con las iniciales GS"""

    icon_dir = "static/pwa"
    os.makedirs(icon_dir, exist_ok=True)

    sizes = [16, 32, 57, 60, 72, 76, 96, 114,
             120, 128, 144, 152, 180, 192, 384, 512]

    for size in sizes:
        # Crear imagen con fondo azul de Grúa Style
        img = Image.new('RGB', (size, size), '#2d5bff')
        draw = ImageDraw.Draw(img)

        # Agregar texto "GS" para Grúa Style
        font_size = size // 3
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()

        # Calcular posición del texto
        text = "GS"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (size - text_width) // 2
        y = (size - text_height) // 2

        # Dibujar texto blanco
        draw.text((x, y), text, fill='white', font=font)

        # Guardar
        filename = f"icon-{size}x{size}.png"
        filepath = os.path.join(icon_dir, filename)
        img.save(filepath, "PNG")
        print(f"✅ Creado: {filename}")

    print(f"\n🎉 ¡Iconos creados en {icon_dir}/!")


if __name__ == "__main__":
    print("🚀 Generando iconos PWA para Grúa Style...")

    try:
        create_simple_icons()
    except ImportError:
        print("❌ Pillow no está instalado. Instálalo con:")
        print("pip install Pillow")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n🔗 Usa el generador online:")
        print("https://www.pwabuilder.com/imageGenerator")
