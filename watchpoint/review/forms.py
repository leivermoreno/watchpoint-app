from flask_wtf import FlaskForm
from wtforms import RadioField, TextAreaField
from wtforms.validators import DataRequired, InputRequired, Length


class ReviewForm(FlaskForm):
    comment = TextAreaField(
        "Write your review:", validators=[DataRequired(), Length(min=10, max=2000)]
    )
    # choices restrict stars to 1–5; coerce makes form.stars.data an int for upsert.
    stars = RadioField(
        "Stars",
        choices=[(i, i) for i in range(1, 6)],
        coerce=int,
        validators=[InputRequired()],
    )
