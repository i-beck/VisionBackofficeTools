"""Vision Connection Class
Requires Telnet connection finger as well as authentication
for user and pswd of the Vision Backoffice System
"""

from telnetlib import Telnet


class VisionConnection(Telnet):
    def __init__(self, host: str, port: int, username: str, password: str) -> None:
        super(VisionConnection, self).__init__(host=host, port=port)

        self.visiondebug: bool = False
        self.timeout: int = 3
        self.menu_type = None
        self.prompt = "menu"

        self.create_vision_telnet_connection(username, password)
        self.gather_menu_type()

        return

    def create_vision_telnet_connection(self, user: str, password: str) -> None:

        try:

            self.read_until(b"login: ", 5)
            self.write(user.encode("ascii") + b"\n")
            self.read_until(b"Password: ", 5)
            self.write(password.encode("ascii") + b"\n")

            if b"Invalid domain/user/password" in self.read_until(b"Enter", 5):
                raise PermissionError("Invalid Vision Credientials Used.")
            self.write(b"\n")
            self.write(b"\n")
            self.write(b"\n")
            self.write(b"\n")

        except (TimeoutError, ConnectionRefusedError) as err:
            self.connection = None
            raise PermissionError("Invalid Vision Credientials Used. (IP/Port Mismatch or Whitelisting Error)") from err

        return

    def close_vision(self):
        """Close the connection."""

        try:
            self.write(b"END\n\nEND\n\nEND\n\nEND\n\n\n\n")
            self.write(b"\n\n\n\n\n\n\n16\n")
            self.write(b"\n\n\n\n\n\n\n5\n")
            self.run_ecl()
            self.write(b"BYE\n\n")
            self.write(b"\n")
            self.read_until(b"cgfdg~fdgdf~gdfg~fdg", 1)
            self.close()
        except ConnectionResetError as _err:
            # print(_err)
            self.close()

            return
        print("Vision Software disconnect Failed, attempting socket disconnect...")

        try:
            super().close()
        except AttributeError as _err:

            return

    def __enter__(self) -> None:
        if self.visiondebug:
            print("Connecting to vision...")
        return self

    def __exit__(self, type, value, traceback):
        if self.visiondebug:
            print("Closing vision...")
        self.close_vision()

    def run_menu(self, force=False) -> None:
        """Runs the Vision Backoffice Menu if it is not already running.

        Args:
            force (bool, optional): Forces function to run regardless of prompt attrib status. Will reset Backoffice to root menu (menu_type). Defaults to False.
        """
        if self.prompt == "menu" and not force:
            return
        self.run_ecl(force=True)
        dump = self.read_until(b":", 1)
        self.write(b"M\n")
        self.prompt("M")
        self.prompt == "menu"

    def run_ecl(self, force=False) -> None:
        """Runs the Vision ECL prompt if it is not already running.

        Args:
            force (bool, optional): Forces function to run regardless of prompt attrib status. Will reset to base prompt of ECL. Defaults to False.
        """
        if self.prompt == "ecl" and not force:
            return
        read_socket = ""
        while "1 record listed" not in read_socket:

            self.write("\x03".encode("ascii"))

            dump = self.read_until(b"Q", 1)

            if "DEBUGGER" in dump.decode("ascii", "ignore").upper():

                self.write("ABORT\n\n\nLIST RELEASE SAMPLE 1\n".encode("ascii"))

            self.write("Q\n\n\nLIST RELEASE SAMPLE 1\n".encode("ascii"))

            read_socket += self.read_until(b":", 1).decode("ascii", "ignore")

        _dump = self.read_until(b"\n:", 2)

        self.prompt = "ecl"
        return

    def gather_menu_type(self) -> None:
        """For setting the menu_type attribute. Not Normally used."""
        save_prompt = self.prompt[::-1][::-1]
        self.run_ecl(force=True)
        self.write(b"M\n")

        if b"***  MAIN MENU  ***" in self.read_until(b"Enter", 0.1):
            self.menu_type = "main"
            if save_prompt == "ecl":
                self.run_ecl()
                return
            self.run_menu()
            return

        self.menu_type = "scanner"
        if save_prompt == "ecl":
            self.run_ecl()
            return
        self.run_menu()
        return

    def wait_write(self, wait_until, write_this, wait_sec=None):
        wait_sec = self.timeout if wait_sec is None else wait_sec
        wait_until = wait_until.encode()
        tn_input = (write_this + "\r\n").encode()

        if self.visiondebug:
            print(self.read_until(wait_until, wait_sec).decode("ascii", "ignore"))
        else:
            _dump = self.read_until(wait_until, wait_sec)
        self.write(tn_input)

    def return_wait_write(self, wait_until, write_this, wait_sec=None, replace_scrnclr=True):
        """RETURNS LAST DATA ASKED FOR THEN:
        write_this = "what you want to write now"
        wait_until = "string your waiting for next" """
        wait_sec = self.timeout * 10 if wait_sec is None else wait_sec
        wait_until = wait_until.encode()
        write_this = (write_this + "\r\n").encode()
        results = self.read_until(wait_until, wait_sec)
        self.write(write_this)
        if not self.visiondebug:
            return results.decode("ascii", "ignore")
        result = results.decode("ascii", "ignore")
        print(result)
        if not replace_scrnclr:
            return result
        return result.replace("[H[2J", "")
