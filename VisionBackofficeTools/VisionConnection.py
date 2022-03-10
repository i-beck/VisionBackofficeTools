"""Vision Connection Class
Requires Telnet connection finger as well as authentication
for user and pswd of the Vision Backoffice System
"""

from telnetlib import Telnet


def yield_vision_telnet_connection(host: str, port: int, user: str, password: str) -> Telnet:

    try:
        with Telnet(host, port) as telnet:
            telnet.read_until(b"login: ", 5)
            telnet.write(user.encode("ascii") + b"\n")
            telnet.read_until(b"Password: ", 5)
            telnet.write(password.encode("ascii") + b"\n")

            if b"Invalid domain/user/password" in telnet.read_until(b"UniData Release", 5):
                raise PermissionError("Invalid Vision Credientials Used.")
            telnet.write(b"\n")
            telnet.write(b"\n")
            telnet.write(b"\n")
            telnet.write(b"\n")

            return telnet
    except (TimeoutError, ConnectionRefusedError) as err:
        raise PermissionError("Invalid Vision Credientials Used. (IP/Port Mismatch or Whitelisting Error)") from err


class VisionConnection:
    def __init__(self, ip: str, port: int, username: str, password: str) -> None:
        connection = yield_vision_telnet_connection(ip, port, username, password)
        connection = self.gather_menu_type(connection)
        connection = self.vision_dump_to_ecl(connection)

        self.connection: Telnet = connection
        self.debug: bool = False
        self.timeout: int = 3

        return

    def close(self):
        """Close the connection."""
        connection = self.connection

        connection = self.vision_dump_to_ecl(connection)
        try:
            connection.write(b"BYE\n\n")
            connection.write(b"\n")
            connection.read_until(b"cgfdg~fdgdf~gdfg~fdg", 1)
            connection.close()
        except ConnectionResetError as _err:
            # print(_err)
            connection.close()
            self.connection = None
            return
        print("Vision Software disconnect Failed, attempting socket disconnect...")

        if connection:
            connection.close()

        self.connection = None

    def __enter__(self) -> None:
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def vision_dump_to_ecl(self, telnet: Telnet) -> Telnet:

        while b"1 record listed" not in telnet.read_until(b"\n:", 0.1):
            telnet.write("\x03Q\n\n\nABORT\n\n\nLIST RELEASE SAMPLE 1\n".encode("ascii"))
        telnet.read_until(b"\n:", 0.1)
        return telnet

    def gather_menu_type(self, connection: Telnet) -> Telnet:
        connection = self.vision_dump_to_ecl(connection)
        connection.write(b"M\n")

        if b"***  MAIN MENU  ***" in connection.read_until(b"Enter"):
            self.menu_type = "main"
            return connection

        self.menu_type = "scanner"

        return connection

    def wait_write(self, wait_until, write_this, wait_sec=None):
        wait_sec = self.timeout if wait_sec is None else wait_sec
        wait_until = wait_until.encode()
        tn_input = (write_this + "\r\n").encode()

        if self.debug:
            print(self.connection.read_until(wait_until, wait_sec).decode("ascii", "ignore"))
        else:
            self.connection.read_until(wait_until, wait_sec)
        self.connection.write(tn_input)

    def return_wait_write(self, wait_until, write_this, wait_sec=None):
        """RETURNS LAST DATA ASKED FOR THEN:
        write_this = "what you want to write now"
        wait_until = "string your waiting for next" """
        wait_sec = self.timeout * 10 if wait_sec is None else wait_sec
        wait_until = wait_until.encode()
        write_this = (write_this + "\r\n").encode()
        results = self.connection.read_until(wait_until, wait_sec)
        self.connection.write(write_this)
        if not self.debug:
            return results.decode("ascii", "ignore")
        result = results.decode("ascii", "ignore")
        print(result)
        return result
