from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, Length


class SignupForm(FlaskForm):
    nickname = StringField(
        "Nickname", validators=[DataRequired(), Length(min=3, max=50)]
    )
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=7, max=128)]
    )


class LoginForm(FlaskForm):
    nickname = StringField("Nickname", validators=[DataRequired(), Length(max=50)])
    password = PasswordField("Password", validators=[DataRequired(), Length(max=128)])
