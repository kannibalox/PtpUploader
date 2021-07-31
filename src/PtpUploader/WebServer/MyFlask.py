from flask import Flask


class MyFlask(Flask):
    def get_send_file_max_age(self, name):
        # Set expiration to 30 days for static content.
        if (
            name.endswith(".js")
            or name.endswith(".css")
            or name.endswith(".png")
            or name.endswith(".gif")
            or name.endswith(".ico")
        ):
            return 60 * 60 * 24 * 30

        return Flask.get_send_file_max_age(self, name)
