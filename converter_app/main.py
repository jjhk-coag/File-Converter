from requirements_installer import install_requirements

install_requirements()

from frontend.app_window import ConverterApp


def main():
    app = ConverterApp()
    app.run()


if __name__ == "__main__":
    main()