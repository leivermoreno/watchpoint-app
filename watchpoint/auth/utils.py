def validate_credentials(nickname, password):
    if len(nickname) < 3 or len(password) < 7:
        return "Must provide, nickname >= 3 characters, and password >= 7 characters."
