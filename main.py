import time
import RPi.GPIO as GPIO
from app import App

def main():
    try:
        application = App()
        time.sleep(3)
        application.run_app()
    finally:
        GPIO.cleanup() # TODO: add cleaning of PINs used by the application and not all of them

if __name__ == '__main__':
    main()
