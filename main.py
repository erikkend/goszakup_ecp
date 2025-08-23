import os
import time
import logging
import requests

from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from dotenv import load_dotenv

# Загружаем .env переменные
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.WARNING,  # для всего — только WARNING+
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("autozakup.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logging.getLogger("seleniumwire").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("selenium").setLevel(logging.WARNING)

logger = logging.getLogger("autozakup")
logger.setLevel(logging.INFO)

class AutoZakup:
    def __init__(self):
        try:
            self.driver = webdriver.Chrome()
            logger.info("WebDriver успешно инициализирован.")
        except Exception as e:
            logger.exception("Ошибка при инициализации WebDriver.")
            raise

    def main(self):
        try:
            self.driver.get("https://v3bl.goszakup.gov.kz/ru/user/login")
            logger.info("Открыта страница авторизации.")
            time.sleep(3)

            auth_button = self.driver.find_element(By.CSS_SELECTOR, "input#selectP12File")
            auth_button.click()
            logger.info("Кнопка выбора файла сертификата нажата.")
            time.sleep(2)

            sign_key = ""
            for request in self.driver.requests:
                if "goszakup.gov.kz" in request.url:
                    if request.url == "https://v3bl.goszakup.gov.kz/ru/user/sendkey/kz":
                        if request.response:
                            sign_key = request.response.body.decode("utf-8")
                            logger.info(f"Получен sign_key: {sign_key}")

            if sign_key == "":
                logger.error("Sign key не получен!")
                raise Exception("Sign key не получен!")

            xml_raw = self.get_xml_sing_by_key(sign_key)
            xml_clean = (
                xml_raw.replace('\\"', '"')
                .replace("\\n", "\n")
                .replace("&#13;", "")
            )

            script = f"""
                var xhr = new XMLHttpRequest();
                xhr.open('POST', 'https://v3bl.goszakup.gov.kz/user/sendsign/kz', false);
                xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');

                var data = 'sign=' + encodeURIComponent(`{xml_clean}`);
                xhr.send(data);

                return xhr.status + '|' + xhr.responseText;
            """

            result = self.driver.execute_script(script)
            status_code, response_text = result.split('|', 1)

            if (
                    response_text.strip()
                    == "<script>document.location.href = 'https://v3bl.goszakup.gov.kz/ru/user/registration'</script>"
            ):
                logger.warning("Успешно пройден этап подписи, получен редирект на регистрацию. Обновляем страницу...")
                self.driver.refresh()

            input("Нажмите Enter чтобы завершить программу.")

        except Exception as e:
            logger.exception("Ошибка в процессе выполнения main().")
            raise
        finally:
            self.driver.quit()
            logger.info("WebDriver закрыт.")

    def get_xml_sing_by_key(self, key: str):
        base64_key = os.environ.get("BASE64_KEY")
        password = os.environ.get("KEY_PASSWORD")

        if not base64_key or not password:
            logger.error("BASE64_KEY или KEY_PASSWORD не заданы в .env")
            raise ValueError("Отсутствуют ключи для подписи.")

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
        }
        payload = {
            "xml": f"<root><key>{key}</key></root>",
            "signers": [
                {
                    "key": base64_key,
                    "password": password,
                    "keyAlias": None,
                }
            ],
            "clearSignatures": False,
            "trimXml": False,
        }

        try:
            response = requests.post(
                "http://localhost:14579/xml/sign", headers=headers, json=payload, timeout=10
            )
            response.raise_for_status()
            resp_json = response.json()
            logger.info("XML успешно подписан.")
            return resp_json["xml"]
        except requests.RequestException as e:
            logger.exception("Ошибка при отправке запроса на xml/sign.")
            raise

    def health_check(self):
        try:
            health_resp = requests.get("http://localhost:14579/actuator/health", timeout=5)
            logger.info(f"Health check ответ: {health_resp.json()}")
        except requests.RequestException as e:
            logger.exception("Ошибка health check.")


if __name__ == "__main__":
    soft = AutoZakup()
    soft.main()
    # soft.health_check()
