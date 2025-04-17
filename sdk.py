from datetime import datetime


try:
    from urllib import urlopen, quote
except ImportError:
    from urllib.request import urlopen
    from urllib.parse import quote


# Вспомогательная функция, эмуляция тернарной операции ?:
def ifs(cond, val1, val2):
    if cond:
        return val1
    return val2


# Класс для взаимодействия с сервером smsc.ru

class SMSC:
    def __init__(self, auth_token: str, sending_type):
        """
        Инициализация атрибутов класса SMSC

        :param auth_token(str): Токен авторизации
        """
        self.smsc_password = auth_token
        self.smsc_post = True  # Использовать метод POST
        self.smsc_https = True  # Использовать HTTP-протокол
        self.smsc_charset = "utf-8"  # Кодировка сообщение
        self.smsc_login = ""  # Логин (если пустой, используется токен)
        self.smsc_debug = True  # Режим тестирования
        self.sending_type = sending_type  # (0 - sms, ... , 8 - mail, ... , 12 - bot, 13 - telegram)

    def send_sms(self, phones, message, translit=0, time="", id=0,
                 sender=False, query=""):
        """
        Метод отправки SMS

        :param phones(list): Список, состоящий из номеров телефонов
        :param message(str): Сообщение, которое нужно разослать
        :param translit(int, optional): Указывает,
        есть ли необходимость переводить в транслит (1, 2 или 0)
        :param time(str, optional): Указывает время доставки в виде (DDMMYYhhmm, h1-h2, 0ts, +m)
        :param id(int, optional): ИД сообщения, 32-битное число от 1 до 2147483647
        :param sender(str, optional): Имя отправителя или имя бота для телеги
        :param query(str, optional): Строка доп.параметров ("valid=01:00&maxsms=3")

        :return: В случае успешной отправки массив (<id>, <количество sms>, <стоимость>, <баланс>),
        в случае ошибки массив (<id>, -<код ошибки>)
        """
        phones_str = ",".join(phones)
        formats = ["flash=1", "push=1", "hlr=1", "bin=1", "bin=2", "ping=1",
                   "mms=1", "mail=1", "call=1", "viber=1", "soc=1", "", "tg=1"]

        m = self._smsc_send_cmd("send", "cost=3&phones=" + quote(
            phones_str) + "&mes=" + quote(message) + \
                                "&translit=" + str(translit) + "&id=" + str(
            id) + ifs(self.sending_type > 0,
                      "&" + formats[self.sending_type - 1], "") + \
                                ifs(sender == False, "",
                                    ifs(self.sending_type == 12, "&bot=",
                                        "&sender=") + quote(str(sender))) + \
                                ifs(time, "&time=" + quote(time), "") + ifs(
            query, "&" + query, ""))

        # (id, cnt, cost, balance) или (id, -error)

        if self.smsc_debug:
            if m[1] > "0":
                print("Сообщение отправлено успешно. ID: " + m[
                    0] + ", всего SMS: " + m[1] + ", стоимость: " + m[
                          2] + ", баланс: " + m[3])
            else:
                print("Ошибка №" + m[1][1:] + ifs(m[0] > "0", ", ID: " + m[0],
                                                  ""))

        return m

    def get_status(self, id, phone, all=0):
        """
        Метод проверки статуса отправленного SMS

        :param id(int): Идентификатор сообщения
        :param phone(list): Номера телефонов

        :return: Для отправленного SMS  массив
        (<статус>, <время изменения>, <код ошибки sms>)
        При all = 1 дополнительно возвращаются элементы в конце массива:
        (<время отправки>, <номер телефона>, <стоимость>, <sender id>, <название статуса>, <текст сообщения>)
        либо массив (0, -<код ошибки>) в случае ошибки
        """
        m = self._smsc_send_cmd("status",
                                "phone=" + quote(phone) + "&id=" + str(
                                    id) + "&all=" + str(all))

        # (status, time, err, ...) или (0, -error)

        if self.smsc_debug:
            if m[1] >= "0":
                tm = ""
                if m[1] > "0":
                    tm = str(datetime.fromtimestamp(int(m[1])))
                print("Статус SMS = " + m[0] + ifs(m[1] > "0",
                                                   ", время изменения статуса - " + tm,
                                                   ""))
            else:
                print("Ошибка №" + m[1][1:])

        if all and len(m) > 9 and (len(m) < 14 or m[14] != "HLR"):
            m = (",".join(m)).split(",", 8)

        return m

    def _smsc_send_cmd(self, cmd, arg=""):
        """
        Внутренний метод вызова запроса.
        Формирует URL и делает 3 попытки чтения
        """
        url = ifs(self.smsc_https, "https",
                  "http") + "://smsc.ru/sys/" + cmd + ".php"
        _url = url
        arg = ifs(self.smsc_login, "login=" + quote(self.smsc_login) + "&psw=",
                  "apikey=") + quote(
            self.smsc_password) + "&fmt=1&charset=" + self.smsc_charset + "&" + arg

        i = 0
        ret = ""

        while ret == "" and i <= 5:
            if i > 0:
                url = _url.replace("smsc.ru/", "www" + str(i) + ".smsc.ru/")
            else:
                i += 1

            try:
                if self.smsc_post or len(arg) > 2000:
                    data = urlopen(url, arg.encode(self.smsc_charset))
                else:
                    data = urlopen(url + "?" + arg)

                ret = str(data.read().decode(self.smsc_charset))
            except:
                ret = ""

            i += 1

        if ret == "":
            if self.smsc_debug:
                print("Ошибка чтения адреса: " + url)
            ret = ","  # фиктивный ответ

        return ret.split(",")

