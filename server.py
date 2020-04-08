#
# Серверное приложение для соединений
#
import asyncio
from asyncio import transports


class ServerProtocol(asyncio.Protocol):
    login: str = None
    server: 'Server'
    transport: transports.Transport

    def __init__(self, server: 'Server'):
        self.server = server

    def data_received(self, data: bytes):
        print(data)

        decoded = data.decode()

        if self.login is not None:
            # сообщение приходит уже с переводом строки, и в send_message еще перевод строки добавляется, фиксим
            self.send_message(decoded.rstrip())

        elif decoded.startswith("login:"):
            # не во всех системах \r есть, кроме того могут на-вводить пробелов в начале и конце, делаем strip()
            login = decoded.replace("login:", "").strip()

            # 1. При попытке подключения клиента под логином, который уже есть в чате:
            if self.is_login_exists(login):
                # 1.1 отправляем клиенту текст с ошибкой "Логин {login} занят, попробуйте другой"
                self.transport.write("Логин {login} занят, попробуйте другой\n".encode())
                # 1.2 отключаем от сервера соединение клиента
                self.transport.close()
                return

            # 2. При успешном подключении клиента в чат:
            # ! логин может оказаться пустой строкой, проверяем это тоже
            elif login:
                self.login = login
                self.transport.write(f"Привет, {self.login}!\n".encode())
                #  2.1 Отправлять ему последние 10 сообщений из чата
                self.send_history()
                return

            # и вообще приглашение login: по хорошему надо чтоб сервер слал, но в рамках ТЗ оставим как есть
            self.transport.write("Неправильный логин\n".encode())

    def connection_made(self, transport: transports.Transport):
        self.server.clients.append(self)
        self.transport = transport
        print("Пришел новый клиент")

    def connection_lost(self, exception):
        self.server.clients.remove(self)
        print("Клиент вышел")

    def send_message(self, content: str):
        message = f"{self.login}: {content}\n"
        # сохраняем историю
        self.add_history(message)

        for user in self.server.clients:
            # и по хорошему, самому себе не надо сообщение отправлять, оно же уже есть на экране
            # можно было бы добавить код, см ниже, но в рамках тз не будем
            # if user == self:
            #     continue
            # и еще такой момент, когда клиент подключился но не залогинился, он тоже уже получает сообщения,
            # мне кажется это не правильно, но исправлять не буду
            user.transport.write(message.encode())

    def is_login_exists(self, login):
        for user in self.server.clients:
            if user.login == login:
                return True

        return False

    def send_history(self):
        for message in self.server.history:
            self.transport.write(message.encode())

    def add_history(self, message):
        self.server.history.append(message)
        if len(self.server.history) > 10:
            self.server.history.pop(0)


class Server:
    clients: list
    history: list = []

    def __init__(self):
        self.clients = []

    def build_protocol(self):
        return ServerProtocol(self)

    async def start(self):
        loop = asyncio.get_running_loop()

        coroutine = await loop.create_server(
            self.build_protocol,
            '127.0.0.1',
            8888
        )

        print("Сервер запущен ...")

        await coroutine.serve_forever()


process = Server()

try:
    asyncio.run(process.start())
except KeyboardInterrupt:
    print("Сервер остановлен вручную")
